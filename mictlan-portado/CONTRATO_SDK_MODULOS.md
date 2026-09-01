# Contrato del SDK de módulos externos de Mictlan

Este documento es la fuente de verdad de cómo construir un módulo externo
para Mictlan. Reemplaza cualquier nota de sesión anterior sobre el tema
("SDK de módulos externos (plan)" en `CLAUDE.md`, `GUIA_SDK_MODULOS_EXTERNOS.md`
de `mictlan-staging`) — esas fueron el proceso de diseño; esto es el
contrato ya construido, probado y vigente.

Si algo de acá no coincide con el código real de `mictlan/sdk/`, el
código manda — avisar para corregir este documento, no al revés.

## 1. Qué es un módulo externo

Un módulo externo es una carpeta en `external_modules/<module_id>/` que
Mictlan puede detectar, activar y desactivar **sin reiniciar el proceso**
y **sin que su código pase por el repo de Mictlan ni por revisión de
código del mantenedor del bot**. `external_modules/` está fuera de git
(`.gitignore`) — instalar algo ahí es, por definición, confiar en código
no auditado por este repo.

Un módulo externo **nunca** tiene acceso directo a:
- La base de datos principal (`mictlan/db.py`, el pool de Postgres).
- `os.environ` del proceso completo (puede leer su propia API key con
  `os.environ.get(...)`, pero no hay ningún mecanismo que se la esconda —
  la restricción real es de diseño/confianza, no técnica, ver §8).
- `roles.py` directo, ni ningún otro módulo interno de `mictlan/`.

Todo lo que un módulo externo puede hacer pasa por un objeto `contexto`
(`ContextoModulo`, `mictlan/sdk/contexto.py`) que el SDK le entrega al
instalarlo. Cada método de `contexto` exige un **scope** — un permiso
declarado explícitamente en el `manifest.json` del módulo. Sin el scope
declarado, la llamada levanta `PermisoNoConcedido` — nunca falla en
silencio, nunca se salta el chequeo.

## 2. Estructura de carpeta obligatoria

```
external_modules/
  mi_modulo/
    manifest.json       <- obligatorio
    mi_modulo.py         <- el archivo que declara el entrypoint
    otro_archivo.py       <- opcional, un modulo puede tener varios .py propios
    datos/                 <- opcional, catalogos/CSVs de solo lectura que
                               un admin coloca a mano (creada por el SDK
                               si el modulo usa contexto.datos.*_propio)
    estado/                 <- NUNCA se crea a mano -- la crea el SDK
                               automaticamente la primera vez que el
                               modulo usa contexto.datos.db (ver §6.5)
```

El `module_id` (ver §3) determina el nombre de la carpeta — deben
coincidir exactamente.

## 3. `manifest.json` — campos obligatorios

```json
{
  "module_id": "mi_modulo",
  "nombre": "Nombre legible para el panel de /mando",
  "version": "1.0.0",
  "entrypoint": "mi_modulo:install_modulo",
  "permissions": ["mensajes.enviar", "usuarios.registrar"]
}
```

| Campo | Obligatorio | Formato |
|---|---|---|
| `module_id` | Sí | string, sin espacios, coincide con el nombre de la carpeta |
| `nombre` | Sí | string, se muestra tal cual en el panel de `/mando` → 🧩 Módulos |
| `version` | Sí | string libre (ej. `"1.0.0"`), informativo, el SDK no la valida |
| `entrypoint` | Sí | `"<archivo_sin_.py>:<funcion>"` — ver §5 |
| `permissions` | Sí (puede ser `[]`) | lista de scopes exactos de la tabla de §4, nunca comandos ni roles |
| `env` | No | lista informativa de variables de entorno que el módulo necesita — el SDK no la lee ni la valida, es documentación para quien instale el módulo |

Si falta cualquier campo obligatorio, o el JSON es inválido, el SDK
rechaza el módulo con `ModuloInvalido` — no se llega a importar ningún
`.py`.

**Regla dura: `permissions` son scopes de acceso, nunca comandos ni
roles.** Un manifest que meta `/comando` o un nombre de rol dentro de
`permissions` se rechaza como scope desconocido — no se interpreta como
válido, no hay compatibilidad retroactiva con esa confusión.

## 4. Scopes disponibles (tabla completa)

Cualquier scope que no esté en esta tabla, o que empiece con un prefijo
de la lista de bloqueados, se rechaza con `PermisoNoConcedido` al activar
el módulo — nunca se llega a instalar.

| Scope | Habilita |
|---|---|
| `usuarios.leer_rol` | `contexto.obtener_rol(user_id)` |
| `usuarios.registrar` | `contexto.registrar_usuario(user_id, username)` |
| `mensajes.enviar` | `contexto.enviar_mensaje_servicio(...)` |
| `proxy.usar` | `contexto.proxy.url()` / `contexto.proxy.httpx()` |
| `datos.leer_propio` | `contexto.datos.listar_propios()` / `leer_csv_propio()` / `abrir_sqlite_propio()` |
| `datos.leer_compartido` | `contexto.datos.listar_compartidos()` / `leer_csv_compartido()` / `abrir_sqlite_compartido()` |
| `datos.escribir_propio` | `contexto.datos.db.*` (persistencia propia real, ver §6.5) |
| `canal.publicar` | `contexto.canal.*` (publicar y administrar destinos propios) |
| `creditos.leer_saldo` | `contexto.creditos.saldo(user_id)` |
| `creditos.cobrar` | `contexto.creditos.cobrar(...)` / `reembolsar(...)` |

Prefijos **siempre bloqueados**, sin excepción, aunque se agregara un
scope nuevo algún día que empiece igual: `db.`, `database.`, `secrets.`,
`env.`, `core.`, `shell.`, `system.`.

**Todavía no existen `contexto.captcha` ni `contexto.sms`** (2Captcha/
CapSolver/Anti-Captcha, HeroSMS/SMSPool). Eran groundwork explorado en
`mictlan-staging` pero quedaron pendientes de una decisión del dueño del
proyecto (con qué proveedor probar primero, si se soporta un proveedor
activo o varios a la vez) y nunca se validaron con credenciales reales.
Un manifest que declare `"captcha.resolver"` o `"sms.usar"` se rechaza
hoy como scope desconocido — no asumir que existen hasta que este
documento se actualice.

## 5. El entrypoint: `install_modulo(app, contexto)`

`entrypoint` en el manifest tiene el formato `"<archivo>:<función>"`. El
SDK importa dinámicamente `<archivo>.py` de la carpeta del módulo y llama
a `<función>(app, contexto)` — **síncrona, nunca `async def`** (el SDK no
la espera con `await`; si necesitás correr algo async al instalar, lanzá
una tarea con `asyncio.create_task(...)` desde dentro, o resolvelo de
forma perezosa en el primer uso real, ver §6.5).

```python
# mi_modulo.py
from telegram.ext import CommandHandler

def install_modulo(app, contexto) -> None:
    app.bot_data["mi_modulo_ctx"] = contexto  # patron estandar, ver §7
    app.add_handler(CommandHandler("micomando", _mi_comando))
    contexto.logger.info("modulo mi_modulo instalado")
```

`app` acá **no es** el `Application` real de `python-telegram-bot` — es
un envoltorio (`AppRecorder`, `mictlan/sdk/recorders.py`) que graba cada
`add_handler(...)` y cada job de `app.job_queue.run_*(...)` que el módulo
agregue, para poder sacarlos de verdad cuando se desactive (ver §9). Para
cualquier otro uso (`app.bot_data`, `app.bot`, etc.) se comporta
exactamente igual al `Application` real — un módulo no nota la
diferencia.

`contexto` es una instancia de `ContextoModulo` (`mictlan/sdk/contexto.py`),
con los permisos ya resueltos a partir del `manifest.json` — nunca se
construye a mano.

## 6. API completa de `ContextoModulo`

### 6.1 Métodos base (sin facade propio)

```python
await contexto.obtener_rol(user_id: int) -> str
    # requiere "usuarios.leer_rol"

await contexto.registrar_usuario(user_id: int, username: str | None) -> None
    # requiere "usuarios.registrar"

await contexto.enviar_mensaje_servicio(context, chat_id: int, texto: str, **kwargs)
    # requiere "mensajes.enviar" -- unico punto de salida para el primer
    # envio de un mensaje de servicio: agrega automaticamente el boton
    # "Cerrar" y agenda su autoborrado a los 30 minutos.
```

`contexto.module_id` (str) y `contexto.logger` (`logging.Logger`,
namespace `mictlan.modulos.<module_id>`) están siempre disponibles, sin
scope — no exponen nada sensible.

### 6.2 `contexto.proxy` (requiere `proxy.usar`)

```python
contexto.proxy.url() -> str                # DATAIMPULSE_PROXY_URL de .env
contexto.proxy.httpx() -> dict              # {"http://": url, "https://": url}, listo para httpx.AsyncClient(mounts=...)
```

Si `DATAIMPULSE_PROXY_URL` no está configurada en `.env`, levanta
`ProxyNoConfigurado` — el módulo debe capturarla y avisar con un mensaje
claro, nunca dejar pasar un traceback.

**Regla dura: cualquier módulo que salga a un servicio de terceros de
consumo/volumen debe salir por acá, nunca con su propia configuración de
red.**

### 6.3 `contexto.datos` — lectura de referencia (solo lectura)

```python
contexto.datos.listar_propios() -> list[str]               # requiere datos.leer_propio
contexto.datos.leer_csv_propio(nombre: str) -> list[dict]    # requiere datos.leer_propio
contexto.datos.abrir_sqlite_propio(nombre: str)                # requiere datos.leer_propio, context manager sqlite3 de solo lectura

contexto.datos.listar_compartidos() -> list[str]             # requiere datos.leer_compartido
contexto.datos.leer_csv_compartido(nombre: str) -> list[dict]  # requiere datos.leer_compartido
contexto.datos.abrir_sqlite_compartido(nombre: str)             # requiere datos.leer_compartido
```

- **Propios**: archivos en `external_modules/<module_id>/datos/`, un
  admin los coloca a mano en el disco del servidor. Nadie más los ve.
- **Compartidos**: archivos en `datos_compartidos/` (raíz del repo, fuera
  de git), legibles por cualquier módulo con el scope — para catálogos
  que varios módulos necesitan consultar.
- `leer_csv_*` carga el archivo **completo** en memoria, sin límite de
  filas — nunca trunca ni hace slicing.
- `abrir_sqlite_*` es **siempre de solo lectura** (`mode=ro`) — cualquier
  intento de escritura falla. Para persistencia escribible, ver §6.5.

### 6.4 `contexto.creditos` (requiere `creditos.leer_saldo` y/o `creditos.cobrar`)

```python
await contexto.creditos.saldo(user_id: int) -> int
    # requiere "creditos.leer_saldo"

await contexto.creditos.cobrar(user_id: int, cantidad: int, motivo: str) -> str
    # requiere "creditos.cobrar" -- descuenta de verdad, revalida el
    # saldo server-side dentro de un candado. Devuelve tx_id.

await contexto.creditos.reembolsar(tx_id: str, motivo: str = "reembolso") -> str
    # requiere "creditos.cobrar" -- SOLO reembolsa un tx_id que el propio
    # modulo genero con cobrar(). Nunca el de otro modulo. Nunca dos
    # veces el mismo tx_id (levanta TransaccionInexistente).
```

**Regla dura, sin excepción: `contexto.creditos` nunca tiene ni tendrá un
método `otorgar()`/`acuñar()`.** Acuñar créditos nuevos es exclusivo de
código interno gateado por rol `root` (`/otorgar`, ver
`mictlan/modules/creditos.py`). Un módulo externo que necesite dar de
alta saldo a un usuario (ej. una promoción) tiene que pedirle a un
administrador que corra `/otorgar` — nunca se construye un atajo para
que el módulo lo haga solo.

**Regla dura: nunca confiar en un saldo mostrado antes de cobrar.**
Cualquier pantalla de confirmación ("¿comprar por 10 créditos?") debe
mostrar el saldo en el **texto**, nunca en un botón — y `cobrar()` ya
revalida el saldo real en el momento del cobro, no antes.

Excepciones: `creditos.SaldoInsuficiente`, `creditos.TransaccionInexistente`
(reexportadas, no viven en el namespace de `sdk`).

### 6.5 `contexto.datos.db` (requiere `datos.escribir_propio`) — persistencia propia

Un módulo que necesite recordar algo entre reinicios (ej. un pedido a
medio resolver, un puntaje, un contador por usuario) usa
`contexto.datos.db` — un archivo SQLite propio y privado
(`external_modules/<module_id>/estado/estado.db`), con una conexión
`aiosqlite` real (async, nunca bloquea el proceso) que vive durante toda
la vida del proceso.

```python
await contexto.datos.db.executescript(script: str) -> None
    # para CREATE TABLE IF NOT EXISTS ... -- llamar de forma idempotente
    # (guardia propia del modulo, ver ejemplo abajo) antes del primer uso.

await contexto.datos.db.execute(query: str, *args) -> None
await contexto.datos.db.fetch(query: str, *args) -> list
await contexto.datos.db.fetchrow(query: str, *args)
await contexto.datos.db.fetchval(query: str, *args)
    # misma sintaxis $1/now() que el resto de Mictlan, aunque el backend
    # real de ESTE almacen sea SQLite, no Postgres.

contexto.datos.db.bloqueo  # -> asyncio.Lock propio de ESTE modulo
    # para cualquier seccion critica leer-y-decidir (ej. "sumar 1 sin
    # perder un incremento concurrente"). Uso:
    #   async with contexto.datos.db.bloqueo:
    #       actual = await contexto.datos.db.fetchval(...)
    #       await contexto.datos.db.execute(..., actual + 1)
```

Ejemplo completo, patrón obligatorio de inicialización perezosa (no hay
forma de correr `await` durante `install_modulo`, que es síncrono):

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

**Reglas duras:**
- Este almacén es **privado y aislado por módulo** — un archivo físico
  distinto por `module_id`, nunca compartido. Ni siquiera un bug en otro
  módulo puede leerlo o pisarlo.
- **Nunca** usar `contexto.datos.abrir_sqlite_propio()` (§6.3, solo
  lectura) para guardar estado — son conceptos y carpetas distintas
  (`datos/` vs `estado/`) a propósito, para no confundir catálogos de
  referencia con datos mutables del módulo.
- El candado (`bloqueo`) es **propio del módulo** — nunca esperar a otro
  módulo sin relación. Si tu módulo necesita una sección crítica, usá el
  tuyo; no hay un candado global.

### 6.6 `contexto.canal` (requiere `canal.publicar`)

```python
await contexto.canal.config(destino: str = "principal") -> dict
    # levanta PublicacionNoConfigurada si el destino no existe, esta
    # desactivado, o no tiene chat_id -- usar para el camino de "publicar
    # de verdad", no para un panel de configuracion (ver estado() abajo).

await contexto.canal.destinos_activos() -> list[dict]
await contexto.canal.plantilla(destino: str = "principal") -> str | None

await contexto.canal.publicar_texto(context, texto, destino="principal", botones_extra=None)
await contexto.canal.publicar_foto(context, foto, texto, destino="principal", botones_extra=None)
await contexto.canal.publicar_a_todos(context, texto=None, foto=None, botones_extra=None) -> dict[str, dict]
    # publica en TODOS los destinos activos del modulo a la vez -- ningun
    # destino caido tumba a los demas, se reporta {destino: {"ok": bool, "error": str|None}}

# -- administracion del propio modulo (para un panel de configuracion) --
# Estos NUNCA levantan PublicacionNoConfigurada -- un panel necesita
# poder mostrar/editar un destino apagado o incompleto, no solo usarlo.
await contexto.canal.estado(destino: str) -> dict | None
await contexto.canal.alternar_activo(destino: str) -> bool
await contexto.canal.fijar_periodicidad(destino: str, minutos: int) -> None
await contexto.canal.fijar_csv(destino: str, archivo: str, campo: str) -> None
```

Un módulo puede tener varios "destinos" (etiquetas libres, ej. `'canal'`
y `'principal'`) — cada uno con su propio `chat_id`, botón y
periodicidad, configurados por un admin, nunca hardcodeados en el
módulo.

## 7. Patrón estándar de un handler

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

Guardar `contexto` en `app.bot_data["<module_id>_ctx"]` dentro de
`install_modulo` es el patrón estándar para que los handlers lo recuperen
— el SDK no lo hace automático porque `contexto` puede necesitar
distintos nombres si un módulo tiene varios entrypoints.

## 8. Reglas duras (nunca romper)

1. **`permissions` son scopes, nunca comandos ni roles.** (§3)
2. **Nunca exponer `otorgar()`/acuñar crédito a un módulo externo.** (§6.4)
3. **Nunca confiar en un saldo/estado mostrado antes de una acción
   irreversible** — revalidar siempre server-side en el momento de
   actuar, no antes.
4. **Nunca guardar estado sin límite en un `dict`/`list` a nivel de
   módulo** (memoria de proceso que solo crece). Si el estado necesita
   sobrevivir un restart o crecer sin cota fija, usar
   `contexto.datos.db` (§6.5), acotado por diseño de esquema, no por un
   dict en RAM.
5. **Cualquier salida a un servicio de terceros de consumo/volumen pasa
   por `contexto.proxy`**, nunca con configuración de red propia del
   módulo.
6. **Namespace de `callback_data` propio, sin colisionar** con los ya
   reservados por código interno: `mando:` (`/mando`), `svc:` (botón
   Cerrar), `reporte:` (`/reporte`). Un módulo nuevo elige su propio
   prefijo (ej. `mimodulo:`) y lo usa siempre.
7. **El aislamiento de un módulo externo es solo por convención de
   scopes, no por proceso o sandbox real.** Un módulo corre en el mismo
   proceso Python que el resto del bot — nada le impide técnicamente
   hacer `os.system(...)`, leer `os.environ` directo, o quedarse con un
   `asyncio.Lock` sin liberarlo. La barrera de `ContextoModulo` es
   disciplina de diseño (nunca expone `app`/`db.get_pool()`/`os.environ`
   crudo), no una sandbox — instalar un módulo de un tercero no confiable
   sigue siendo, en la práctica, darle acceso equivalente al del propio
   bot. Revisar el código de un módulo antes de instalarlo sigue siendo
   la única defensa real.
8. **Nunca reimportar el `.py` de un módulo ya cargado en el proceso** —
   el SDK ya lo garantiza (`_loaded` en `mictlan/sdk/ciclo_vida.py`), un
   módulo no necesita (ni debe) forzar su propia recarga.

## 9. Ciclo de vida desde `/mando` → 🧩 Módulos

- **🔍 Detectar módulos**: escanea `external_modules/*/manifest.json` y
  registra cualquier `module_id` nuevo en la tabla `sdk_modulos`,
  **siempre inactivo por defecto**. La sola presencia del `.py` en disco
  nunca alcanza para que corra.
- **Activar**: valida el manifest + los scopes, importa el `.py` (si es
  la primera vez en este proceso) y corre `install_modulo(app, contexto)`
  contra el `Application` real que ya está corriendo — sin reiniciar el
  bot.
- **Desactivar**: saca de verdad cada handler agregado
  (`app.remove_handler(...)`) y cancela cada job programado
  (`job.schedule_removal()`). El módulo sigue importado en memoria para
  poder reactivarlo rápido, pero deja de responder a todo. Los datos de
  `contexto.datos.db` **nunca se tocan** al desactivar — siguen ahí para
  cuando se reactive.
- **Eliminar**: desactiva + borra la fila de `sdk_modulos` + libera el
  módulo de la memoria del proceso. **Nunca borra la carpeta de
  `external_modules/`** ni el archivo de `contexto.datos.db` — si el
  `.py` sigue en disco, "Detectar módulos" lo vuelve a encontrar como
  nuevo (inactivo) más adelante, con sus datos previos intactos.
- **Marcar interno/externo**: solo cambia una etiqueta en el panel (para
  marcar candidatos "graduados" a portar a mano a `mictlan/modules/`) —
  no mueve archivos ni cambia cómo se carga el módulo.

## 10. Checklist paso a paso para construir un módulo nuevo

1. Crear `external_modules/<module_id>/` con `manifest.json` (§3) y el
   `.py` del entrypoint.
2. Declarar en `permissions` **solo** los scopes de la tabla de §4 que el
   módulo realmente usa — el mínimo necesario, nunca "por las dudas".
3. Escribir `install_modulo(app, contexto)` (síncrona) registrando
   handlers/jobs, guardando `contexto` en `app.bot_data` (§7).
4. Si el módulo necesita persistencia propia: seguir el patrón exacto de
   §6.5 (esquema + guardia de inicialización perezosa + candado para
   secciones críticas).
5. Si el módulo cobra créditos: pantalla de confirmación con el saldo en
   texto (nunca en botón), revalidar con `cobrar()` en el momento de la
   acción, reembolsar en **cualquier** camino de fallo posterior al
   cobro.
6. Elegir un prefijo de `callback_data` propio, sin colisionar (regla 6
   de §8).
7. Probar en `mictlan-staging` primero — nunca directo contra producción
   (ver metodología de pruebas de `CLAUDE.md`).
8. Desde `/mando` → 🧩 Módulos: "🔍 Detectar módulos" → abrir el módulo →
   "✅ Activar". Confirmar en el journal que no hay errores.
9. Si el módulo falla al activar, el mensaje de error (`ModuloInvalido` o
   `PermisoNoConcedido`) se muestra en el panel de detalle — no hace
   falta mirar logs para saber qué falta.

## 11. Ejemplo mínimo completo

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
    texto = " ".join(context.args) if context.args else "(nada que repetir)"
    await contexto.enviar_mensaje_servicio(
        context, message.chat_id, f"{texto}\n\n(tu rol: {rol})"
    )

def install_modulo(app, contexto) -> None:
    app.bot_data["eco_ctx"] = contexto
    app.add_handler(CommandHandler("eco", _eco_command))
    contexto.logger.info("modulo eco instalado")
```

## 12. Qué falta (para no asumir que ya existe)

- `contexto.captcha` / `contexto.sms` — ver §4, decisión pendiente del
  dueño del proyecto.
- Auditoría propia de un módulo (`contexto.audit`, para que un módulo
  loguee sus propias acciones de negocio de forma append-only) —
  candidato identificado comparando contra el SDK de ALFA-1, nunca
  construido.
- Ningún mecanismo de sandbox/aislamiento real por proceso — ver regla 7
  de §8.
