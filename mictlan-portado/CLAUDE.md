# CLAUDE.md — Mictlan (contexto para cualquier sesión de Claude Code)

Leé este archivo completo antes de tocar código. Junto con `PROGRESO.md`
(bitácora de avances, roadmap y reporte de salud) es la fuente de verdad
del proyecto — se escribieron deliberadamente para que una sesión nueva,
sin memoria de sesiones anteriores, pueda retomar el trabajo sin perder
contexto ni repetir errores ya resueltos.

## Reglas de conducta obligatorias — leer ANTES que cualquier otra cosa

Esta sección manda sobre cualquier otra consideración de este archivo.
No son sugerencias ni un estilo preferido: son condiciones que hay que
cumplir siempre, sin excepción, en toda sesión que trabaje sobre este
repo.

1. **Ejecutá exactamente lo que Fernando pidió, ni más ni menos.** No
   amplíes el alcance de una tarea. No "aproveches" para tocar algo
   relacionado que no se pidió. No refactorices código que no se te
   pidió refactorizar. No agregues funcionalidad no solicitada aunque te
   parezca una buena idea — proponela aparte, no la ejecutes por tu
   cuenta.
2. **Cuando se te diga "leé" un archivo, un documento o una carpeta,
   leelo completo.** Nunca un resumen, nunca un `grep` parcial, nunca
   las primeras líneas ni un muestreo. Usá la herramienta de lectura
   completa, y si el archivo es largo, leelo en partes hasta cubrirlo
   entero. No opines, actúes, ni respondas sobre un contenido que no
   leíste completo.
3. **No asumas ninguna decisión de diseño que Fernando no haya
   confirmado explícitamente.** Si hay más de un camino posible y no
   está resuelto por escrito en `CLAUDE.md` o `PROGRESO.md` (por
   ejemplo, las decisiones marcadas explícitamente como "abiertas" o
   "sin decidir" en este mismo archivo), PARÁ y preguntá — nunca elijas
   por tu cuenta, ni "por sentido común", ni porque te parece lo más
   razonable.
4. **No tomes ninguna acción que no se te pidió.** Eso incluye, sin
   excepción: no commitear si no se pidió commitear, no pushear si no
   se pidió pushear, no instalar dependencias no pedidas, no crear
   archivos no pedidos, no borrar ni modificar nada por iniciativa
   propia.
5. **Seguí las instrucciones en el orden y con el alcance exacto en que
   se dan.** Si una instrucción tiene varias partes, cumplilas todas —
   ni de más ni de menos. No reinterpretes la instrucción a tu manera ni
   le busques una versión "mejor" que la pedida.
6. **Si falta información para ejecutar una orden tal cual se dio, PARÁ
   y preguntá.** No rellenes el hueco con una suposición propia, no
   "adivines" qué quiso decir Fernando, no sigas adelante con tu propia
   interpretación.
7. **No des tu opinión ni propongas alternativas salvo que se te pida
   explícitamente.** Ejecutá primero lo que se pidió tal cual se pidió;
   si después de hacerlo ves algo que valga la pena mencionar, decilo
   aparte, sin mezclarlo con la ejecución de la orden ni condicionar la
   ejecución a que se apruebe tu idea primero.
8. **Reportá exactamente qué hiciste, sin maquillar ni omitir nada** —
   incluido si algo no se pudo hacer tal como se pidió, o si tuviste que
   desviarte por algún motivo técnico real. Nunca digas que algo está
   "listo" o "probado" si no lo verificaste de verdad (ver la
   metodología de pruebas obligatoria más abajo — un chequeo de sintaxis
   no es una prueba).

Ante la duda de si algo está dentro del alcance de lo que se pidió, la
respuesta por defecto es **no**, y corresponde preguntar antes de
actuar — incluida la tentación de "ser útil" agregando algo no pedido.

## Qué es Mictlan

Bot de Telegram nuevo. Comparte varias funciones con ALFA-1 (repo
`FranEstAlv/samaritano-alfa1-init-estadomayor`, sub-incluido como `alfa1/`
en el repo OLIMPO) pero es un proyecto independiente, no una copia ni un
fork — "tendrá muchas de las funciones de alfa pero no será alfa" (palabras
textuales de Fernando).

- Repo: `github.com/FranEstAlv/Mictlan`
- Dueño: Fernando (FranEstAlv).
- Ya desplegado en producción en el mismo VPS (Contabo) que corre OLIMPO y
  HADES, vía `systemd` (`mictlan.service`) + PostgreSQL propio.
- Root de Telegram (ver regla fija abajo): `8513204887`.
- Grupo de gestión / admin (comparable al "OLIMPO admin"): `-1003939023898`.

## Regla fija: cero referencias a "súper administrador"

Ese término/concepto **no debe aparecer nunca** — ni en código, ni en
variables de entorno, ni en texto visible a ningún usuario. Es una
restricción explícita de Fernando, no una preferencia de estilo.

- El rol máximo se llama `root` (columna `usuarios.rol` en
  `mictlan/db.py`, jerarquía en `mictlan/roles.py`).
- **Patrón "silencio total"**: cualquier comando o callback restringido
  por rol y/o por chat responde con silencio absoluto si el chequeo
  falla — nunca un mensaje de error, nunca una pista de que esa función
  existe. Ya implementado en `mando.py` y `reporte.py`; replicarlo en
  toda superficie administrativa nueva.

### Regla ampliada (2026-09-01): ningún nombre de rol como texto plano en ningún panel

Extensión explícita de Fernando sobre la regla de arriba: no solo
"súper administrador" — **ningún nombre de rol** (`root`,
`administrador`, `vendedor`, ni siquiera `miembro`) debe aparecer como
texto plano en ningún mensaje o botón, en **ningún** panel/menú —
incluidos los que ya están gateados por rol (`/mando`, `/perfil`). El
motivo es no dejar evidencia textual explícita del nivel de permisos de
una cuenta ni siquiera en superficies ya protegidas por control de
acceso (una captura de pantalla, un log, o un mensaje reenviado no debe
poder usarse para identificar "esta cuenta es root").

- `roles.emoji_rol(rol)` (`mictlan/roles.py`) es el **único** punto que
  traduce un rol a algo visible — siempre un emoji (`EMOJI_ROL`:
  👤 miembro, 💼 vendedor, 🛠 administrador, 👑 root), nunca la palabra.
  Cualquier texto o botón que necesite mostrar el rol de alguien pasa por
  ahí, nunca interpola `{rol}`/`u['rol']` directo.
- Ya aplicado en `modules/perfil.py` (`/perfil`, visible a cualquier
  usuario sobre sí mismo) y `modules/mando/usuarios.py` (detalle de
  usuario, submenú "Cambiar rol" — antes los botones decían literalmente
  "root"/"administrador", la leyenda de la lista, y el mensaje de
  confirmación al cambiar rol).
- **Comparado contra el espejo de ALFA-1 antes de decidir el diseño**:
  ALFA-1 no tiene una regla escrita sobre esto, pero en la práctica su
  `/me` (equivalente a `/perfil`) omite el campo de rol por completo, y
  su `/staff` público jamás usa los nombres internos de rol
  (`admin`/`superadmin`/`seller`) — los recategoriza a etiquetas propias
  ("Admin/tratos", "Amigos"). Solo muestra el nombre de rol crudo en un
  panel ya protegido por control de acceso (`PANEL SETADMIN`). La regla
  de Mictlan es más estricta que la de ALFA-1: ni siquiera en paneles ya
  protegidos (`/mando`) se muestra el nombre — no se copió el patrón de
  ALFA-1 tal cual, se llevó más lejos a propósito.

## Regla prohibitiva: ALFA-1 es espejo, nunca código fuente

**PROHIBIDO copiar y pegar código de ALFA-1 a Mictlan tal cual.** Los
archivos listados en la sección siguiente se usan exclusivamente como
espejo — para comparar qué prometen los `.md` de Mictlan contra qué se
esperaba de verdad en producción en un bot comparable — nunca como
fuente de copy-paste ni como dependencia.

- **PROHIBIDO** importar o `include`-ar cualquier módulo de `alfa1/`
  dentro de `mictlan/`, ni siquiera "temporalmente".
- **PROHIBIDO** trasladar la estructura de carpetas, los nombres de
  archivo, o los nombres de comando de ALFA-1 a Mictlan — ya se decidió
  deliberadamente usar nombres y una organización distintos (ver
  "Paridad de comandos" en `PROGRESO.md`).
- **PROHIBIDO** asumir que un patrón es válido solo porque "así lo hace
  ALFA-1" — en particular, `core.py` es precisamente el antipatrón
  documentado en "Modularidad" más abajo, no un modelo a imitar.
- **PROHIBIDO** copiar texto de UI, mensajes al usuario, o strings
  literales de ALFA-1 — reescribir siempre para el tono y las
  convenciones propias de Mictlan.
- **Permitido y esperado**: leer estos archivos para entender la
  intención original de una función comparable, contrastarla con lo que
  el `.md` de Mictlan describe, y detectar huecos de diseño — pero la
  implementación se escribe siempre de cero, siguiendo las convenciones
  de este archivo (async/`asyncpg`, `install_xxx(app)`, `roles.py`,
  `mensajes.py`, silencio total, etc.), nunca calcada de ALFA-1.

### Archivos de ALFA-1 para usar como espejo

Rutas dentro del repo OLIMPO (mismo VPS, clonado aparte de Mictlan —
confirmar la ruta local exacta si hace falta, no asumirla). Se listan
solo los que ya demostraron tener contenido real y verificado, no toda
la carpeta:

**Documentación / decisiones de arquitectura:**
- `alfa1/ALFA1_MASTER.md`, `alfa1/CHANGELOG_MODULAR.md`,
  `alfa1/MODULARIZATION_NOTES.md` — panorama general y por qué se
  modularizó lo que se modularizó.
- `alfa1/docs/ALFA1_A16_SECURITY_CANON.md` — canon de seguridad
  aplicable a un bot de Telegram en general, no solo a ALFA-1.
- `alfa1/docs/ALFA1_A8_ROLES_PERMISSIONS.md`,
  `alfa1/ADMIN_COMMAND_INLINE_POLICY.md` — cómo pensaron roles/permisos
  y política de comandos administrativos por botones.
- `alfa1/docs/ALFA1_COMANDOS_STAFF.md` — catálogo completo de comandos
  de staff (ya generado en una sesión anterior), útil para comparar
  cobertura funcional, nunca para copiar nombres.

**SDK de módulos (para cuando se construya el de Mictlan):**
- `alfa1/samaritan/services/module_sdk.py` (411 líneas) — loader real,
  no el diseño en abstracto.
- `alfa1/docs/ALFA1_R2_31_8_25_MODULE_CONTRACT.md`,
  `alfa1/docs/ALFA1_R2_31_8_28_MODULE_SDK_CONTRACT.md`,
  `alfa1/docs/ALFA1_MODULE_MANIFEST_SCHEMA.md` — contrato real de
  permisos/scopes y formato de manifest.

**Grupos dinámicos:**
- `alfa1/samaritan/ops/dynamic_groups.py` (543 líneas) — implementación
  real de detección pasiva por mensaje (ver la decisión abierta en
  "Grupos dinámicos (plan)" más abajo).
- `alfa1/docs/ALFA1_R2_31_DYNAMIC_GROUPS.md`.

**Créditos (para cuando se construya el ledger auditado de Mictlan):**
- `alfa1/samaritan/credits/service.py` (306 líneas) — el ledger en sí.
- `alfa1/samaritan/credits/admin_panel.py`,
  `alfa1/samaritan/credits/commands.py`,
  `alfa1/samaritan/credits/install.py` — cómo se expone/administra.

**Mantenimiento / heartbeat / SOMBRA:**
- `alfa1/docs/ALFA1_A9_MAINTENANCE_MODE.md`,
  `alfa1/docs/ALFA1_A9_1_MAINTENANCE_CALLBACK_FIX.md`,
  `alfa1/docs/ALFA1_A10_HEARTBEAT.md`,
  `alfa1/docs/ALFA1_A11_SOMBRA_LINK.md`,
  `alfa1/docs/ALFA1_A12_SOMBRA_SIMULATOR.md`.
- `alfa1/future/SOMBRA_ARQUITECTURA_Y_BASE.md` — diseño completo de
  SOMBRA, ya leído en detalle (ver "Lo bueno" arriba).

**Bugs y errores reales (para no repetirlos, no para copiar el fix
literal):**
- `alfa1/future/ALFA1_BUGS_Y_GLITCHES.md`,
  `alfa1/future/ALFA1_CODIGO_CRITICO.md`.
- `alfa1/docs/ALFA1_A7_AUDIT_ERRORS.md`.
- `alfa1/docs/ALFA1_R2_24_PERMISSIONS_DESTINATIONS_AUDIT.md` — origen de
  la regla de separación de canales por propósito, arriba.

**El bug sin resolver (contexto, no solución):**
- `alfa1/samaritan/services/extra.py` — el archivo con el bug de
  búsqueda en CSV descrito en "Lo fallido — evitar". Se referencia para
  no repetir el patrón de búsqueda que falló, no porque tenga una
  solución que copiar (todavía no la tiene).

## Arquitectura y convenciones

- `main.py` — entrypoint. Arma la `Application`, hace `load_dotenv()`,
  registra cada módulo vía su `install_xxx(app)`.
- Paquete `mictlan/`: `db.py` (pool + esquema), `roles.py` (jerarquía y
  helpers de rol), `mensajes.py` (helper compartido de envío),
  `creditos.py` (ledger auditado), `canal.py`/`proxy.py`/`datos.py`/
  `almacen_modulos.py` (infraestructura del SDK, ver
  `CONTRATO_SDK_MODULOS.md`), `paginacion.py` (grilla 2×3 para paneles
  con listas de botones), `sdk/` (paquete del SDK de módulos externos,
  nunca un solo archivo — ver "Modularidad" abajo), y `modules/` con un
  archivo (o sub-paquete, ej. `modules/mando/`) por feature.
- **Convención `install_xxx(app)` por módulo** — deliberadamente calcada
  de la convención `install_*` de ALFA-1 porque Fernando ya está cómodo
  con ese patrón. Todo módulo nuevo debe seguirla.
- **PostgreSQL vía `asyncpg`** (pool asíncrono), elegido a propósito sobre
  SQLite — encaja con la naturaleza async del bot. Toda conexión pasa por
  `db.get_pool()`; nunca abrir una conexión suelta en código nuevo.
- **Roles**: `miembro (0) < vendedor (1) < administrador (2) < root (3)`,
  con `CHECK` constraint en Postgres restringiendo la columna a esos 4
  valores exactos. Comparar siempre con `roles.alcanza_rol(rol, minimo)`.
- **`asegurar_root(user_id)`** se corre en cada arranque (`_post_init` en
  `main.py`) y fuerza esa fila de la DB a `rol = 'root'` — la DB es la
  única fuente de verdad, pero un reinicio siempre re-fija el ID
  designado, aunque la fila hubiera sido alterada.
- **`mensajes.enviar_mensaje_servicio()`** es el único punto de salida
  para el primer envío de cualquier mensaje de servicio del bot — agrega
  automáticamente un botón "✖️ Cerrar" y agenda su autoborrado a los 30
  minutos (por mensaje, no por lote). Excepción: la navegación in-place
  dentro de un panel ya abierto (`query.edit_message_text`) NO pasa por
  ahí — no hay que duplicar el job de autoborrado — pero sí debe
  re-adjuntar el botón manualmente con `agregar_boton_cerrar()`.
- **Manejo de "message is not modified"**: todo `edit_message_text` debe
  capturar `telegram.error.BadRequest`, y si el texto en minúsculas
  contiene `"message is not modified"`, responder con
  `query.answer("Sin cambios ⏸")` en vez de tratarlo como error real;
  cualquier otro `BadRequest` se re-lanza. Patrón ya usado en
  `modules/mando/__init__.py` y `modules/reporte.py`.
- **Variables de entorno leídas de forma perezosa** (dentro del cuerpo de
  la función, no a nivel de módulo) cuando el valor viene de `.env` —
  `main.py` llama `load_dotenv()` después de sus propios imports de nivel
  superior, así que un `os.environ[...]` a nivel de módulo en un archivo
  importado correría antes de que `load_dotenv()` poblara el entorno en
  ejecuciones locales (no-systemd). Ver `ROOT_ID` en `main.py` y
  `ADMIN_GROUP_ID` en `modules/mando/__init__.py` como referencia.
- **Consola `/mando`**: un solo comando de entrada +
  `CallbackQueryHandler` con namespace `mando:`, dividida en sub-paquete
  (`modules/mando/__init__.py` como router + `usuarios.py`/`modulos.py`/
  `grupos.py`) apenas sumó una segunda sección real — ver "Modularidad"
  abajo. Prácticamente toda la funcionalidad administrativa vive ahí como
  botones, no como comandos de texto sueltos. Restringida a DM o al grupo
  de gestión (`ADMIN_GROUP_ID`) — cualquier otro chat, silencio total,
  sin importar el rol de quien escriba.
- **Comandos para miembros ordinarios**: deliberadamente pocos y cortos
  (`/start`, `/perfil`, `/reporte`; pendientes `/menu`, `/precios`).
  `/otorgar` es de staff (root), no de miembro.
- **Prefijos de `callback_data` reservados** (namespace por módulo, para
  que ningún módulo nuevo —interno o externo— pise el `callback_data` de
  otro): `mando:` (`modules/mando/`), `svc:` (`mensajes.py`, botón de
  cerrar), `reporte:` (`modules/reporte.py`). Todo módulo nuevo elige un
  prefijo propio que no empiece igual que estos — ver
  `CONTRATO_SDK_MODULOS.md` regla 6 para módulos externos.
- **Separación estricta de canales/chats por propósito**: un chat que
  recibe contenido para miembros (anuncios, referidos, etc.) nunca debe
  recibir también errores, logs, alertas o paneles administrativos, y
  viceversa. Lección directa de ALFA-1, que tuvo que auditar y corregir
  exactamente esta mezcla (`alfa1/docs/ALFA1_R2_24_PERMISSIONS_DESTINATIONS_AUDIT.md`).
  Hoy Mictlan solo tiene `ADMIN_GROUP_ID`, pero en cuanto se sumen un
  canal de difusión o un canal de logs, deben ser IDs distintos entre sí
  y del grupo de gestión — no asumir que "ya hay un grupo admin, sirve
  para todo".

## Modularidad: nunca un `core.py`

Chequeado directamente sobre el código real de ALFA-1 (no es un supuesto):
`alfa1/samaritan/core.py` tiene **14,874 líneas**, **486** funciones/métodos
definidos, **139** llamadas a `add_handler` y **una sola clase** — es decir,
prácticamente todo el bot (logging, acceso a datos, cada comando, cada
callback, cada flujo de conversación, toda la lógica de negocio) vive
apilado en un único archivo. Eso es exactamente lo que Mictlan tiene que
evitar, no como estética sino porque un archivo así es imposible de leer,
probar en aislamiento o tocar sin miedo a romper algo lejano.

Reglas concretas para no llegar a eso:

- Cada feature vive en su propio archivo dentro de `modules/`, y se
  registra a sí misma vía su propio `install_xxx(app)` — `main.py` solo
  llama a esos `install_xxx`, nunca contiene handlers ni lógica de
  negocio propia.
- Si un módulo crece más allá de las ~300-400 líneas o empieza a mezclar
  más de una responsabilidad clara (por ejemplo: la consola `/mando`
  ganando secciones para usuarios, grupos, créditos y módulos externos
  todas en `mando.py`), se convierte en un **sub-paquete**
  (`modules/mando/__init__.py` + `modules/mando/usuarios.py` +
  `modules/mando/grupos.py`, etc.) en vez de seguir creciendo como un
  solo archivo. El criterio no es la cuenta exacta de líneas, es si
  todavía se puede entender el archivo entero de una sentada.
- Ningún archivo debe terminar siendo el punto donde se registra *todo*
  el bot — ese es precisamente el problema de `core.py`. Si algún día un
  archivo de Mictlan empieza a acumular `add_handler` de features que no
  están relacionadas entre sí, es la señal de que hay que partirlo.
- El "Reporte de salud" en `PROGRESO.md` incluye un chequeo explícito de
  esto — ver esa sección.

**Dos precedentes reales ya aplicados, no solo la regla en teoría**:
`modules/mando/` (router + `usuarios.py`/`modulos.py`/`grupos.py`, cada
uno bajo 200 líneas) y `sdk/` (el antiguo `sdk.py` de 818 líneas dividido
en 13 archivos de una sola responsabilidad cada uno, ninguno arriba de
230 líneas — `excepciones.py`, `scopes.py`, `rutas.py`, `facades_proxy.py`,
`facades_creditos.py`, `facades_datos.py`, `facades_canal.py`,
`contexto.py`, `manifiestos.py`, `importador.py`, `recorders.py`,
`ciclo_vida.py`, `__init__.py` como fachada). Usar estos dos como
referencia de "cómo se ve bien dividido" antes de inventar una
estructura nueva.

## SDK de módulos externos (implementado)

**Construido, probado y documentado — ver `CONTRATO_SDK_MODULOS.md` (raíz
del repo) para el contrato completo, normativo, paso a paso.** Esta
sección queda solo como resumen de arquitectura; si algo de acá no
coincide con `CONTRATO_SDK_MODULOS.md`, ese documento manda.

- `mictlan/sdk/` (paquete, no un solo archivo — ver "Modularidad" abajo):
  descubre e importa módulos desde `external_modules/` (carpeta en
  `.gitignore` — cualquier módulo ahí se instala bajo el entendimiento de
  que no pasó revisión de código).
- Cada módulo externo expone `install_modulo(app, contexto)`. `contexto`
  (`ContextoModulo`) es un objeto acotado, **no** acceso directo a
  `db.py`/`roles.py` — expone `obtener_rol`/`registrar_usuario`/
  `enviar_mensaje_servicio`, y los facades `contexto.proxy`,
  `contexto.datos` (lectura de referencia + `contexto.datos.db`,
  persistencia propia real), `contexto.creditos` (ledger, sin `otorgar()`)
  y `contexto.canal`. **`contexto.captcha`/`contexto.sms` todavía NO
  existen** — groundwork sin decisión tomada (qué proveedor, uno activo o
  varios), ver `CONTRATO_SDK_MODULOS.md` §4 y §12.
- Guarda contra reimportación repetida (`_loaded: dict`, en
  `mictlan/sdk/ciclo_vida.py`) — activar/desactivar/reactivar nunca
  reimporta el `.py` del disco dos veces en el mismo proceso.
- Tabla `sdk_modulos` (`module_id`, `nombre`, `origen`, `activo`) —
  sección real "🧩 Módulos" dentro de `/mando`, paginada (ver
  "Modularidad" y el panel en `mictlan/modules/mando/modulos.py`):
  detectar/activar/desactivar/eliminar/alternar origen, todo en caliente,
  sin reiniciar el proceso. **Activar/desactivar sacan de verdad los
  handlers del `Application`** (`app.remove_handler(...)`) y cancelan los
  jobs programados — no es un simple guard que deja el handler registrado
  para siempre (ver comparación con el SDK de ALFA-1 más abajo).
- **Advertencia vigente para cualquier módulo, interno o externo**: nunca
  guardar estado sin límite en un `dict`/`list` a nivel de módulo. Si el
  estado necesita sobrevivir un restart, usar `contexto.datos.db`
  (persistencia real por módulo, `mictlan/almacen_modulos.py`), acotado
  por diseño de esquema, no un `dict` en RAM.
- **`permissions` son scopes, no comandos ni roles** — lección directa
  del SDK real de ALFA-1, que tuvo que parchear dos veces por manifests
  viejos que mezclaban comandos/roles ahí. `permissions` de Mictlan
  siempre fue solo scopes de acceso, la tabla completa está en
  `CONTRATO_SDK_MODULOS.md` §4.
- **El aislamiento de un módulo externo sigue siendo solo por convención,
  no por proceso** — un módulo corre en el mismo proceso que el bot y
  nada le impide técnicamente `os.system(...)` o leer `os.environ`
  directo. `ContextoModulo` nunca expone `app`/`db.get_pool()`/
  `os.environ` crudo, pero eso es disciplina de diseño, no una sandbox
  real. Sigue sin resolverse si hace falta un proceso separado para
  módulos de terceros no confiables — decisión pendiente, no asumir que
  ya está resuelta.
- **Comparación completa con el SDK real de ALFA-1** ya hecha (código +
  ~18 docs leídos completos, `mictlan-staging`, sesión 2026-09-01):
  hallazgo principal, el activar/desactivar de Mictlan ya es mejor que el
  de ALFA-1, que nunca logra sacar un handler de verdad del `Application`
  por asumir (incorrectamente) que python-telegram-bot no lo permite.

## Grupos dinámicos (implementado)

Decisión ya tomada y construida: `ChatMemberHandler` sobre
`my_chat_member` (evento real de alta/baja del bot en un chat), **no** la
detección pasiva por mensaje que usa ALFA-1
(`alfa1/samaritan/ops/dynamic_groups.py`). `ADMIN_GROUP_ID` sigue
existiendo aparte, fijo por variable de entorno — es el grupo de
*gestión* del root, no uno más de la tabla.

- Tabla `grupos`: `chat_id BIGINT PRIMARY KEY`, `nombre TEXT`, `tipo
  TEXT` (`'group'`/`'supergroup'`/`'channel'`/`'private'`), `activo
  BOOLEAN NOT NULL DEFAULT false`, `agregado_en TIMESTAMPTZ`, `principal
  BOOLEAN NOT NULL DEFAULT false` (agregada 2026-09-01 vía `ALTER TABLE
  ... ADD COLUMN IF NOT EXISTS` sobre la tabla ya existente — ver "Grupo
  principal y links de invitación" abajo).
- `mictlan/modules/grupos.py`: el handler + `listar()`/`activar()`/
  `desactivar()`. Cuando el bot es agregado a un chat nuevo, se inserta
  la fila con `activo = false` — que cualquiera lo meta a un grupo no le
  da poderes ahí, un administrador o root lo tiene que activar a
  propósito.
- `mictlan/modules/mando/grupos.py`: sección "🏘 Grupos" real dentro de
  `/mando`, lista paginada con activar/desactivar. Nunca borra la fila —
  eso no forma parte del contrato de esta sección.
- Cualquier feature futura que necesite actuar sobre "todos los grupos
  gestionados" (moderación masiva, difusión) recorre esta tabla filtrando
  por `activo = true`, en vez de un `chat_id` hardcodeado.

## Acciones de membresía en /mando (implementado)

Sección "👥 Usuarios" de `/mando` construida y probada en
`mictlan-staging` (2026-09-01) y portada acá el mismo día: pasó de una
lista de solo lectura a un panel paginado con detalle por usuario y
acciones reales.

- `mictlan/membresias.py`: `ajustar_dias(user_id, dias)` — botones
  +7/+30/-7/-30 en el detalle de usuario. `fin`/`inicio` son
  `TIMESTAMPTZ` reales; la aritmética de fechas es directa con
  `datetime`, sin parsear ni formatear texto a mano (a diferencia del
  adaptador SQLite de `mictlan-staging`, que sí necesita ese parseo
  porque ahí todo es `TEXT`). Restar días sin membresía previa es no-op;
  sumar días le crea una membresía nueva desde ahora.
- `roles.establecer_rol(user_id, rol)`: submenú "🎭 Cambiar rol" con las 4
  opciones.
- `mictlan/modules/mando/usuarios.py`: paginado (`mictlan/paginacion.py`,
  mismo criterio 2×3 que Módulos/Grupos), vista de detalle con rol,
  estado de membresía y estado de baneo.

## Baneo y lista negra (implementado)

Espejo del mecanismo real de ALFA-1 (`samaritan/services/global_moderation.py`,
`samaritan/ops/deslistar_command.py`), reescrito de cero — ver la regla
prohibitiva de espejo arriba. **"Banear" es exclusivamente expulsar (kick)
de todos los grupos/canales gestionados + guardar un reporte (motivo +
foto) para que un admin sepa por qué no debe volver a aceptar a ese
usuario.** Confirmado explícitamente por Fernando: esto es un mecanismo
**distinto** de una futura expulsión automática por membresía vencida —
esa es solo por tiempo, sin motivo, sin entrada en `blacklist`.

- Tablas `blacklist` (`user_id BIGINT PRIMARY KEY`, `motivo`,
  `foto_file_id`, `admin_id`, `creado_en TIMESTAMPTZ`, `activo BOOLEAN`) y
  `expulsiones` (insert-only, mismo patrón que `creditos_ledger`: una fila
  por cada grupo en el que se intentó expulsar a alguien, con el
  resultado real de esa llamada puntual a la API de Telegram; `tipo` es
  `TEXT` libre sin `CHECK` para no bloquear el futuro tipo
  `membresia_vencida`).
- `mictlan/moderacion.py`: `expulsar_de_todos_los_grupos()` /
  `reingresar_a_todos_los_grupos()` (recorren la tabla `grupos` completa,
  no filtran por `activo` — ese flag solo gatea paneles de administración,
  no si el bot es admin de verdad ahí) + CRUD de `blacklist`.
- **Guardia de reingreso**: `ChatMemberHandler.CHAT_MEMBER` — si un
  usuario en `blacklist` vuelve a entrar a cualquier grupo gestionado, se
  lo expulsa de inmediato ahí mismo. Necesitó `allowed_updates=Update.ALL_TYPES`
  en `main.py`/`app.run_polling()`: a diferencia de `my_chat_member`
  (alta del propio bot), Telegram no manda eventos `chat_member` por
  defecto.
- `mictlan/modules/mando/baneo.py`: `ConversationHandler` (motivo → foto)
  registrado en `main.py` **antes** de `install_mando(app)` — su entry
  point y el `CallbackQueryHandler` de "ver reporte" necesitan interceptar
  `mando:usuarios:banear:...`/`mando:usuarios:reporte:...` antes que el
  router genérico de `/mando` (mismo grupo de handlers, PTB solo corre el
  primero que matchea el `callback_data`). Sin texto libre salvo motivo +
  foto — es la única sección de `/mando` que usa una conversación en vez
  de solo botones, porque motivo y evidencia son inherentemente datos
  libres que no se pueden precargar como botones fijos.
- "✅ Desbanear" / "📋 Ver reporte" (reenvía la foto + motivo real) desde
  el detalle de usuario cuando ya está baneado.

## Grupo principal y links de invitación de un solo uso (implementado)

Antes de construir, revisado a fondo el mecanismo real de ALFA-1 (auto-
expulsión por tiempo, aprobación de ingreso + auto-expulsión si nadie
aprueba, links de invitación de un solo uso — los tres confirmados como
existentes en su código real). Fernando confirmó el diseño a adaptar:
**solo** auto-expulsión por membresía vencida (ver sección siguiente) y
links de invitación — la aprobación de ingreso con ventana de tiempo de
ALFA-1 quedó **explícitamente fuera**, no asumir que hay que construirla
solo porque el espejo la tiene.

- **Grupo principal**: `grupos.principal` (`BOOLEAN`, exclusivo — nunca
  dos a la vez, `establecer_principal()`/`obtener_principal()` en
  `mictlan/modules/grupos.py`). Marcado desde `/mando > Grupos` (botón
  "⭐ Marcar como principal" en el detalle de un grupo).
- **Links de un solo uso** (`mictlan/invitaciones.py`, tabla
  `invitaciones` insert-only — igual patrón que `creditos_ledger`):
  `create_chat_invite_link(chat_id, member_limit=1)`. Telegram mismo
  invalida el link tras el primer ingreso — **sin** listener de
  auto-revocación/rotación como tiene ALFA-1 (decisión explícita: solo
  el panel de generar/actualizar).
- **Dos flujos separados generan links, nunca el mismo para los dos
  casos**:
  - `/mando > Grupos`: root, **solo** para el grupo principal (botón "🔗
    Generar nuevo link" — solo visible en el detalle del grupo marcado
    como principal).
  - **Comando `/canales`** (nombre elegido para Mictlan — corto, nunca
    igual a `/invitar`/`/scrapper` de ALFA-1, regla de nombres
    respetada): cualquier miembro con `membresias.activa = true`, usado
    **dentro** del grupo principal (silencio total en cualquier otro
    chat), se autogenera un link a un grupo/canal **secundario** — nunca
    al principal, gateado también del lado del callback, no solo de la UI.

## Expulsión automática por membresía vencida (implementado)

`mictlan/vencimientos.py`: job vía `job_queue.run_repeating` cada 1 hora
(mismo ritmo que `auto_expel_expired_users` de ALFA-1) que expulsa a todo
usuario con `membresias.activa = true AND fin <= now()`. Confirmado
explícitamente por Fernando: expulsa de **todos** los grupos/canales
gestionados ("todo el ecosistema"), no solo el principal — reutiliza
`moderacion.expulsar_de_todos_los_grupos()` (el mismo mecanismo del
baneo) con `tipo='membresia_vencida'` en vez de `'baneo'` en la tabla
`expulsiones`.

- **Distinto de un baneo en todo sentido salvo el mecanismo de
  expulsión**: sin motivo, sin entrada en `blacklist`, nunca bloquea
  reingreso — si el usuario paga de nuevo y un admin le suma días
  (`/mando > Usuarios`), puede volver a entrar como cualquier otro. Ver
  "Baneo y lista negra" arriba para el mecanismo que sí bloquea.
- Tras expulsar, `membresias.desactivar(user_id)` marca `activa = false`
  — el job es idempotente, no vuelve a intentar expulsar a quien ya
  quedó desactivado.
- ALFA-1 tiene además un job diario de solo aviso (24h antes del
  vencimiento) — **no construido en Mictlan**, no se pidió.

## Mictlantecuhtli (implementado)

Segundo bot de respaldo/failover — nombre propio, **nunca** "SOMBRA" (el
nombre de ALFA-1). Fernando pidió explícitamente cubrir **todo** lo que
`alfa1/future/SOMBRA_ARQUITECTURA_Y_BASE.md` planteaba por escrito, no
solo la mitad de monitoreo pasivo que ALFA-1 llegó a construir de verdad
(ver "Lecciones de ALFA-1" más abajo para el detalle de esa diferencia).
Con tono neutral/técnico en todo momento.

- **Proceso completamente separado**: `mictlantecuhtli.py` (raíz del
  repo, sibling de `main.py`), su propia `Application`, su propio token
  (`MICTLANTECUHTLI_BOT_TOKEN`, vía @BotFather). Comunicación con el bot
  principal por **base de datos compartida** (misma `DATABASE_URL`),
  nunca una API HTTP nueva — es la opción más simple que el propio
  documento de ALFA-1 proponía, y no existe ningún servidor HTTP en
  ningún otro lugar de Mictlan.
- `mictlan/heartbeat.py` (instalado por el bot **principal**,
  `install_heartbeat(app)` en `main.py`): job cada
  `TECUHTLI_HEARTBEAT_INTERVAL_SEGUNDOS` (default 60s) que inserta en la
  tabla `heartbeats`, podada a las últimas 500 filas. El timestamp se
  calcula siempre en Python (`datetime.now(timezone.utc)`) y se pasa
  explícito — nunca `DEFAULT VALUES`/`now()` del lado de la DB, mismo
  criterio que `membresias.py`/`mantenimiento.py` (un bug real de esto
  se coló y se corrigió el mismo día: comparar un timestamp default de
  la DB contra un `datetime` consciente de zona horaria de Python
  revienta con `TypeError`).
- `mictlan/tecuhtli/` (paquete que corre en el proceso de
  Mictlantecuhtli):
  - `estado.py`: máquina de estados de 5 fases — consolidación
    deliberada de las 7 fases del documento de ALFA-1, que el propio
    documento aplica de forma inconsistente entre su texto narrativo y
    su pseudocódigo. `normal → alerta → critico → respaldo_activo →
    recuperacion_pendiente`. Umbrales por variable de entorno
    (`TECUHTLI_ALERTA_SEGUNDOS`=180, `TECUHTLI_CRITICO_SEGUNDOS`=480,
    `TECUHTLI_RESPALDO_SEGUNDOS`=900 — este último es el valor narrativo
    del documento original, "15 minutos", no el de su pseudocódigo con
    bug). **Consulta `mantenimiento.esta_en_mantenimiento()` antes de
    escalar** — si Mictlan está en mantenimiento deliberado, nunca
    escala; es el enganche que "Modo de mantenimiento" había dejado
    pendiente ("sigue sin existir un heartbeat que lo consulte de
    verdad").
  - `acciones.py`: `respaldo_activo` restringe (`set_chat_permissions`,
    `can_send_messages=False`) **todos** los grupos gestionados —
    reversible, nunca banea ni expulsa a nadie, a diferencia de
    `moderacion.py`.
  - `recuperacion.py`: comando `/reactivar` (root-only, mismo gate
    DM/`ADMIN_GROUP_ID` que `/mando`) — sin argumentos abre una ventana
    de `TECUHTLI_VENTANA_RECUPERACION_SEGUNDOS` (default 30s); con el
    secreto correcto (`TECUHTLI_SECRETO_RECUPERACION`) dentro de esa
    ventana, libera los grupos y vuelve a `normal`. `/tecuhtli_simular
    <fase>` fuerza una fase a mano (espejo simplificado del "simulador
    SOMBRA" de ALFA-1, sin tabla de historial de simulaciones aparte).
  - `evaluador.py`: job propio de Mictlantecuhtli (cada
    `TECUHTLI_EVALUAR_INTERVALO_SEGUNDOS`, default 30s) que ata todo lo
    anterior.
- **`respaldo_activo` es una fase "pegajosa"**: solo `/reactivar` con el
  secreto correcto puede sacarla de ahí — ni siquiera que el heartbeat
  del bot principal vuelva por su cuenta alcanza. Esto reemplaza el
  "contra-interrogatorio" que el propio código de ALFA-1 dejó sin
  terminar (comentario literal `# se implementará aquí`): en vez de un
  segundo secreto separado para "confirmar reintegración", cualquier
  salida de `respaldo_activo` exige siempre la misma confirmación
  humana explícita.
- **Desplegado de verdad en `mictlan-staging`** con un token real
  (`@respaldomictlanstagg_bot`), confirmado con `getMe()` — corre como
  proceso manual (`nohup`), no como servicio systemd todavía (la sesión
  de Claude Code que lo desplegó no tiene sudo para crear unidades
  nuevas). Ver `DESPLIEGUE_MICTLANTECUHTLI.md` (raíz del repo) para los
  comandos exactos de cómo convertirlo en un servicio real, incluidas
  las líneas de `visudo` para que una sesión futura pueda administrarlo.

## Proxies salientes vía DataImpulse (implementado)

Un solo lugar que sabe cómo salir a internet a través de DataImpulse —
`mictlan/proxy.py`, mismo nivel que `db.py`/`roles.py`. **Ya probado con
credenciales reales de DataImpulse en `mictlan-staging`**, no solo
diseñado.

```python
def obtener_proxy_url() -> str:
    return os.environ["DATAIMPULSE_PROXY_URL"]

def proxies_httpx() -> dict:
    url = obtener_proxy_url()
    return {"http://": url, "https://": url}
```

Lectura perezosa (dentro de la función, no a nivel de módulo) por la
misma razón que `ROOT_ID`/`ADMIN_GROUP_ID`. Expuesto también como
`contexto.proxy` para módulos externos vía el SDK (`proxy.usar`) — un
módulo de terceros nunca maneja sus propias credenciales de proxy.
`DATAIMPULSE_PROXY_URL` en `.env.example` es **opcional**: sin ella,
`contexto.proxy.url()` levanta `ProxyNoConfigurado`, pero el bot arranca
igual — solo hace falta si algún módulo la usa de verdad.

## Migraciones de esquema (plan)

Hoy `_SCHEMA` en `db.py` solo corre `CREATE TABLE IF NOT EXISTS` en cada
arranque — sirve para crear tablas nuevas, pero no para modificar una
tabla que ya existe en producción con datos reales. En cuanto haga falta
agregar una columna a `usuarios`/`membresias`, o a las tablas nuevas
(`grupos`, `sdk_modulos`, el futuro ledger de créditos), ese patrón no
alcanza.

Plan:

- `_SCHEMA` sigue sirviendo tal cual para tablas nuevas.
- Para cambios sobre tablas existentes, agregar sentencias
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` explícitas al final de
  `_SCHEMA` — Postgres las hace idempotentes, así que correr el esquema
  completo en cada arranque sigue siendo seguro.
- Antes de aplicar un cambio de esquema en el VPS: probarlo primero
  contra la DB descartable de pruebas (misma metodología de siempre). Si
  el cambio no es aditivo (renombrar o borrar una columna con datos ya
  cargados), avisar a Fernando y proponer los pasos en vez de aplicarlo
  directo — un `ALTER`/`DROP` destructivo sobre la base de producción
  nunca se corre sin confirmación explícita, sudo acotado o no.

## Logging propio de Mictlan (implementado)

`mictlan/logging_setup.py`: `configurar_logging()`, llamada en `main.py`
justo después de `load_dotenv()`. Sigue mandando a stdout (`journalctl`
funciona igual que antes) y además agrega un `RotatingFileHandler`
(5 MB, 3 backups) para no perder historial cuando el journal rota o se
llena.

- Guarda explícita contra duplicar handlers (`if root.handlers: return`)
  — mismo patrón que `OLIMPO/logging_setup.py`, con la misma lección
  aprendida ahí: sin esa guarda un logger termina duplicando cada línea.
  Adaptado, no copiado — `OLIMPO/logging_setup.py` no es ALFA-1, es un
  proyecto hermano del mismo Fernando, sirve como referencia de patrón
  igual que cualquier código propio ya probado.
- Ruta y nivel configurables por variable de entorno
  (`MICTLAN_LOG_PATH`, `MICTLAN_LOG_LEVEL`, ambas opcionales — default
  `mictlan.log` / `INFO`), leídas de forma perezosa dentro de la función.
- **Redacción de token en cualquier línea, sin importar el nivel**: el
  logger de `httpx`/`telegram` puede loguear la URL completa de cada
  request a la API de Telegram con el token embebido — se redacta antes
  de escribir a archivo o consola. Mismo riesgo que ya se había
  identificado en el logging propio de `mictlan-staging` (que corre en
  `TRACE`, mucho más verboso); acá aplica igual aunque el nivel por
  defecto sea `INFO`, por si alguna vez se sube a `DEBUG` en producción.

## Backups de PostgreSQL (plan)

No hay plan de respaldo/restauración documentado para la base de
Mictlan. Un fallo del VPS o un error humano — particularmente relevante
ahora que se habilita sudo sin contraseña para el servicio, ver política
de sudo más abajo — dejaría usuarios, membresías y reportes sin forma de
recuperarse.

Plan:

- `pg_dump` programado (cron o timer de systemd) de la base de Mictlan a
  un archivo comprimido con fecha, en una ruta fuera de la propia base
  (otro disco o, a futuro, almacenamiento externo).
- Retención simple: guardar N días y borrar los más viejos — definir N
  con Fernando, no asumirlo.
- Documentar acá mismo el procedimiento de restauración (`pg_restore` /
  `psql < dump.sql`) en cuanto se implemente, para que cualquier sesión
  sepa cómo recuperar sin improvisar en un momento de crisis.

## Bot de staging (plan)

Hoy solo existe un bot/token de Mictlan: el de producción, el mismo que
usan los miembros reales del grupo. El flujo de trabajo actual implica
probar cambios nuevos hablándole directamente a ese bot en Telegram.

Plan:

- Crear un segundo bot de Telegram (vía @BotFather) exclusivamente para
  pruebas, con su propio `TELEGRAM_BOT_TOKEN`.
- `.env` de staging separado (o un segundo servicio,
  `mictlan-staging.service`) apuntando a una base de staging propia —
  nunca a la base de datos de producción.
- Probar ahí antes de reiniciar el servicio de producción, sobre todo
  para cambios que toquen flujos delicados (moderación, créditos,
  membresías).

## Modo de mantenimiento (implementado)

Espejo del concepto de ALFA-1 (`samaritan/ops/maintenance.py`,
`alfa1/docs/ALFA1_A9_MAINTENANCE_MODE.md`), reescrito de cero. Construido
en `mictlan-staging` y portado acá el 2026-09-01. **Por diseño, igual que
el original: esto es SOLO un estado consultable — no detiene el bot, no
cierra grupos, no expulsa a nadie.** Sigue sin existir un heartbeat en
Mictlan que lo consulte; esta pieza queda lista para cuando se construya
esa fase (umbrales de alerta/crítico separados, ver referencia de ALFA-1
180s/480s, siguen siendo diseño futuro, no implementados).

- Tabla `mantenimiento`: ventanas (`activo BOOLEAN`, `iniciado_en`,
  `hasta`, `finalizado_en` — todos `TIMESTAMPTZ`, `motivo`, `admin_id`,
  `finalizado_por`). Solo la última fila (mayor `id`) importa para el
  estado actual; las anteriores quedan como historial. Activar una
  ventana nueva cierra cualquier ventana activa previa — nunca dos a la
  vez.
- `mictlan/mantenimiento.py`: `activar(minutos, admin_id)` (30 min / 2 h /
  indefinido si `minutos=None`), `desactivar(admin_id)`, `estado_actual()`
  (expira sola una ventana vencida), y `esta_en_mantenimiento()` — la
  función que una fase futura de heartbeat consultaría.
- Sección "🛠 Mantenimiento" en `/mando`: solo botones de duración fija
  (30 min / 2 h / Indefinido / Finalizar), sin texto libre — mismo
  criterio que ALFA-1 y que el resto de `/mando`.

## Permisos de sudo en el VPS (política)

La sesión de Claude Code que corre en el VPS tiene sudo sin contraseña,
pero **acotado a comandos específicos** vía un archivo en
`/etc/sudoers.d/` — nunca se le dio ni se le debe dar la contraseña real
de Fernando, ni acceso total (`ALL=(ALL) NOPASSWD: ALL`).

Alcance esperado (confirmar el contenido real del archivo en el VPS si
hay dudas, esto documenta la intención, no reemplaza revisarlo):

```
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl start mictlan.service
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl stop mictlan.service
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl restart mictlan.service
olimpo ALL=(root) NOPASSWD: /usr/bin/systemctl status mictlan.service
olimpo ALL=(root) NOPASSWD: /usr/bin/journalctl -u mictlan.service
```

Reglas para cualquier sesión que opere con este sudo acotado:

- Nunca pedirle a Fernando la contraseña de sudo, ni sugerirle que la
  pegue en un archivo, `.env`, o en el chat.
- Nunca ampliar el archivo de `/etc/sudoers.d/` por cuenta propia — si
  hace falta un comando nuevo en la lista, proponérselo a Fernando
  explícitamente para que lo agregue él mismo con `visudo`.
- Nada de `hades.service`, ni de la configuración compartida de
  PostgreSQL, entra en este sudo acotado — sigue aplicando la regla fija
  de `OLIMPO/CLAUDE.md` de no tocar HADES sin preguntar primero.
- Un comando destructivo (`DROP DATABASE`, borrar archivos de datos,
  etc.) nunca se corre solo porque el sistema operativo técnicamente lo
  permite — se sigue pidiendo confirmación explícita en el chat antes,
  sudo acotado o no.

## Metodología de pruebas (obligatoria, no negociable)

Este entorno tiene PostgreSQL 16 instalado pero **apagado por defecto**
(`pg_lsclusters` lo muestra "down" hasta que se arranca).

Antes de dar por terminada cualquier funcionalidad que toque la DB o el
flujo de un comando/callback:

1. `service postgresql start` (o `sudo service postgresql start`).
2. Crear un usuario/DB descartables: `CREATE USER mictlan_test WITH
   PASSWORD 'test123';` / `CREATE DATABASE mictlan_test OWNER
   mictlan_test;`.
3. Escribir un script de prueba real (venv temporal, `asyncpg` +
   `unittest.mock` para simular `Update`/`Context` de
   `python-telegram-bot`) que ejercite **todos** los caminos relevantes:
   permitido, bloqueado por rol, bloqueado por chat, casos límite (ID
   inexistente, doble acción, etc.) — no solo el camino feliz.
4. Correrlo contra la DB real y confirmar cada aserción.
5. Limpiar siempre: `DROP DATABASE`, `DROP USER`, borrar el venv
   temporal y el script de prueba.

**Un `py_compile` (chequeo de sintaxis) nunca sustituye la prueba
funcional.** No marcar una tarea de Mictlan como terminada sin haber
corrido pruebas reales contra Postgres.

**Aclaración de Fernando (2026-09-01)**: mientras se van portando
features sueltas al working tree de este repo desde `mictlan-staging`,
la prueba contra Postgres real de esta sección **se corre una sola vez
al final, integral, contra el Mictlan real** — no en cada porteo
individual. No marcar cada porteo con semáforo 🟡 por esto ni bloquear
el trabajo esperando sudo/DSN de Postgres en el medio; sí seguir
probando cada feature con la mejor alternativa disponible sin Postgres
real (sustituto de SQLite con tipos nativos cuando aplique, revisión a
mano de sintaxis Postgres-específica) y dejarlo anotado con precisión en
`PROGRESO.md`.

## Lecciones de ALFA-1

### Lo bueno — replicar

- Convención `install_*(app)` por módulo — aísla cada feature y la hace
  fácil de registrar/desregistrar.
- `CreditService` con ledger auditado (`alfa1/samaritan/credits/service.py`)
  — **construido en Mictlan** (`mictlan/creditos.py`, insert-only,
  probado con 5 cobros concurrentes contra un saldo que solo alcanza para
  4 en `mictlan-staging`), con una mejora deliberada sobre el propio
  ALFA-1: `contexto.creditos` del SDK nunca expone `otorgar()` — ver
  "SDK de módulos externos" arriba. (OLIMPO tiene su propio
  `creditos.py`, más simple y sin auditoría — ese sigue siendo el
  ejemplo a NO seguir.)
- Diseño de **SOMBRA** (segundo bot de respaldo/failover) documentado en
  `alfa1/future/SOMBRA_ARQUITECTURA_Y_BASE.md`. **Corrección
  (2026-09-02, investigación más profunda que la nota del 09-01 de más
  abajo)**: lo que SÍ está implementado de verdad en ALFA-1 es solo la
  mitad de **monitoreo pasivo** — `heartbeat.py` (407 líneas, job real
  que escribe latidos) y `sombra_link.py` (334, calcula el estado y lo
  expone en un panel de solo lectura dentro del propio ALFA-1).
  `sombra_simulator.py` (316) **solo simula** snapshots, no ejecuta
  ninguna acción real (confirmado por su propio footer:
  "No se ejecutó ninguna acción destructiva..."). El bot de respaldo
  **independiente**, el cierre de perímetro real, el comando de
  recuperación (`/comando`) y el "contra-interrogatorio" **nunca se
  construyeron** — quedaron solo en el `.md` (la propia tabla de la
  sección 9 del documento los marca con ❌). Construido en Mictlan el
  2026-09-02 — ver "Mictlantecuhtli (implementado)" más abajo: cubre
  todo lo que el documento de ALFA-1 planteaba por escrito, con tono
  neutral/técnico (nunca "Comando Conjunto"/"Protocolo Emboscada"/
  "Estado de Sitio") y nombre propio.

### Lo fallido — evitar

- `alfa1/samaritan/services/extra.py`: bug sin resolver — la búsqueda
  sobre un CSV de 83,000+ filas no encuentra valores más allá de ~3,000
  distintos. Causa raíz aún no confirmada (diagnóstico pausado esperando
  que Fernando corra `grep -n "^CODIGO,"` sobre una fila real que falle
  y pegue el resultado). Antes de escribir cualquier búsqueda sobre
  datasets grandes en Mictlan, revisar por qué falló ese patrón — no
  asumir que un `csv.DictReader` simple escala sin problema.
- Nombres de comando largos/genéricos (ej. `/moduleload`) — Mictlan usa
  nombres cortos, no genéricos, y explícitamente distintos a los de
  ALFA-1 (ver tabla de paridad en `PROGRESO.md`).
- Terminología "súper administrador" expuesta — prohibida en Mictlan (ver
  regla fija arriba).
- Mucha funcionalidad administrativa como comandos de texto sueltos en
  vez de una consola centralizada — Mictlan la centraliza en `/mando`
  con botones.
- Mensajes de servicio que se acumulan sin límite en el chat — resuelto
  en Mictlan con el botón de cerrar + autoborrado a los 30 min en todo
  mensaje de servicio (`mensajes.py`).
- **Bug real de parseo de listas de IDs desde variables de entorno**:
  ALFA-1 tuvo un caso donde una variable de IDs (`ADMIN_IDS` /
  `BATMAN_SUPER_ADMINS`) terminaba siendo un string en vez de
  lista/set, y `*list(string)` la descomponía en caracteres — así
  `"123456"` se interpretaba como los IDs `1, 2, 3, 4, 5, 6`, arriesgando
  acceso involuntario a `user_id=1`
  (`alfa1/future/ALFA1_BUGS_Y_GLITCHES.md` §4.3). `ROOT_ID` en Mictlan
  hoy es un único entero (`int(os.environ["ROOT_ID"])`), no afectado —
  pero si algún día se agrega una variable con una *lista* de IDs (por
  ejemplo varios administradores fijos), parsearla explícitamente
  (`[int(x) for x in valor.split(",")]`) y nunca asumir el tipo.
- **Capas de parches sobre un núcleo pueden dejar inertes los fixes
  hechos "donde parece lógico"**: el bug más grave documentado en todo
  ALFA-1 fue un módulo de compatibilidad (`rbac_bridge.py`) que
  sobreescribía en el arranque 8 funciones de permisos ya definidas en
  `core.py` — cualquier corrección hecha directamente en `core.py`
  quedaba sin efecto en runtime, y les tomó dos intentos fallidos
  entenderlo (`alfa1/future/ALFA1_BUGS_Y_GLITCHES.md` §2). Mictlan hoy
  no tiene capas de parcheo, pero si alguna vez se introduce una (por
  ejemplo, un módulo externo que quiera sobreescribir comportamiento de
  uno interno), hay que documentar sin ambigüedad cuál capa manda para
  cada función — nunca dejarlo implícito.

## Estado del proyecto y roadmap

Viven en `PROGRESO.md`, no acá — se actualiza en cada sesión de trabajo,
mientras que este archivo describe la arquitectura/reglas, que cambian
poco. Leer ambos antes de empezar.

## Cómo saber si Mictlan va por buen camino

Ver la sección "Reporte de salud" en `PROGRESO.md`. Toda sesión nueva
debe:

1. Leer este archivo y `PROGRESO.md` completos antes de tocar código.
2. Revisar la última entrada de "Reporte de salud": si el semáforo no es
   🟢, resolver lo pendiente (o dejarlo explícitamente documentado como
   conocido) antes de sumar funcionalidad nueva.
3. Al cerrar una tarea: correr las pruebas reales (ver metodología
   arriba), actualizar "Avances hechos" / "Lo que falta" en
   `PROGRESO.md`, y agregar una entrada nueva de "Reporte de salud"
   fechada, siguiendo el formato exacto que ahí se especifica.

## Infraestructura de despliegue

- VPS Contabo, compartido con OLIMPO y HADES (ver `OLIMPO/CLAUDE.md` en
  el repo OLIMPO para contexto de esos otros proyectos si hace falta —
  Mictlan es independiente de ambos).
- `systemd`: `mictlan.service` (`After=network.target postgresql.service`,
  `EnvironmentFile=.env`, `Restart=on-failure`).
- `.env` (nunca commiteado — ver `.env.example`):
  `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `ROOT_ID`, `ADMIN_GROUP_ID`, y
  opcional `DATAIMPULSE_PROXY_URL` (solo si algún módulo usa
  `contexto.proxy`, ver "Proxies salientes vía DataImpulse").
- Base de datos PostgreSQL propia de Mictlan, en la misma instancia de
  Postgres del VPS que usa HADES — es "territorio de HADES" así que
  cualquier cambio a la configuración compartida de Postgres (no la
  creación de una DB/rol aislados nuevos, que no toca los datos de
  HADES) se coordina como cortesía con Chack0071 antes de actuar.
- Después de cualquier cambio: `git pull`, revisar si `.env` necesita una
  variable nueva (ver changelog en `PROGRESO.md`), y recién ahí
  `sudo systemctl restart mictlan.service`.
