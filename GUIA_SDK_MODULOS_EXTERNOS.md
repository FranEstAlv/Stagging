# Guía SDK — construcción de módulos externos para Mictlan (staging)

Reescrita por completo el 2026-09-05. La versión anterior de este
documento (escrita el 2026-08-31, antes de que existieran
`contexto.datos`, `contexto.creditos`, `contexto.canal`, `contexto.captcha`
y `contexto.sms`, y antes de que `mictlan/sdk.py` se partiera en el
paquete `mictlan/sdk/` de 13 archivos) quedó obsoleta — no queda rastro
de esa versión acá, todo lo de abajo está verificado contra el código
real de `mictlan/sdk/` a esta fecha.

**Cambio de enfoque pedido explícitamente por Fernando**: este documento
ya no es una guía narrativa/exploratoria. Es un conjunto de instrucciones
**obligatorias** y **prohibiciones** — cada punto marcado `OBLIGATORIO`
o `PROHIBIDO` es una condición real para que el SDK acople el módulo
(lo detecte, lo importe y lo active sin error), no una recomendación de
estilo. Donde una regla existe por una razón no obvia, se explica el
mecanismo atómico exacto (qué línea de qué archivo hace qué), para que
quien construya un módulo entienda el *porqué*, no solo el *qué*.

Si algo de acá no coincide con el código real de `mictlan/sdk/`, el
código manda — avisar para corregir este documento, no al revés.

---

## 1. Estructura de carpeta

```
external_modules/
  mi_modulo/
    manifest.json     <- OBLIGATORIO
    mi_modulo.py       <- el archivo del entrypoint, OBLIGATORIO
    otro_archivo.py     <- OPCIONAL, un modulo puede tener varios .py propios
    datos/               <- OPCIONAL, catalogos de solo lectura (contexto.datos.leer_csv_propio)
    estado/               <- NUNCA crear a mano -- la crea el SDK solo al primer uso de contexto.datos.db
```

**OBLIGATORIO**: `module_id` (el campo del manifest, ver §2) debe ser
idéntico al nombre de esta carpeta. Si no coincide, `activar_modulo`
calcula la ruta `external_modules/<module_id>/` a partir del manifest —
si esa carpeta no existe, falla con `ModuloInvalido` (`ciclo_vida.py:132-134`).
El SDK **no corrige** un mismatch, no busca la carpeta por otro nombre.

**PROHIBIDO** nombrar un archivo propio igual a un paquete real de Python
ya instalado en el venv (`json.py`, `requests.py`, `os.py`, etc.). Motivo
atómico: `importador.py` hace `sys.path.append(str(carpeta))` (línea 26,
**al final** de `sys.path`, nunca al principio, precisamente para que un
paquete real ya cargado gane primero) — pero esa entrada queda **para
siempre** en `sys.path` mientras el proceso viva, incluso si tu módulo
se desactiva. Un archivo con nombre colisionante puede sombrear un
import de OTRO módulo que se cargue después del tuyo en el mismo
proceso. `eliminar_modulo` sí limpia esta entrada (`desregistrar_ruta()`,
corregido 2026-09-05) — pero solo al eliminar, nunca al desactivar.

---

## 2. `manifest.json`

### 2.1 Campos — qué es OBLIGATORIO de verdad

```json
{
  "module_id": "mi_modulo",
  "nombre": "Nombre legible para el panel de /mando",
  "version": "1.0.0",
  "entrypoint": "mi_modulo:install_modulo",
  "permissions": ["mensajes.enviar", "usuarios.registrar"]
}
```

| Campo | Obligatorio de verdad (`manifiestos.py:12`) | Qué se valida realmente |
|---|---|---|
| `module_id` | **Sí** | Solo *truthiness* (`if not manifest.get(c)`, línea 23) — un número, una lista no vacía, cualquier valor "truthy" pasa. **Cero validación de tipo ni de formato.** No hay regex de snake_case ni chequeo de caracteres válidos para nombre de carpeta. |
| `nombre` | **Sí** | Igual, solo truthiness. Se muestra tal cual (sin sanitizar) en el panel de `/mando` → 🧩 Módulos. |
| `version` | **Sí** | Solo truthiness — string libre, ni siquiera se exige que "parezca" un semver. Puramente informativo. |
| `entrypoint` | **Sí** | Solo truthiness acá; la validación real de *formato* (`"archivo:función"`) ocurre después, en `importador.py:11-12` (ver §3). |
| `permissions` | **NO está en `CAMPOS_MANIFEST_OBLIGATORIOS`** pese a que un manifest sin esta clave funciona igual — se resuelve como `[]` (`ciclo_vida.py:136,216`, `manifest.get("permissions", [])`). Declararla igual es buena práctica, no es una condición real de aceptación. |
| `env` | No, nunca se lee ni se valida. Puramente documental para quien instale el módulo a mano. |

**OBLIGATORIO**: si falta cualquiera de los 4 campos de verdad
obligatorios, o el archivo no es JSON válido, `leer_manifest` levanta
`ModuloInvalido` (`manifiestos.py:18,22,25`) **antes** de que se
importe una sola línea del `.py` — este es el único punto de todo el
ciclo de vida donde la validación ocurre sin ejecutar código del
módulo.

**PROHIBIDO**: meter un nombre de comando (`/comando`) o un nombre de
rol (`admin`, `root`, etc.) dentro de `permissions`. Se rechaza como
scope desconocido (§2.2) — nunca se interpreta como válido, no hay
compatibilidad retroactiva con esa confusión. Lección directa de los
parches R2.31.8.28.1/.28.2 de ALFA-1, que tuvo que corregir dos veces
manifests reales que mezclaban comandos/roles con scopes.

### 2.2 Scopes — tabla completa, allowlist cerrada

Cualquier scope que no esté en esta lista exacta se rechaza con
`PermisoNoConcedido` (`scopes.py:39-42`) **antes** de importar el
`.py` — a diferencia de la validación del manifest, esta sí es
genuinamente estática, no requiere ejecutar nada del módulo.

| Scope | Habilita |
|---|---|
| `usuarios.leer_rol` | `contexto.obtener_rol(user_id)` |
| `usuarios.registrar` | `contexto.registrar_usuario(user_id, username)` |
| `mensajes.enviar` | `contexto.enviar_mensaje_servicio(...)` |
| `proxy.usar` | `contexto.proxy.url()` / `contexto.proxy.httpx()` |
| `captcha.resolver` | `contexto.captcha.*` (2Captcha/CapSolver/Anti-Captcha, incluido Turnstile) |
| `sms.usar` | `contexto.sms.*` (HeroSMS/SMSPool) |
| `datos.leer_propio` | `contexto.datos.listar_propios()` / `leer_csv_propio()` / `abrir_sqlite_propio()` |
| `datos.leer_compartido` | `contexto.datos.listar_compartidos()` / `leer_csv_compartido()` / `abrir_sqlite_compartido()` |
| `datos.escribir_propio` | `contexto.datos.db.*` (persistencia propia real, ver §6) |
| `canal.publicar` | `contexto.canal.*` |
| `creditos.leer_saldo` | `contexto.creditos.saldo(user_id)` |
| `creditos.cobrar` | `contexto.creditos.cobrar(...)` / `reembolsar(...)` |

**PROHIBIDO**, doble barrera además de no estar en la tabla de arriba
(`scopes.py:26`): cualquier scope que empiece con `db.`, `database.`,
`secrets.`, `env.`, `core.`, `shell.`, `system.` — bloqueado por
prefijo aunque alguna vez se agregara un scope nuevo que empezara
igual.

**OBLIGATORIO**: declarar solo los scopes que el módulo usa de verdad —
el mínimo necesario, nunca "por las dudas". La revalidación de scopes
ocurre en cada (re)activación (`ciclo_vida.py:136,216`), nunca en
tiempo real contra un manifest editado en caliente: un módulo ya activo
sigue corriendo con el `ContextoModulo(module_id, permisos)` congelado
al momento de instalarse (línea 114) hasta el próximo
desactivar+activar.

---

## 3. El entrypoint — regla exacta, sin excepciones

`entrypoint` = `"<archivo_sin_extension>:<función>"`.

**OBLIGATORIO**: la función debe ser **síncrona** (`def`, nunca
`async def`). Mecanismo atómico: `ciclo_vida.py:118` llama
`instalar_fn(recorder, contexto)` **sin `await`**. Antes del
2026-09-05 esto fallaba en silencio — una corrutina sin ejecutar, el
módulo quedaba marcado "activo" en `sdk_modulos` sin haber registrado
un solo handler, sin ningún error visible. Corregido: `importador.py`
ahora detecta `inspect.iscoroutinefunction(instalar_fn)` y rechaza con
`ModuloInvalido` **antes** de marcar el módulo activo. Si tu entrypoint
necesita hacer algo async al instalar, usá `asyncio.create_task(...)`
desde dentro de la función síncrona, o resolvelo de forma perezosa en
el primer uso real (patrón de §6).

**OBLIGATORIO**: la función debe existir con exactamente ese nombre en
exactamente ese archivo. Mecanismo atómico exacto, en orden:
1. `importador.py:14-16` — si `<archivo>.py` no existe en la carpeta,
   `ModuloInvalido` limpio, **nada se ejecuta todavía**.
2. `importador.py:28-32` — `spec_from_file_location` +
   `exec_module(mod)`. **Acá se ejecuta TODO el código top-level de tu
   `.py` completo** — imports, variables de módulo, cualquier código
   que no esté dentro de una función. Esto pasa **antes** del siguiente
   paso.
3. `importador.py:33` — recién ahora se chequea `hasattr(mod, funcion)`.
   Si falta, `ModuloInvalido` — pero tu código top-level **ya corrió**
   igual.

**Consecuencia atómica importante, no obvia**: un módulo con un
`entrypoint` mal escrito en el manifest (nombre de función que no
existe) **igual ejecuta todo tu código top-level** antes de fallar. Si
ese código top-level tiene efectos secundarios (abrir un archivo,
conectarse a algo, lanzar un hilo), esos efectos ya ocurrieron aunque
el módulo termine rechazado. **PROHIBIDO** asumir que un `ModuloInvalido`
significa "nada de tu código corrió" — solo significa que
`install_modulo` no se llamó.

**PROHIBIDO** (no hay ningún chequeo de esto, así que es
responsabilidad de quien escribe el módulo): declarar el entrypoint con
una firma distinta a `(app, contexto)` — dos parámetros posicionales
exactos. `importador.py` solo chequea que la función *exista*, nunca su
firma. Una firma con distinta aridad revienta con un `TypeError` normal
de Python en `ciclo_vida.py:118`, fuera del `try/except` que atrapa
`(ModuloInvalido, PermisoNoConcedido)` en el panel de `/mando` — el
admin ve silencio + el error solo en el canal de logs (ver
`mictlan/logs_canal.py`), no un mensaje lindo en el panel.

```python
# mi_modulo.py — forma exacta obligatoria
from telegram.ext import CommandHandler

def install_modulo(app, contexto) -> None:
    app.bot_data["mi_modulo_ctx"] = contexto
    app.add_handler(CommandHandler("micomando", _mi_comando))
    contexto.logger.info("modulo mi_modulo instalado")
```

`app` **no es** el `Application` real — es `AppRecorder`
(`mictlan/sdk/recorders.py`), un envoltorio que graba cada
`add_handler(...)` y cada `app.job_queue.run_*(...)` para poder
sacarlos de verdad al desactivar (§7). Para cualquier otro atributo
(`app.bot`, `app.bot_data`, etc.) se comporta exactamente igual al
`Application` real.

---

## 4. Qué se valida sin ejecutar código vs. qué solo se descubre importando

Distinción atómica central de todo el SDK — de esto depende qué tan
"seguro" es instalar un módulo que no revisaste línea por línea:

**Se valida SIN correr nada del `.py` del módulo:**
- `manifest.json` existe, es JSON válido, tiene los 4 campos
  obligatorios (§2.1).
- `entrypoint` tiene el formato `"archivo:función"` (`importador.py:11-12`).
- El archivo del entrypoint existe en la carpeta (`importador.py:15-16`).
- Los scopes declarados están en la allowlist y no tienen prefijo
  bloqueado (§2.2).

**Solo se descubre EJECUTANDO el código real** (`exec_module`,
`importador.py:32`):
- Que la función del entrypoint exista de verdad.
- Que sea síncrona (chequeado automáticamente desde 2026-09-05).
- Que tenga la firma correcta.
- **Absolutamente cualquier otra cosa que el código top-level del
  módulo haga** — no hay AST-inspection previo, no hay sandbox, no hay
  límite de qué puede importar o ejecutar antes de que el SDK chequee
  nada.

**PROHIBIDO** instalar (activar) un módulo externo cuyo código no
leíste completo vos mismo. El aislamiento de `ContextoModulo` es
disciplina de diseño, no una sandbox real (§8) — "el SDK lo validó" NO
significa "el código es seguro", significa únicamente "el manifest
tiene el formato correcto y los scopes declarados existen".

---

## 5. Detección — cuándo un módulo nuevo se vuelve visible

**OBLIGATORIO** entender que esto **no es un escaneo periódico**. Un
`.py` nuevo en `external_modules/` es invisible para el bot hasta que
pase una de exactamente estas dos cosas:
1. `descubrir_e_instalar(app)` — corre **una sola vez**, al arrancar el
   proceso (`main.py:89`, dentro de `_post_init`).
2. El botón "🔍 Detectar módulos" en `/mando` → 🧩 Módulos
   (`modulos.py`, acción `"escanear"`).

`sincronizar_registro()` (`ciclo_vida.py:40-69`) registra en
`sdk_modulos` cualquier `module_id` con manifest válido que todavía no
tenga fila — **siempre `activo=False`** por defecto. La sola presencia
del `.py` en disco nunca alcanza para que corra: alguien lo tiene que
activar a propósito.

---

## 6. `contexto.datos.db` — persistencia propia, patrón obligatorio

Un módulo que necesite recordar algo entre reinicios usa
`contexto.datos.db` (requiere `datos.escribir_propio`) — un SQLite
propio y privado por módulo (`external_modules/<module_id>/estado/estado.db`,
`mictlan/almacen_modulos.py`), conexión `aiosqlite` real, async.

**OBLIGATORIO** el patrón de inicialización perezosa exacto — no hay
forma de correr `await` durante `install_modulo`, que es síncrona:

```python
_ESQUEMA = "CREATE TABLE IF NOT EXISTS puntajes (user_id INTEGER PRIMARY KEY, puntos INTEGER NOT NULL DEFAULT 0);"
_esquema_listo: set[str] = set()

async def _asegurar_esquema(contexto) -> None:
    if contexto.module_id in _esquema_listo:
        return
    await contexto.datos.db.executescript(_ESQUEMA)
    _esquema_listo.add(contexto.module_id)

async def _sumar_punto(contexto, user_id: int) -> int:
    await _asegurar_esquema(contexto)
    async with contexto.datos.db.bloqueo:
        actual = await contexto.datos.db.fetchval(
            "SELECT puntos FROM puntajes WHERE user_id = $1", user_id
        )
        nuevo = (actual or 0) + 1
        await contexto.datos.db.execute(
            "INSERT INTO puntajes (user_id, puntos) VALUES ($1, $2) "
            "ON CONFLICT(user_id) DO UPDATE SET puntos = excluded.puntos",
            user_id, nuevo,
        )
        return nuevo
```

**PROHIBIDO** usar `contexto.datos.abrir_sqlite_propio()` (§9, scope
`datos.leer_propio`, siempre solo lectura) para guardar estado — son
carpetas y conceptos distintos a propósito (`datos/` catálogos de
referencia vs. `estado/` mutable del módulo).

**PROHIBIDO** guardar estado que necesite sobrevivir un restart en un
`dict`/`list` a nivel de módulo sin límite — antipatrón ya documentado
en `CLAUDE.md`. Estado efímero acotado (ej. `trivia/estado.py`, sesión
activa por `chat_id`, se borra al resolver) sí es válido en RAM,
mientras tenga ciclo de vida completo — nunca un diccionario que solo
crece.

**OBLIGATORIO**: el candado `contexto.datos.db.bloqueo` es propio de
CADA módulo — nunca esperar el candado de otro módulo, no existe un
candado global compartido.

---

## 7. Ciclo de vida — qué pasa atómicamente en cada acción del panel

| Acción | Qué hace de verdad | Qué NO hace |
|---|---|---|
| 🔍 Detectar módulos | Registra `module_id` nuevos en `sdk_modulos`, siempre `activo=False` | Nunca activa nada solo |
| ✅ Activar | Importa el `.py` (solo la primera vez en este proceso, `_loaded`), corre `install_modulo(app, contexto)`, marca `activo=True` | — |
| ⛔ Desactivar | `app.remove_handler(handler, group)` de verdad + `job.schedule_removal()` de verdad para cada handler/job que ESE módulo agregó | El módulo sigue importado en memoria (para reactivar rápido); su estado en `contexto.datos.db` **nunca se toca** |
| Reactivar | Vuelve a llamar `install_modulo(app, contexto)` — **nunca reimporta el `.py`** | — |
| 🗑 Eliminar | Desactiva + borra la fila de `sdk_modulos` + libera el módulo de memoria + saca la carpeta de `sys.path` (corregido 2026-09-05) | **Nunca** borra la carpeta de `external_modules/` ni el archivo de `contexto.datos.db` — "Detectar módulos" lo vuelve a encontrar como nuevo (inactivo) más adelante, con sus datos previos intactos |
| Marcar interno/externo | Solo cambia una etiqueta (`sdk_modulos.origen`) | Nunca mueve archivos ni cambia cómo se carga |

**OBLIGATORIO desde 2026-09-05**: `activar_modulo` es idempotente —
llamarlo dos veces seguidas sin pasar por "Desactivar" en el medio
(ej. una carrera de dos admins clickeando "Activar" casi al mismo
tiempo) ya no deja una primera tanda de handlers huérfana en el
`Application` sin ninguna referencia para sacarla. Antes de esta fecha,
`_handlers[module_id]` se pisaba entero con la tanda nueva, perdiendo
la referencia a la tanda vieja — bug real, corregido.

**PROHIBIDO** forzar la reimportación del `.py` de un módulo ya cargado
en el proceso — el SDK ya lo garantiza (`_loaded`), un módulo no
necesita (ni debe) intentar recargarse a sí mismo.

---

## 8. Aislamiento — lo que existe y lo que NO existe

**OBLIGATORIO entender esto antes de instalar cualquier módulo de un
tercero no confiable**: no hay sandbox real. Un módulo corre en el
mismo proceso Python, mismo usuario del sistema operativo (`olimpo`),
mismo intérprete que el resto del bot. `ContextoModulo`
(`mictlan/sdk/contexto.py`) no expone `app` crudo, `db.get_pool()`, ni
`os.environ` — pero eso es disciplina de diseño, no una restricción
técnica. Nada le impide a un módulo, si su autor lo escribe así,
`import os; os.system(...)`, leer `os.environ` directo, o
`from mictlan import db` y agarrar el pool real. **La única defensa
real es leer el código del módulo antes de activarlo** — el SDK no
sustituye esa revisión.

**PROHIBIDO** asumir que declarar pocos `permissions` en el manifest
limita técnicamente lo que el código Python del módulo puede hacer —
los scopes solo gatean los métodos de `ContextoModulo`; no filtran ni
restringen imports ni llamadas directas a otras librerías.

**Nota sobre dependencias de terceros**: no existe ningún mecanismo de
`pip install` automático. Un módulo que necesite un paquete que no está
ya en el venv compartido (`venv/`) falla con `ModuleNotFoundError` al
importarse — instalarlo a mano en el venv del VPS sigue siendo un paso
manual obligatorio, sin importar cómo llegó el `.py` al disco.

---

## 9. API completa de `ContextoModulo` (referencia rápida)

```python
# Sin scope, siempre disponibles
contexto.module_id: str
contexto.logger: logging.Logger              # namespace mictlan.modulos.<module_id>

# Metodos base
await contexto.obtener_rol(user_id) -> str                                    # usuarios.leer_rol
await contexto.registrar_usuario(user_id, username) -> None                   # usuarios.registrar
await contexto.enviar_mensaje_servicio(context, chat_id, texto, **kw)         # mensajes.enviar

# contexto.proxy -- proxy.usar
contexto.proxy.url() -> str
contexto.proxy.httpx() -> dict                # {"http://": url, "https://": url}

# contexto.captcha -- captcha.resolver (2Captcha/CapSolver/Anti-Captcha)
contexto.captcha.proveedores_disponibles() -> list[str]
await contexto.captcha.balance(proveedor) -> float
await contexto.captcha.resolver_recaptcha_v2(proveedor, sitekey, url) -> str
await contexto.captcha.resolver_turnstile(proveedor, sitekey, url) -> str
await contexto.captcha.resolver_imagen(proveedor, imagen_base64) -> str

# contexto.sms -- sms.usar (HeroSMS/SMSPool)
contexto.sms.proveedores_disponibles() -> list[str]
await contexto.sms.balance(proveedor) -> str

# contexto.datos -- lectura de referencia, siempre solo lectura
contexto.datos.listar_propios() -> list[str]                    # datos.leer_propio
contexto.datos.leer_csv_propio(nombre) -> list[dict]             # datos.leer_propio
contexto.datos.abrir_sqlite_propio(nombre)                        # datos.leer_propio
contexto.datos.listar_compartidos() -> list[str]                  # datos.leer_compartido
contexto.datos.leer_csv_compartido(nombre) -> list[dict]           # datos.leer_compartido
contexto.datos.abrir_sqlite_compartido(nombre)                      # datos.leer_compartido

# contexto.datos.db -- persistencia propia ESCRIBIBLE (ver §6), datos.escribir_propio
await contexto.datos.db.executescript(script) -> None
await contexto.datos.db.execute(query, *args) -> None
await contexto.datos.db.fetch(query, *args) -> list
await contexto.datos.db.fetchrow(query, *args)
await contexto.datos.db.fetchval(query, *args)
contexto.datos.db.bloqueo                       # asyncio.Lock propio del modulo

# contexto.creditos -- creditos.leer_saldo / creditos.cobrar
await contexto.creditos.saldo(user_id) -> int                                 # creditos.leer_saldo
await contexto.creditos.cobrar(user_id, cantidad, motivo) -> str              # creditos.cobrar, devuelve tx_id
await contexto.creditos.reembolsar(tx_id, motivo="reembolso") -> str          # creditos.cobrar

# contexto.canal -- canal.publicar
await contexto.canal.config(destino="principal") -> dict
await contexto.canal.destinos_activos() -> list[dict]
await contexto.canal.plantilla(destino="principal") -> str | None
await contexto.canal.publicar_texto(context, texto, destino="principal", botones_extra=None)
await contexto.canal.publicar_foto(context, foto, texto, destino="principal", botones_extra=None)
await contexto.canal.publicar_a_todos(context, texto=None, foto=None, botones_extra=None) -> dict
await contexto.canal.estado(destino) -> dict | None            # nunca levanta, para paneles
await contexto.canal.alternar_activo(destino) -> bool
await contexto.canal.fijar_periodicidad(destino, minutos) -> None
await contexto.canal.fijar_csv(destino, archivo, campo) -> None
```

**PROHIBIDO, sin excepción**: `contexto.creditos` nunca tiene ni tendrá
un método `otorgar()`/`acuñar()`. Acuñar créditos nuevos es exclusivo
de código interno gateado por rol `root` (`/otorgar`). Un módulo que
necesite dar de alta saldo a un usuario tiene que pedirle a un
administrador que corra `/otorgar` — nunca se construye un atajo para
que el módulo lo haga solo. Esta regla es una lección directa de
revisar ambos SDKs de ALFA-1 hoy mismo: el SDK "oficial" de módulos de
ALFA-1 (`samaritan/services/module_sdk.py`) ni siquiera ofrece una
fachada de créditos — un módulo que quisiera tocar créditos ahí no
tiene ningún camino sancionado, solo podría importar el servicio
interno directo y llamar a `mint()`, que además **no verifica en
ningún lado que quien lo invoca sea superadmin** (ese chequeo vive
solo en la capa de comando de Telegram, nunca dentro del servicio). En
Mictlan el camino sancionado (`contexto.creditos`) existe, y la
asimetría (nunca `otorgar()`) es estructural: el método ni siquiera
está importado en `facades_creditos.py`.

**PROHIBIDO** confiar en un saldo mostrado antes de cobrar. Cualquier
pantalla de confirmación ("¿comprar por 10 créditos?") debe mostrar el
saldo en el **texto**, nunca en un botón — `cobrar()` ya revalida el
saldo real en el momento del cobro, dentro de un candado
(`asyncio.Lock`) contra doble gasto concurrente.

---

## 10. Patrón estándar de un handler

```python
async def _mi_comando(update, context):
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    contexto = context.bot_data["mi_modulo_ctx"]  # guardado en install_modulo
    await contexto.registrar_usuario(user.id, user.username)
    await contexto.enviar_mensaje_servicio(context, message.chat_id, "Hola!")
```

**OBLIGATORIO** guardar `contexto` en `app.bot_data["<module_id>_ctx"]`
dentro de `install_modulo` — el SDK no lo hace automático (un módulo
puede tener varios entrypoints con necesidades distintas). Sin esto,
ningún handler tiene forma de acceder al `contexto` que el SDK
construyó con los permisos ya resueltos.

**OBLIGATORIO** namespace de `callback_data` propio, sin colisionar con
los ya reservados por código interno: `mando:`, `svc:`, `reporte:`,
`bienvenida:`, `ingreso:`. Un módulo nuevo elige su propio prefijo (ej.
`mimodulo:`) y lo usa siempre, en todos sus botones.

---

## 11. Créditos y cobro — reglas duras para cualquier módulo que cobre algo

**OBLIGATORIO** revalidar server-side (con `cobrar()`, nunca con un
saldo cacheado en memoria) inmediatamente antes de cualquier acción
irreversible.

**OBLIGATORIO** reembolsar (`contexto.creditos.reembolsar(tx_id, ...)`)
en **absolutamente cualquier** camino de fallo posterior al cobro — sin
importar en qué paso del flujo falló la acción que el cobro pagaba. Un
módulo que cobra y no completa la acción, y no reembolsa, es un bug
grave, no un detalle menor.

**OBLIGATORIO** un `reembolsar()` solo puede revertir un `tx_id` que el
propio módulo generó con su propio `cobrar()` — nunca el de otro
módulo, nunca dos veces el mismo `tx_id` (levanta
`TransaccionInexistente` si se reintenta).

---

## 12. `contexto.proxy` — salida a internet

**OBLIGATORIO**: cualquier módulo que salga a un servicio de terceros
de consumo/volumen (scraping, verificación de proxies, llamadas
masivas) sale por `contexto.proxy`, nunca con su propia configuración
de red (`httpx.AsyncClient()` sin `mounts`, `requests` con su propio
proxy hardcodeado, etc.).

**PROHIBIDO** asumir que `DATAIMPULSE_PROXY_URL` siempre está
configurada — si falta, `contexto.proxy.url()` levanta
`ProxyNoConfigurado`; el módulo debe capturarla y avisar con un mensaje
claro al usuario, nunca dejar pasar un traceback.

---

## 13. Checklist obligatorio antes de "Activar" un módulo nuevo

Ningún módulo se considera correctamente acoplado si no cumple los 12
puntos:

- [ ] `manifest.json` tiene los 4 campos obligatorios de verdad
      (`module_id`, `nombre`, `version`, `entrypoint`) y el nombre de
      carpeta coincide exactamente con `module_id`.
- [ ] `permissions` declara **solo** scopes de la tabla de §2.2, el
      mínimo que el módulo usa de verdad.
- [ ] El entrypoint es una función **síncrona** con firma exacta
      `(app, contexto)`.
- [ ] `contexto` se guarda en `app.bot_data["<module_id>_ctx"]` dentro
      de `install_modulo`.
- [ ] `callback_data` usa un prefijo propio que no colisiona con
      `mando:`/`svc:`/`reporte:`/`bienvenida:`/`ingreso:`.
- [ ] Ningún archivo propio del módulo se llama igual a un paquete real
      de Python.
- [ ] Si necesita persistencia: usa `contexto.datos.db` con el patrón
      de inicialización perezosa de §6 — nunca `dict`/`list` sin límite
      a nivel de módulo para algo que debe sobrevivir un restart.
- [ ] Si sale a internet a un servicio de terceros de volumen: pasa por
      `contexto.proxy`.
- [ ] Si cobra créditos: saldo mostrado en texto (nunca en botón),
      revalida con `cobrar()` en el momento de la acción, reembolsa en
      **cualquier** camino de fallo posterior.
- [ ] Vos (o quien lo instale) leyó el código completo del módulo — el
      SDK no ofrece ninguna garantía de seguridad más allá de scopes y
      formato de manifest (§4, §8).
- [ ] Se probó primero en `mictlan-staging`, nunca directo contra
      producción.
- [ ] Tras "🔍 Detectar módulos" → "✅ Activar", se confirmó en el canal
      de logs / journal que no hay errores.

---

## 14. Ejemplo mínimo completo y funcionando

```
external_modules/eco/manifest.json:
{
  "module_id": "eco",
  "nombre": "Eco",
  "version": "1.0.0",
  "entrypoint": "eco:install_modulo",
  "permissions": ["mensajes.enviar", "usuarios.leer_rol"]
}

external_modules/eco/eco.py:
from telegram.ext import CommandHandler

async def _eco_command(update, context):
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    contexto = context.bot_data["eco_ctx"]
    rol = await contexto.obtener_rol(user.id)
    texto = " ".join(context.args) if context.args else "(sin texto)"
    await contexto.enviar_mensaje_servicio(context, message.chat_id, f"🔊 eco (rol={rol}): {texto}")

def install_modulo(app, contexto) -> None:
    app.bot_data["eco_ctx"] = contexto
    app.add_handler(CommandHandler("eco", _eco_command))
    contexto.logger.info("modulo eco instalado")
```

Módulo real ya instalado y activo en `mictlan-staging`, sirve como
referencia mínima verificada. Para un ejemplo con botones, estado en
memoria por chat y persistencia con `contexto.datos.db`, ver
`external_modules/trivia/` (`trivia.py` + `estado.py` + `preguntas.py`)
en este mismo repo.
