# PROGRESO.md — Mictlan

Bitácora viva del proyecto. Se actualiza en cada sesión de trabajo — ver
`CLAUDE.md` para arquitectura, reglas fijas y metodología de pruebas
(eso casi no cambia; esto sí).

## Avances hechos (changelog)

Commits más recientes primero. Cada línea corresponde a una tarea que se
probó contra PostgreSQL real antes de pushear (ver metodología en
`CLAUDE.md`) — si alguna vez se rompe esa regla, debe quedar anotado acá
y en el "Reporte de salud" correspondiente.

- `a0dcfbd` — **`/reporte`**: quejas de miembros al grupo de gestión, con
  botón "Atendido" (solo `administrador`/`root`), tabla `reportes` con
  auditoría (quién, qué, cuándo, quién lo atendió). Probado: 17
  escenarios reales.
- `c72e44d` — **`/mando` restringido**: solo responde en DM o en el grupo
  de gestión (`-1003939023898`); silencio total en cualquier otro chat.
  Probado: 10 escenarios reales (comando + callback, root/no-root,
  DM/grupo admin/otro chat).
- `87a965a` — **Fase 2, esqueleto de `/mando`**: consola admin por
  botones, gate de rol `root` con silencio total, primera sección real
  "👥 Usuarios" (últimos 20 registrados, con membresía). Navegación
  menú↔lista, manejo de "message is not modified".
- `eb3baf2` — **`/perfil`**: agrega el ID de Telegram visible en el
  panel.
- `65e5e8b` — **Botón de cerrar + autoborrado**: infraestructura
  compartida (`mensajes.py`) retrofitteada en `/start` y `/perfil`; todo
  mensaje de servicio nuevo la hereda automáticamente.
- `dd14933` — **Fase 1, cimientos**: pool de PostgreSQL (`asyncpg`),
  tablas `usuarios`/`membresias`, `roles.py` (jerarquía + `asegurar_root`),
  `/perfil` (info + perfil + saldo unificados, según indicación explícita
  de Fernando de que "los 3 son información personal").

Desplegado y confirmado corriendo en el VPS por Fernando ("Ya está
levantado") desde la Fase 1.

## Esqueleto portado al working tree del repo real (2026-09-01, sin commitear)

**Importante — esto NO son commits todavía.** `git status` en este repo
muestra los archivos de abajo como modificados/nuevos, sin agregar ni
commitear — a propósito, para que Fernando revise el diff completo antes
de decidir si se commitea. Nada de esto tocó `/home/olimpo/mictlan`
(el proceso real en producción, `mictlan.service`) ni se pusheó a
`origin/main`.

Fernando pidió explícitamente portar "todo el avance que se lleva hasta
ahora" desde `mictlan-staging` a este repo, **excluyendo los módulos de
prueba** (`external_modules/` de staging — `eco`, `malo`, `trivia`,
`compartir`, `proxycheck`, `consulta1/2/3`, `csvbuscador`, `panelpub`,
`publicadorprod`, `orquestador`, `creditos_demo` — ninguno se copió,
existían solo para probar capacidades del SDK, no como funcionalidad
real). También se excluyó a propósito `contexto.captcha`/`contexto.sms`
(groundwork en staging, bloqueado por una decisión de Fernando sin
tomar) y sus scopes — no se portó nada que dependiera de una decisión
pendiente.

### Qué se portó

- **`mictlan/db.py`**: esquema extendido con 4 tablas nuevas
  (`sdk_modulos`, `grupos`, `publicaciones_modulo`, `creditos_ledger`),
  traducidas a tipos Postgres reales — no una copia del esquema SQLite de
  staging. `chat_id`/`user_id` son `BIGINT` (no `INTEGER`): los IDs de
  supergrupo/canal de Telegram (formato `-100xxxxxxxxxx`) exceden el
  rango de un `INTEGER` de 32 bits de Postgres — un bug real que se
  hubiera colado portando literal.
- **`mictlan/creditos.py`** (ledger), **`canal.py`**, **`datos.py`**,
  **`almacen_modulos.py`**, **`proxy.py`**, **`paginacion.py`**,
  **`formato.py`** — portados, casi todos verbatim porque el código de
  negocio de staging ya estaba escrito en sintaxis compatible con
  `asyncpg` (`db.get_pool()` con `$1`/`fetchval`/`fetchrow` es
  exactamente la API real de `asyncpg.Pool`, no una coincidencia — fue
  diseño deliberado desde el día 1 de `mictlan-staging`, confirmado
  ahora en la práctica).
- **`mictlan/sdk/`** como paquete (11 archivos, no un `sdk.py` de una
  pieza) — mismo split que ya se hizo en staging, sin `facades_externos.py`
  completo: solo se portó `ProxyFacade` (renombrado `facades_proxy.py`);
  `CaptchaFacade`/`SmsFacade` quedaron afuera (ver exclusión de arriba).
- **`mictlan/modules/grupos.py`** + **`mictlan/modules/mando/`**
  (reemplaza el `mando.py` de un solo archivo — ahora
  `__init__.py`/`usuarios.py`/`modulos.py`/`grupos.py`, con paginación
  2×3 en Módulos y Grupos).
- **`mictlan/modules/creditos.py`** (`/otorgar`), **`perfil.py`**
  (saldo real en vez del placeholder `$0.00`), **`main.py`** (registra
  `sdk.descubrir_e_instalar`, `install_grupos`, `install_creditos`,
  cierra `almacen_modulos` al apagar).
- **`requirements.txt`** (+ `aiosqlite`, para el almacén propio de
  módulo), **`.gitignore`** (+ `external_modules/`, `datos_compartidos/`),
  **`.env.example`** (+ `DATAIMPULSE_PROXY_URL`, opcional).
- **`CONTRATO_SDK_MODULOS.md`** (nuevo, raíz del repo) — contrato
  normativo completo: estructura de carpeta, `manifest.json` exacto,
  tabla completa de scopes, API método por método de `ContextoModulo`
  (incluida `contexto.datos.db`), 8 reglas duras, checklist paso a paso,
  ejemplo mínimo funcional, y una sección final de "qué falta" para que
  nadie asuma que `captcha`/`sms` ya existen. Reemplaza cualquier nota
  de sesión anterior sobre el SDK como fuente de verdad.

### Correcciones que salieron de portar con cuidado, no copiar y pegar

- `mictlan/modules/creditos.py` capturaba `sqlite3.IntegrityError`
  (staging) para el caso de otorgar créditos a un `user_id` no
  registrado — en Postgres real es `asyncpg.ForeignKeyViolationError`.
  Confirmado que la clase existe de verdad en el paquete `asyncpg`
  instalado (no solo supuesto).
- El comentario del `asyncio.Lock` del ledger de créditos
  (`_LEDGER_LOCK`) decía "alcanza porque hay una sola conexión SQLite" —
  ya no aplica con un pool real de múltiples conexiones de Postgres. Se
  reescribió con la razón correcta: el `Lock` serializa la **sección
  crítica de Python** (un único proceso, un único event loop), no las
  conexiones de la base en sí — sigue siendo válido con un pool, pero
  dejaría de alcanzar si Mictlan corriera en múltiples procesos/workers
  algún día (anotado explícitamente en el comentario para que no se
  asuma que escala solo).
- `almacen_modulos.py` perdió su import de `_traducir` desde `db.py`
  (ese helper existía en el `db.py` de staging porque *ahí* la base
  principal también era SQLite; el `db.py` real es `asyncpg` puro y
  nunca lo tuvo). Se movió `_traducir` directo a `almacen_modulos.py` —
  sigue haciendo falta porque el almacén *propio* de cada módulo sigue
  siendo SQLite a propósito, aunque la base principal ya no lo sea.

### Límite honesto de las pruebas — no se probó contra PostgreSQL real

Esta sesión de Claude Code no tiene credenciales ni sudo para administrar
PostgreSQL en este entorno (el sudo disponible está acotado solo a
`systemctl`/`journalctl` de `mictlan-staging.service`, confirmado
intentando `sudo -u postgres psql` y leer `pg_hba.conf` — ambos
rechazados). Por eso **no se cumplió la metodología de pruebas
obligatoria de este mismo archivo** tal cual está escrita ("PostgreSQL
16 instalado... `CREATE USER`/`CREATE DATABASE`"). Lo que sí se hizo,
para no reportar esto como "probado" sin serlo:

- Revisión manual de la sintaxis Postgres del esquema nuevo (tipos,
  `CHECK`, `BIGINT` vs `INTEGER`).
- Confirmado por import directo que `asyncpg.ForeignKeyViolationError`
  existe y es subclase de `asyncpg.PostgresError`.
- 20 aserciones de **lógica Python** (roles, ledger con 5 cobros
  concurrentes contra un saldo que alcanza para 3, `contexto.creditos`
  sin `otorgar()`, grupos con `chat_id` negativo grande, paginación,
  ciclo de vida completo de un módulo de prueba real activado/desactivado,
  scope peligroso `db.raw` rechazado) corridas con un *shim* SQLite
  temporal — mismo mecanismo que ya usa `mictlan-staging`, parcheando en
  memoria `mictlan.db.get_pool()`, borrado al terminar. Valida la
  lógica de Python, **no** valida que el DDL de Postgres corra de verdad
  ni el comportamiento real de `asyncpg` más allá del chequeo de la
  excepción.

**Pendiente antes de commitear/pushear esto**: correr la prueba real
contra PostgreSQL (`service postgresql start`, `CREATE USER`/`CREATE
DATABASE` descartables, script de prueba real, `DROP` al final) — hace
falta hacerlo desde una sesión con sudo completo o que Fernando comparta
un DSN de prueba.

### Compilación verificada

`python -m py_compile` sobre los ~33 archivos `.py` del repo — limpio.
Dependencias instaladas en un venv temporal (`requirements.txt` +
`aiosqlite`) para confirmar que `import telegram, asyncpg, aiosqlite,
dotenv` funciona sin conflictos de versión — venv borrado al terminar.

### Porteos adicionales el mismo día (2026-09-01, sesiones de continuación)

Después del porteo inicial de arriba, se construyó más en
`mictlan-staging` y se portó al working tree el mismo día, mismo patrón
(nunca commiteado, mismas correcciones de tipo TEXT/SQLite → TIMESTAMPTZ/
Postgres explicadas abajo). Detalle completo de cada uno en "Avances en
el ambiente de staging" y en el "Reporte de salud":

- **Acciones de membresía en `/mando`** (días/rol) + **baneo y lista
  negra** (`mictlan/membresias.py`, `mictlan/moderacion.py`,
  `modules/mando/usuarios.py` reescrito con paginado/detalle,
  `modules/mando/baneo.py` — único `ConversationHandler` de todo
  `/mando`). Tablas nuevas: `blacklist`, `expulsiones`.
- **Modo de mantenimiento** (`mictlan/mantenimiento.py`,
  `modules/mando/mantenimiento.py`). Tabla nueva: `mantenimiento`.
- **Grupo principal, links de invitación de un solo uso, expulsión
  automática por membresía vencida** (`mictlan/invitaciones.py`,
  `mictlan/vencimientos.py`, `mictlan/modules/canales.py` — comando
  nuevo `/canales`, `modules/grupos.py`/`modules/mando/grupos.py`
  ampliados con `principal`). Tabla nueva: `invitaciones`, columna nueva
  `grupos.principal` (primera migración real de columna sobre una tabla
  ya existente, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`).
- `main.py` terminó registrando, además de lo del porteo inicial:
  `install_baneo` (antes de `install_mando`, ver motivo en
  `modules/mando/baneo.py`), `install_canales`,
  `moderacion.install_moderacion`, `vencimientos.install_vencimientos`, y
  `app.run_polling(allowed_updates=Update.ALL_TYPES)` (antes sin
  argumento — necesario para que lleguen los eventos `chat_member`).
- **Logging propio** (`mictlan/logging_setup.py`, 2026-09-01, construido
  directo acá, sin pasar por staging — ver esa entrada de "Reporte de
  salud" para el motivo).

### Porteo del 2026-09-02: Mictlantecuhtli

- **Mictlantecuhtli** (segundo bot de respaldo/failover, nombre propio —
  ver "Mictlantecuhtli (implementado)" en `CLAUDE.md` para el diseño
  completo): `mictlantecuhtli.py` (raíz, entrypoint separado de
  `main.py`), `mictlan/heartbeat.py` (instalado por el bot principal),
  `mictlan/tecuhtli/` (paquete: `estado.py`, `acciones.py`,
  `evaluador.py`, `recuperacion.py`). Tablas nuevas: `heartbeats`,
  `tecuhtli_estado`.
- Cubre todo lo que ALFA-1 planteó por escrito para "SOMBRA" (no solo la
  mitad de monitoreo pasivo que llegó a construir de verdad — ver
  investigación completa en "Lecciones de ALFA-1" y en la propia sección
  de `CLAUDE.md`), con tono neutral/técnico.
- **Bug real encontrado y corregido en el porteo**: `heartbeat.py`
  dependía de `DEFAULT VALUES`/`now()` del lado de la DB para
  `creado_en`, en vez de calcularlo en Python como el resto del código
  — la prueba de lógica del repo real lo hizo explotar de verdad
  (`TypeError: can't subtract offset-naive and offset-aware datetimes`).
  Corregido en ambos repos (staging y real) para pasar siempre un
  `datetime` explícito.

## Avances en el ambiente de staging (`mictlan-staging`, sin commitear)

**Importante — separación física, confirmada por Fernando (2026-09-01):**
`/home/olimpo/mictlan-staging` es un ambiente de pruebas descartable, no el
Mictlan real. El Mictlan real corre en `/home/olimpo/mictlan`
(`mictlan.service`, Postgres). Este repo (`Mictlan/`, clonado dentro de
`mictlan-staging/` solo como referencia de `CLAUDE.md`/`PROGRESO.md`) no
es el código que ejecuta el bot de staging — ese vive en
`mictlan-staging/mictlan/` (minúscula, **fuera de este repo git**, no
tiene historial de commits). Por eso todo lo de acá abajo no aparece en
el changelog de arriba: nunca se comiteó, es válido que se rompa, y la
idea explícita de Fernando es portarlo "poco a poco" al Mictlan real
cuando se valide en pruebas — no de una sola vez.

Corre como `mictlan-staging.service` (systemd, `EnvironmentFile=.env`
propio, `Restart=on-failure`), con su propio bot/token de Telegram y su
propia base de datos. Confirmado activo y sano el 2026-09-01 (revisión de
sesión: journal sin errores, polling normal).

### Base de datos: SQLite (`aiosqlite`), no Postgres

`mictlan-staging/mictlan/db.py` es una adaptación manual del `db.py` real
(Postgres/`asyncpg`) a SQLite — decisión deliberada y documentada en el
propio archivo ("no es el `db.py` real de Mictlan... la decisión de
Postgres para producción sigue firme"). Traduce sintaxis `$1`/`now()` de
Postgres a `?`/`CURRENT_TIMESTAMP` de SQLite. Mismo esquema base
(`usuarios`, `membresias`, `reportes`) más **3 tablas que todavía no
existen en el `db.py` real**:
- `sdk_modulos` (module_id, nombre, origen interno/externo, activo).
- `grupos` (chat_id, nombre, tipo, activo, agregado_en) — para el plan de
  "Grupos dinámicos" de `CLAUDE.md`.
- `publicaciones_modulo` (module_id + destino como clave compuesta,
  chat_id, botón texto/url, activo, periodicidad, plantilla, csv) — config
  de a qué grupo/canal publica cada módulo, con varios destinos posibles
  por módulo.

### SDK de módulos externos: gestión completa en caliente desde `/mando` (2026-09-01, sesión de continuación)

`mictlan-staging/mictlan/sdk.py` descubre e instala módulos desde
`external_modules/` (fuera de git, igual que el diseño de OLIMPO), con
`ContextoModulo` exponiendo scopes reales (`contexto.proxy` ya probado
contra DataImpulse real). Esta sesión pasó de "instala todo lo que
encuentra en el arranque" a un ciclo de vida real, gestionable sin
reiniciar el proceso:

- **`sincronizar_registro()`** — escanea el disco y registra cualquier
  módulo nuevo como **inactivo por defecto**. Antes el flag `activo` de
  `sdk_modulos` no controlaba nada de verdad (se pisaba a `True` en cada
  arranque — bug corregido esta sesión); ahora sí es la fuente de verdad
  de qué corre.
- **`activar_modulo(app, id)` / `desactivar_modulo(app, id)`** — agregan o
  sacan de verdad los handlers (y los jobs de `job_queue`, vía un
  wrapper que intercepta `run_repeating`/`run_once`/`run_daily` y los
  cancela con `schedule_removal()`) del `Application` que ya está
  corriendo. No reimporta el `.py` del disco si el módulo ya se cargó una
  vez en este proceso.
- **`eliminar_modulo(app, id)`** — desactiva + borra la fila de
  `sdk_modulos`. El archivo sigue en `external_modules/`, así que el
  próximo "🔍 Detectar módulos" lo vuelve a encontrar como nuevo
  (inactivo).
- **`alternar_origen(id)`** — cambia la etiqueta `interno`/`externo` en la
  DB (solo bookkeeping para marcar candidatos "graduados" a portar a
  mano; no mueve archivos ni cambia cómo se carga).
- Sigue rechazando scopes peligrosos (`db.raw`, `shell.exec`, etc.) con
  `PermisoNoConcedido` antes de instalar — confirmado en vivo con el
  módulo `malo`.

**UI nueva: `/mando` → 🧩 Módulos.** `mictlan/modules/mando.py` se dividió
en sub-paquete (`mando/__init__.py` como router + `usuarios.py` +
`modulos.py`) apenas sumó esta segunda sección real, siguiendo la regla
de modularidad de `CLAUDE.md` ("si mando.py gana secciones... se
convierte en sub-paquete"). Lista con estado (✅/⛔ activo, 🧪/🏠
externo/interno, ⚠️ si falta la carpeta en disco), vista de detalle por
módulo con botones Activar/Desactivar, Marcar interno/externo y Eliminar
(con pantalla de confirmación), y "🔍 Detectar módulos" para re-escanear
sin reiniciar.

**Probado de verdad, no solo compilado** (metodología de `CLAUDE.md`,
adaptada a SQLite): script contra un SQLite temporal + una `Application`
real de `python-telegram-bot` (sin red), 24 aserciones — activar agrega
el handler real al `Application`, desactivar lo saca, reactivar no
reimporta, `malo` se rechaza y queda inactivo, un módulo con `job_queue`
(`publicadorprod`) programa y cancela su job correctamente, eliminar +
re-detectar funciona, y las 4 vistas de la UI (lista/detalle/error/
confirmación) generan texto+teclado correctos. Desplegado con
`sudo systemctl restart mictlan-staging.service` (sudo acotado) — journal
limpio, los 11 módulos reales que ya estaban activos siguieron activos
sin interrupción, `malo` quedó correctamente inactivo.

**12 módulos externos registrados hoy: 11 activos + `malo` inactivo**
(rechazado a propósito). Ver el catálogo completo de qué hace cada uno
más abajo.

### Catálogo unificado de comandos — todos los módulos activos hoy en staging

Referencia única de qué existe y qué hace cada cosa en el bot de staging
ahora mismo, para no tener que releer código cada vez que haga falta
saber "¿esto ya existe?". Cubre internos (cargados directo por `main.py`,
sin pasar por el SDK) y externos (vía SDK, todos de prueba/demostración —
ninguno es funcionalidad real de cara a un usuario final todavía).

**Internos (`mictlan/modules/`, acceso directo a `db.py`/`roles.py`, sin
permisos de SDK):**

| Comando / sección | Quién | Qué hace |
|---|---|---|
| `/start` | cualquiera | mensaje de bienvenida fijo |
| `/perfil` | cualquiera (se autoregistra) | ID, rol, membresía, **saldo real** (`creditos.saldo()`, ya no placeholder) |
| `/reporte <texto>` | cualquiera (se autoregistra) | queja al grupo de gestión con botón "✅ Atendido" (admin/root), tabla `reportes` auditada (quién, qué, cuándo, quién atendió) |
| `/mando` → 👥 Usuarios | root, solo DM o grupo de gestión | últimos 20 usuarios registrados + estado de membresía |
| `/mando` → 🧩 Módulos | root, solo DM o grupo de gestión | detectar/activar/desactivar/eliminar/alternar origen de los módulos del SDK (ver sección de arriba); lista paginada 2 columnas × 3 filas (6 por página) desde 2026-09-01 |
| `/mando` → 🏘 Grupos | root, solo DM o grupo de gestión | **nuevo esta sesión** — lista paginada (2×3) de grupos/canales auto-registrados por `my_chat_member`, activar/desactivar cada uno; nunca borra la fila |
| `/otorgar <user_id> <cantidad> [motivo]` | root, solo DM o grupo de gestión | **nuevo esta sesión** — único punto del bot que puede acuñar créditos (`creditos.otorgar()`), ver "Ledger de créditos" arriba |
| (automático, evento `my_chat_member`) | — | alta pasiva de grupo en la tabla `grupos`, siempre inactivo hasta que un admin lo prenda a propósito |
| botón ✖️ Cerrar (todo mensaje de servicio) | cualquiera | borra el mensaje; autoborrado también a los 30 min si nadie lo cierra antes |

**Externos (`external_modules/`, vía SDK — cada uno con sus permisos
declarados en `manifest.json`). 11 activos, `malo` y `creditos_demo`
inactivos (el primero a propósito, el segundo por ser recién detectado —
falta activarlo desde el panel), 13 con carpeta en disco:**

| module_id | Comandos | Qué hace | Notas técnicas |
|---|---|---|---|
| `eco` | `/eco <texto>` | repite el texto + el rol de quien lo llamó | módulo mínimo de referencia del SDK |
| `malo` | (ninguno — nunca llega a instalarse) | pide `db.raw`/`shell.exec`; el SDK lo rechaza (`PermisoNoConcedido`) antes de importar el código | control negativo: confirma que el SDK filtra scopes peligrosos |
| `proxycheck` | `/proxyinfo`, `/proxytest` | muestra la URL de proxy configurada (password enmascarada) y hace un `GET` real a `ipify.org` a través de DataImpulse | primer módulo que probó `contexto.proxy` con credenciales reales |
| `consulta1` / `consulta2` / `consulta3` | `/c1`, `/c2`, `/c3` | busca un código en el CSV compartido (`productos.csv`) + lee una tabla SQLite propia de cada módulo, mide tiempos de ambas vías | 3 copias casi idénticas a propósito — prueban que 3 módulos distintos cacheando el mismo CSV en memoria no interfieren entre sí |
| `csvbuscador` | `/buscarcodigo`, `/buscarsql`, `/datospesado`, `/datosconcurrente` | busca en un CSV de 500k filas (lineal, sin índice) vs. SQLite; `/datospesado` verifica 4 "filas trampa" contra el valor exacto esperado (una replica el límite del bug de 83k filas de `extra.py` en ALFA-1); `/datosconcurrente` lanza 20 búsquedas SQL en paralelo con `asyncio.gather` | la prueba más pesada de `contexto.datos` — confirma con datos reales de 500k filas que el patrón de búsqueda que falló en ALFA-1 no se repite acá |
| `trivia` | `/trivia`, `/triviatop` + botones | preguntas de opción múltiple con botones, puntaje por usuario, ranking top 5 | **actualizado 2026-09-01**: puntaje (aciertos/intentos) ya persiste vía `contexto.datos.db`, sobrevive un restart; solo la sesión de pregunta activa (`estado.py`) sigue en memoria a propósito, ver "Persistencia propia de módulo" abajo |
| `compartir` | `/compartir` (respondiendo a una foto) | verifica que la foto sea de quien la comparte, bloquea duplicados por `file_unique_id`, publica en **todos** los destinos activos del módulo a la vez, cuenta publicaciones por usuario | espejo deliberado de `refe_command` de ALFA-1 (comportamiento, nunca código ni texto); **actualizado 2026-09-01**: contador por usuario y deduplicación de fotos ya persisten vía `contexto.datos.db` |
| `panelpub` | `/pub`, `/panelpub` + panel de botones | 3 "personalidades" de publicación en un solo módulo: `canal` (por evento, como `/pub`), `grupo` (programado), `ambos` (canal+grupo simultáneo, `asyncio.gather`) — todo configurable por botones (CSV/campo, periodicidad, on/off), sin tocar código; listas de CSV/campos paginadas 2×3 desde 2026-09-01 | pensado a propósito para estresar concurrencia: dos jobs de `job_queue` corriendo cerca uno del otro |
| `publicadorprod` | (sin comando, solo programado) | cada 60s revisa si ya pasó `periodicidad_minutos` desde la última publicación y, si corresponde, publica un producto al azar del CSV compartido | primer módulo 100% automático (sin interacción de usuario) del SDK |
| `orquestador` | `/svcstatus`, `/svcflujo`, `/svc2captcha`, `/svccapsolver`, `/svcanticaptcha` | `/svcstatus`: chequea proxy + los 3 proveedores de captcha + los proveedores de SMS **en paralelo** (`asyncio.gather`, reintentos solo en errores de red); `/svcflujo`: cadena real con decisión dinámica (consulta saldo de los 3 captcha en paralelo, elige el de mayor saldo, resuelve un captcha real con ESE proveedor) | el módulo que más lejos llevó `contexto.proxy`/`contexto.captcha`/`contexto.sms` a la vez |
| `creditos_demo` | `/saldo`, `/comprar` + botones Confirmar/Cancelar | **nuevo esta sesión** — cobra 10 créditos reales vía `contexto.creditos.cobrar()`, con pantalla de confirmación (saldo antes→después en el texto) y revalidación server-side antes de cobrar | primer módulo que ejercita `contexto.creditos` de punta a punta; inactivo por defecto, activar desde `/mando` → 🧩 Módulos para probarlo |

Los 3 huecos reales documentados arriba (`contexto.db`, ledger de
créditos, `contexto.captcha` sin construir) siguen siendo los mismos —
confirmado leyendo el código completo de los 12 módulos en esta sesión:
`trivia` y `compartir` son los dos casos concretos que hoy pierden su
estado en cada restart por falta de `contexto.db`. **Actualización
2026-09-01: el hueco de créditos ya se resolvió, ver más abajo. Segunda
actualización 2026-09-01, sesión de continuación: el hueco de
`contexto.db` también se resolvió — ver "Persistencia propia de módulo
(contexto.datos.db)" más abajo. De los 3 huecos originales del SDK solo
queda `contexto.captcha`, bloqueado por la decisión abierta de Fernando
(ver esa sección).**

### Comparación completa con el SDK real de ALFA-1 (2026-09-01)

Sesión dedicada a leer completo el SDK de módulos de ALFA-1 (repo OLIMPO,
`alfa1/`): `samaritan/services/module_sdk.py` (411 líneas),
`module_runtime.py` (968 líneas), `module_loader.py` (257),
`module_audit_service.py` (182), `modules_panel.py` (475),
`module_contract.py` (173), más ~18 documentos y las dos guías HTML de
construcción de módulos (v1/v2). Objetivo: confirmar qué de nuestro
diseño ya es sólido y qué vale la pena adoptar de ahí antes de seguir
construyendo.

**Hallazgo más importante — nuestro activar/desactivar ya es mejor que el
de ALFA-1, no al revés.** El propio código de ALFA-1 asume una premisa
falsa (`module_runtime.py:942-944`): *"PTB no permite remover handlers en
runtime; el toggle envuelve los callbacks."* `Application.remove_handler()`
sí existe y lo confirmamos funcionando con pruebas reales esta misma
sesión (ver la sección de SDK arriba). Por esa premisa incorrecta, ALFA-1
nunca saca un handler de verdad: envuelve cada callback en un guard que,
si el módulo está "inactivo", no hace nada — pero el handler **sigue
registrado para siempre**. Consecuencias concretas:
- **No existe "eliminar módulo" en ALFA-1** — en 968 líneas de
  `module_runtime.py` ninguna función desregistra un handler. Una vez
  cargado, vive en el proceso hasta el próximo restart.
- **Cero manejo de jobs programados** al desactivar — sin equivalente a
  nuestro `_JobQueueRecorder`/`schedule_removal()`.
- **Todo el estado activo/inactivo es en memoria** (`_LOADED_MODULES`,
  `_MODULE_ENABLED_STATE`), se pierde en cada restart — hay que
  recargar módulo por módulo a mano. Nuestra tabla `sdk_modulos` persiste
  esto sin intervención.

**Panel de administración — feature por feature contra
`/mando` → 🧩 Módulos:**

| Acción | ALFA-1 (`modules_panel.py`) | Nosotros |
|---|---|---|
| Detectar/listar | ✅ | ✅ (y persiste en DB) |
| Activar | ✅ (una vez, no reversible del todo) | ✅ (real, reversible) |
| Desactivar | ✅ (guard, handler sigue registrado) | ✅ (real, saca handlers + cancela jobs) |
| Eliminar | ❌ no existe | ✅ (con confirmación) |
| Marcar interno/externo | ❌ (no tienen ese concepto) | ✅ |
| Auditoría de acciones del admin sobre módulos | ❌ tampoco lo tienen | ❌ (hueco compartido, sin resolver) |
| Servicio de auditoría para que el módulo loguee sus propias acciones de negocio | ✅ `module_audit_service.py`, JSONL con redacción de tokens | ❌ no existe (`contexto.audit`, candidato a futuro) |

**Aislamiento real — más débil en ALFA-1 de lo que se pensaba.** No se
pudo confirmar la cita original de `CLAUDE.md` a
`ALFA1_CODIGO_CRITICO.md §8.1` (ese archivo no tiene esa sección numerada
sobre aislamiento — probablemente viene de una síntesis de otra sesión).
Pero se encontró algo más concreto y peor: `ctx.application`/`ctx.app` se
expone **sin envolver** a cualquier módulo (`module_sdk.py:314`), y la
guía oficial de construcción de módulos le enseña explícitamente a un
autor a hacer `bot_data.get("credit_service")` para cobrar créditos — un
atajo documentado que rodea el sistema de permisos por completo, con
acceso a `mint()` incluido. Nuestro `ContextoModulo` nunca expone
`app`/`application` crudo, así que no tenemos ese boquete específico —
confirmado y explotado a propósito en el diseño del ledger nuevo (ver
abajo).

**Cómo resuelve ALFA-1 los huecos que teníamos:**
- `contexto.db`: no lo resolvieron con una fachada tampoco — la regla
  oficial es que cada módulo abra su propio SQLite directo, sin gate del
  SDK. El único módulo real que necesitaba persistencia (`smspool.py`)
  **nunca fue tratado como módulo externo sandboxed** — vive en código
  core con acceso total. Ni ellos lograron persistencia real dentro del
  sandbox.
- Ledger de créditos: nunca se construyó tampoco (confirmado como
  "pendiente" en 3 documentos distintos). Sí dejan un principio de diseño
  limpio que adoptamos: **nunca exponer `mint()` a un módulo externo**,
  solo `spend`/`get_balance` — reembolsos son manuales por admin. Ese
  principio es la base del ledger que se construyó esta sesión.
- Captcha: sin equivalente en ALFA-1, nada que comparar.

**Candidatos a portar, en orden de impacto/esfuerzo** (el primero y el
tercero ya se ejecutaron esta sesión, ver más abajo):
1. ~~Permitir escritura en `contexto.datos.abrir_sqlite_propio()`~~ —
   **todavía pendiente**, sigue siendo el camino más barato para
   `contexto.db`.
2. `contexto.audit` — servicio de auditoría append-only para que un
   módulo loguee sus propias acciones. Pendiente.
3. ~~Nunca exponer `mint()`/acuñar crédito a un módulo externo~~ —
   **aplicado** en el diseño de `contexto.creditos` (ver abajo).
4. Pantalla de confirmación con saldo antes→después antes de cualquier
   cobro (saldo siempre en texto, nunca en botón) — **aplicado** en
   `creditos_demo`, pendiente fijarlo como regla dura en
   `GUIA_SDK_MODULOS_EXTERNOS.md` para cualquier módulo futuro.
5. No adoptar el patrón de "toggle por guard sin sacar el handler" — nota
   dejada acá mismo para que nadie "simplifique" hacia ese patrón más
   adelante.
6. Un test que confirme que `ContextoModulo` nunca expone
   `app`/`db.get_pool()`/`os.environ` crudo. Pendiente.
7. Checklist de guardas defensivas contra `None` (`(x or {}).get(...)`
   encadenado) para sumar a `GUIA_SDK_MODULOS_EXTERNOS.md`. Pendiente.

### Ledger de créditos: construido y probado (2026-09-01)

Resuelve el hueco #2 de arriba. Diseño deliberadamente asimétrico,
directo de la lección de ALFA-1 de la sección anterior: el código interno
puede acuñar créditos, un módulo externo **nunca**.

- **`mictlan/creditos.py`** (nuevo, mismo nivel que `db.py`/`roles.py`) —
  ledger insert-only: la tabla `creditos_ledger` nunca se pisa, el saldo
  de un usuario siempre se deriva de `SUM(delta)`, nunca se guarda como
  columna aparte. `saldo()`, `otorgar()` (acuñar — código interno
  solamente), `cobrar()` (revalida el saldo real dentro del mismo
  `asyncio.Lock` que el insert, nunca confía en un saldo leído antes),
  `reembolsar()` (solo del propio módulo, nunca de otro, nunca dos veces
  el mismo `tx_id`), `historial()`.
- **`contexto.creditos` en `sdk.py`** (`CreditosFacade`) — expone
  `saldo()`, `cobrar()`, `reembolsar()`. **Nunca `otorgar()`** — ni
  siquiera está importado en la clase, no es solo un scope sin conceder.
  2 scopes nuevos: `creditos.leer_saldo`, `creditos.cobrar`.
- **`/otorgar <user_id> <cantidad> [motivo]`** (nuevo,
  `mictlan/modules/creditos.py`) — único punto del bot que puede acuñar
  créditos, root + mismo chat que `/mando` (DM o grupo de gestión).
  Otorgar a un `user_id` no registrado falla con un mensaje claro (antes
  daba `sqlite3.IntegrityError` crudo por la FK a `usuarios`).
- **`/perfil`** — ya no muestra el placeholder `$0.00`, ahora es el saldo
  real vía `creditos.saldo()`.
- **`external_modules/creditos_demo/`** — módulo de prueba end-to-end:
  `/saldo`, `/comprar` (pantalla de confirmación con saldo antes→después
  en el texto, nunca en un botón, siguiendo el candidato #4 de arriba),
  cobra de verdad vía `contexto.creditos.cobrar()`. Igual que cualquier
  módulo nuevo, quedó **inactivo por defecto** tras el reinicio — hay que
  activarlo desde `/mando` → 🧩 Módulos para probarlo en Telegram.

**Probado de verdad** (metodología de `CLAUDE.md`, adaptada a SQLite): 20
aserciones contra un SQLite temporal + una `Application` real — saldo
inicial en 0, otorgar/cobrar/reembolsar en los caminos felices, cobrar
más del saldo disponible rechazado sin tocar el saldo, otorgar a un
`user_id` inexistente rechazado por la FK, reembolsar dos veces el mismo
`tx_id` rechazado, un módulo reembolsando el cobro de otro módulo
rechazado, historial ordenado correctamente, **5 cobros concurrentes
contra un saldo que solo alcanza para 4 — exactamente 4 pasan, ninguno se
duplica** (confirma que el `asyncio.Lock` evita double-spend), el módulo
externo real `creditos_demo` activado vía `sdk.activar_modulo()` cobrando
y reembolsando de verdad a través de `contexto.creditos`, y que
`contexto.creditos` sin el scope correspondiente se rechaza con
`PermisoNoConcedido`. Desplegado con
`sudo systemctl restart mictlan-staging.service` — journal limpio, los 11
módulos que ya estaban activos siguieron activos, `creditos_demo` se
detectó correctamente como nuevo (inactivo).

### Persistencia propia de módulo (`contexto.datos.db`): construida y probada (2026-09-01, sesión de continuación)

Resuelve el hueco #1 restante (`contexto.db`) — pedido explícito de
Fernando de "resolver el hueco de persistencia de memoria, considerando
peticiones de muchos usuarios al bot, cada uno con sus datos por
separado, tareas independientes" y que "los módulos, sean cuantos sean,
deban poder guardar sus datos y mantener persistencia para no perder
nada de los usuarios". La guía original (`GUIA_SDK_MODULOS_EXTERNOS.md`)
proponía el scope `db.propio`, pero `db.` está en
`SCOPES_PREFIJOS_PELIGROSOS` (bloqueado a propósito) — de ahí el nombre
real, dentro del mismo namespace que los otros scopes de `datos`.

- **`mictlan/almacen_modulos.py`** (nuevo) — un archivo SQLite propio y
  privado **por módulo** (`external_modules/<id>/estado/estado.db`,
  carpeta separada a propósito de `datos/` que ya usan `consulta1/2/3`
  para sus `.db` de solo lectura, para no colisionar nombres de archivo).
  Una conexión `aiosqlite` real (async de verdad, nunca bloquea el event
  loop) por módulo, abierta una sola vez y reusada toda la vida del
  proceso — mismo espíritu que el `_pool` único de `db.py`. Modo **WAL** +
  `synchronous=NORMAL`: cada commit sobrevive un crash del proceso sin
  dejar el archivo a medias. Cada módulo tiene su **propio
  `asyncio.Lock`** (nunca uno global) para secciones críticas
  leer-y-decidir, mismo patrón que `_LEDGER_LOCK` de `creditos.py` pero
  aislado — un módulo con mucho tráfico nunca hace esperar a otro sin
  relación.
- **`contexto.datos.db`** (`AlmacenPropioFacade` en `sdk.py`) —
  `execute/fetch/fetchrow/fetchval/executescript` (misma sintaxis
  `$1`/`now()` que `db.py`) + `.bloqueo` (el candado del módulo, para
  envolver un `async with` alrededor de cualquier lectura-y-decisión).
  Scope nuevo **`datos.escribir_propio`**, deliberadamente separado de
  `datos.leer_propio` (ese sigue siendo solo para los archivos de
  referencia que un admin coloca a mano) — dos niveles de privilegio
  distintos.
- Aislamiento **físico**, no solo de permiso: cada módulo tiene su propio
  archivo en disco, así que ni siquiera un bug de otro módulo puede leer
  o pisar estos datos.

**Migrados a persistencia real, los dos casos concretos que
`PROGRESO.md` ya señalaba** (ver catálogo de arriba, actualizado):
`trivia` (puntaje aciertos/intentos por usuario; la sesión de pregunta
activa se queda deliberadamente en memoria, es un puntero efímero a un
mensaje concreto en pantalla, no hay nada real que perder ahí) y
`compartir` (contador de publicaciones por usuario + deduplicación de
`file_unique_id`). Ambos manifests suman el scope `datos.escribir_propio`.

**Probado de verdad** (22 aserciones, SQLite real + `Application` real de
`python-telegram-bot`, sin red): aislamiento físico entre dos módulos
(archivos `.db` distintos, uno no ve las filas del otro), `journal_mode`
confirmado en `wal`, **50 escrituras concurrentes de "usuarios" distintos
contra el mismo módulo, con el candado propio → 0 perdidas** (control
negativo: las mismas 50 escrituras SIN candado sí pierden datos,
confirma que el candado es necesario y no decorativo), un módulo lento
(candado retenido 0.3s) nunca hace esperar a otro módulo sin relación,
`contexto.datos.db` rechaza con `PermisoNoConcedido` a un módulo sin el
scope (y confirma que `datos.leer_propio` por sí solo no alcanza —
privilegios separados de verdad), y la prueba central: **`trivia` y
`compartir` reales, activados vía `sdk.activar_modulo()`, con datos de 2
usuarios independientes, sobreviven un "restart" simulado completo**
(conexiones cerradas + los 4 diccionarios de caché del SDK vaciados +
módulos reimportados desde cero) — el puntaje de cada usuario y la
deduplicación de fotos siguen exactamente iguales después. Desplegado
con `sudo systemctl restart mictlan-staging.service` — journal limpio,
los 11 módulos que ya estaban activos (incluidos `trivia`/`compartir` con
el permiso nuevo) siguieron activos sin errores.

### Paginación 2×3 en paneles con listas de botones (2026-09-01, sesión de continuación)

Pedido explícito de Fernando: reducir botones por pantalla en el panel de
carga de módulos (13 entradas, un botón por fila, quedaba larguísimo) y
aplicar la misma regla a cualquier otro panel con listas de botones —
grilla de **2 columnas × 3 filas (6 ítems) por página**, con paginado
cuando hace falta más de una.

- **`mictlan/paginacion.py`** (nuevo, ~55 líneas) — helper compartido:
  `total_paginas()`, `pagina_valida()` (acota sola si la lista encogió,
  ej. tras borrar un ítem, o si llega un número de página inválido de un
  `callback_data` viejo), `filas()` (recorta y acomoda en la grilla 2×3) y
  `fila_controles()` (fila ⬅️/📄 X de Y/➡️, `None` si todo entra en una
  sola página). El botón del medio (número de página) apunta a sí mismo
  — tocarlo solo la vuelve a mostrar, así no hace falta un
  `callback_data` `noop` aparte que un router tenga que interceptar.
  Importable directo tanto desde código interno como desde un módulo
  externo (mismo precedente que `mictlan.mensajes`/`mictlan.formato`, ya
  importados directo por `panelpub.py`) — es un helper de UI, no un
  recurso privilegiado que necesite pasar por `contexto`/scopes.
- **`/mando` → 🧩 Módulos** (`mictlan/modules/mando/modulos.py`) —
  reescrito para paginar la lista. La página viaja embebida en el
  `callback_data` de cada botón "ver" (`mando:mod:ver:<module_id>:<pagina>`),
  así "⬅️ Volver" desde el detalle de un módulo regresa a la página
  exacta de origen, no siempre a la primera. El router
  (`mictlan/modules/mando/__init__.py`) se simplificó para pasarle a
  `modulos.py` toda la cola del `callback_data` en vez de solo
  `accion`/`module_id` fijos — cada sección sigue parseando lo suyo, el
  dispatcher central no necesita conocer el formato de paginación de
  ninguna.
- **`panelpub`** (el otro panel con listas dinámicas reales) — lista de
  CSVs de `datos_compartidos/` y lista de campos de un CSV, ambas
  paginadas igual. La lista fija de periodicidad (`PERIODOS_MIN`, 5
  opciones) también se acomodó en grilla 2 columnas por consistencia,
  aunque con 5 no llega a necesitar una segunda página.
- **Deliberadamente sin tocar**: paneles que son un puñado fijo de
  acciones distintas entre sí, no una colección que pueda crecer (menú de
  `/mando`, menú de `panelpub`, pantallas de confirmar/cancelar, opciones
  de `trivia`) — paginar ahí no tendría sentido, cada botón es una acción
  distinta, no un ítem intercambiable de una lista.

**Probado de verdad** (33 aserciones, SQLite real + `Application` real de
`python-telegram-bot`): el helper `paginacion.py` aislado (conteo de
páginas para 0/6/7/13 ítems, recorte exacto de la grilla 2×3, controles
⬅️/➡️ correctos en primera/media/última página); el panel de Módulos con
13 filas reales insertadas en `sdk_modulos` — página "1/3" correcta, 3
filas de 2 columnas, navegar a "pagina:1" muestra "2/3" con controles
Anterior+Siguiente, el primer módulo de la página 2 es el esperado
(`fake06`), "Volver" desde su detalle apunta de vuelta a
`mando:mod:pagina:1` (no a la página 0), y al eliminar módulos hasta
quedar en 6 (una sola página) los controles de paginación desaparecen
solos; y `panelpub._teclado_csv_archivos`/`_teclado_csv_campos` con 9/8
ítems traen los controles `csvpagina`/`campopagina` esperados, mientras
que `_teclado_periodo` (5 opciones) no trae controles pero sí queda en 2
columnas. Desplegado con `sudo systemctl restart mictlan-staging.service`
— journal limpio, los 11 módulos activos (incluido `panelpub`, que ahora
importa `mictlan.paginacion`) siguieron activos sin errores.

### Sección "🏘 Grupos" de `/mando`: UI de gestión construida y probada (2026-09-01, sesión de continuación)

Avance del roadmap grande (ítem "Grupos dinámicos reales" en "Lo que
falta" más abajo) — Fernando eligió seguir con esto tras revisar las
opciones pendientes. La detección automática ya existía y estaba
confirmada (`mictlan/modules/grupos.py`, `ChatMemberHandler` sobre
`my_chat_member`, decisión ya tomada — ver "Grupos dinámicos (plan)" en
`CLAUDE.md`): un grupo nuevo se registra solo, siempre **inactivo** hasta
que alguien lo prenda a propósito. Lo que faltaba era la UI para
listar/activar/desactivar — no existía ninguna pantalla, había que tocar
la tabla `grupos` a mano.

- **`mictlan/modules/mando/grupos.py`** (nuevo, sub-paquete de `/mando`,
  mismo patrón que `usuarios.py`/`modulos.py`) — lista paginada (grilla
  2×3, reusa `mictlan/paginacion.py`) con ✅/⛔ por grupo, vista de
  detalle con botón Activar/Desactivar. Nunca borra una fila de
  `grupos` — no se pidió, y el archivo de referencia (`modules/grupos.py`)
  tampoco expone esa operación. Mismo truco de `modulos.py` para que
  "⬅️ Volver" regrese a la página de origen, no siempre a la primera (la
  página viaja embebida en el `callback_data` de cada botón).
- **`/mando` → 🏘 Grupos** agregado al menú principal
  (`mando/__init__.py`), junto a 👥 Usuarios y 🧩 Módulos — mismo gate de
  rol `root` + chat permitido (DM o grupo de gestión) que las otras dos
  secciones, sin duplicar el chequeo dentro de `grupos.py` (confía en el
  gate del router, igual que `modulos.py`).

**Probado de verdad** (15 aserciones, SQLite real + `Application` real de
`python-telegram-bot`, sin red): un grupo se auto-registra disparando el
`my_chat_member` real (no un atajo de prueba — el mismo camino que
dispara un admin agregando el bot a un chat de verdad), queda inactivo
por defecto, aparece en el panel nuevo con el botón correcto, activarlo
desde la UI persiste de verdad en la tabla `grupos` (confirmado leyendo
la fila después, no solo el texto de respuesta), el botón de acción
cambia de "Activar" a "Desactivar" y viceversa, desactivarlo lo saca de
`listar(solo_activos=True)`, "Volver" preserva la página de origen, 9
grupos reales muestran 2 páginas correctas, y pedir un `chat_id`
inexistente cae de vuelta a la lista con un aviso claro, sin traceback.
Desplegado con `sudo systemctl restart mictlan-staging.service` —
journal limpio, los 11 módulos activos siguieron activos sin errores.

### Acciones de membresía en `/mando`: días, rol, baneo/lista negra (2026-09-01, sesión de continuación)

Sección "👥 Usuarios" de `/mando` pasó de una lista de solo lectura (top
20, sin acciones) a un panel paginado con detalle por usuario:

- `mictlan/membresias.py`: `ajustar_dias(user_id, dias)` — botones
  +7/+30/-7/-30. Sin membresía previa, restar es no-op; sumar crea una
  nueva desde ahora.
- `roles.establecer_rol(user_id, rol)` — submenú "🎭 Cambiar rol" con las
  4 opciones.
- **Baneo, revisado a fondo contra el espejo de ALFA-1** a pedido
  explícito de Fernando (`samaritan/services/global_moderation.py`,
  `samaritan/ops/deslistar_command.py`, `samaritan/core.py`
  `list_command`/`list_reason_handler`/`list_image_handler`), reescrito
  de cero. Fernando aclaró explícitamente la semántica antes de construir:
  "banear" = expulsar (kick) de **todos** los grupos/canales gestionados +
  generar un reporte (motivo + foto) para no volver a aceptar a ese
  usuario — **distinto** de una futura expulsión automática por
  membresía vencida (esa es solo por tiempo, sin motivo, sin blacklist).
  - Tablas nuevas `blacklist` y `expulsiones` (insert-only, mismo patrón
    que `creditos_ledger`).
  - `mictlan/moderacion.py`: `expulsar_de_todos_los_grupos()` /
    `reingresar_a_todos_los_grupos()` + CRUD de `blacklist`, y una
    **guardia de reingreso** (`ChatMemberHandler.CHAT_MEMBER`) que
    re-expulsa de inmediato si un usuario en blacklist vuelve a entrar a
    cualquier grupo gestionado. Requirió sumar
    `allowed_updates=Update.ALL_TYPES` a `app.run_polling()` — Telegram no
    manda eventos `chat_member` (a diferencia de `my_chat_member`) si no
    se piden explícitamente.
  - `mictlan/modules/mando/baneo.py`: único `ConversationHandler` de todo
    `/mando` (motivo → foto) — el resto de la consola es 100% botones.
    Registrado en `main.py` antes de `install_mando(app)` para interceptar
    su `callback_data` antes que el router genérico.
  - "✅ Desbanear" / "📋 Ver reporte" desde el detalle de usuario ya
    baneado.
- **Probado funcionalmente de verdad en `mictlan-staging`**: 36
  aserciones — SQLite temporal + una `Application` real de
  `python-telegram-bot` sin red, incluido el `ConversationHandler`
  completo (callback → motivo → foto → blacklist + expulsión real de 3
  grupos mockeados), cancelación a mitad de flujo, y "ver reporte"
  enviando la foto real. Desplegado con
  `sudo systemctl restart mictlan-staging.service`, journal limpio, los
  11 módulos reales siguieron activos.

### Modo de mantenimiento (2026-09-01, sesión de continuación)

Espejo del concepto de ALFA-1 (`samaritan/ops/maintenance.py`), reescrito
de cero. Por diseño, igual que el original: **solo un estado
consultable** — no detiene el bot, no cierra grupos, no expulsa a nadie.
Mictlan todavía no tiene ningún heartbeat que lo consulte; esta pieza
queda lista para cuando se construya esa fase.

- Tabla `mantenimiento`: ventanas (`activo`, `iniciado_en`, `hasta`,
  `finalizado_en`, `motivo`, `admin_id`, `finalizado_por`). Activar una
  ventana nueva cierra cualquier ventana activa previa — nunca dos a la
  vez. Solo la última fila importa para el estado actual.
- `mictlan/mantenimiento.py`: `activar(minutos, admin_id)` (30 min / 2 h /
  indefinido), `desactivar(admin_id)`, `estado_actual()` (expira sola una
  ventana vencida), `esta_en_mantenimiento()`.
- Sección "🛠 Mantenimiento" en `/mando`: solo botones de duración fija,
  sin texto libre — mismo criterio que ALFA-1.
- **Probado funcionalmente**: 24 aserciones contra SQLite real — activar
  por tiempo fijo, indefinido, expiración automática, nunca dos ventanas
  activas, finalizar manual, y el panel completo. Desplegado de verdad,
  journal limpio, 11 módulos activos sin interrupción.

### Grupo principal, links de invitación de un solo uso y expulsión automática por membresía vencida (2026-09-01, sesión de continuación)

Fernando pidió explícitamente revisar el espejo de ALFA-1 antes de
construir (auto-expulsión por tiempo, aprobación de ingreso + expulsión
si nadie aprueba, links de invitación de un solo uso — los tres
confirmados como existentes en ALFA-1, con detalle real de código) y
después dio el diseño concreto a adaptar: **solo** auto-expulsión por
membresía vencida y links de invitación (la aprobación de ingreso con
ventana de 1 minuto de ALFA-1 quedó explícitamente fuera, no se pidió).

- **Concepto nuevo: "grupo principal"** — `grupos.principal` (`BOOLEAN`,
  exclusivo — nunca dos a la vez, `mictlan/modules/grupos.py`
  `establecer_principal()`/`obtener_principal()`). Botón "⭐ Marcar como
  principal" en el detalle de `/mando > Grupos`. Es la primera migración
  real sobre una tabla ya existente con datos (`grupos`) — probada de
  verdad contra la base persistente de `mictlan-staging`, no solo contra
  una DB nueva vacía (`PRAGMA table_info` + `ALTER TABLE` condicional,
  exclusivo del adaptador SQLite; el repo real usa
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, ya documentado en
  `CLAUDE.md`).
- **Links de invitación de un solo uso** (`mictlan/invitaciones.py`,
  tabla `invitaciones` insert-only): `member_limit=1` — Telegram mismo
  invalida el link tras el primer ingreso, sin listener de
  auto-revocación/rotación como tiene ALFA-1 (decisión explícita de
  mantener solo el panel de generar/actualizar). Dos flujos separados:
  - `/mando > Grupos`: root, **solo** para el grupo principal (botón "🔗
    Generar nuevo link" en su detalle).
  - **Comando nuevo `/canales`** (nombre elegido por la sesión — corto,
    distinto de `/invitar`/`/scrapper` de ALFA-1, ver regla de nombres):
    cualquier miembro con membresía activa, usado **dentro** del grupo
    principal, se autogenera un link a un grupo/canal **secundario**
    (nunca al principal). Silencio total si se usa fuera del grupo
    principal.
- **Expulsión automática por membresía vencida** (`mictlan/vencimientos.py`):
  job cada 1 hora (mismo ritmo que `auto_expel_expired_users` de ALFA-1)
  que expulsa con `moderacion.expulsar_de_todos_los_grupos(tipo=
  'membresia_vencida')` de **todos** los grupos/canales gestionados —
  confirmado explícitamente por Fernando ("retirar al miembro de todo el
  ecosistema"), no solo el principal. Reutiliza el mecanismo de
  expulsión ya construido para el baneo, solo con `tipo` distinto — sin
  motivo, sin entrada en `blacklist`, nunca bloquea reingreso (si el
  usuario paga de nuevo puede volver a entrar como cualquier otro).
- **Probado funcionalmente**: 25 aserciones contra SQLite real —
  incluida la migración sobre datos preexistentes, exclusividad del
  grupo principal, generación de links end-to-end (mock de
  `create_chat_invite_link`), `/canales` con los 3 gates (fuera del
  grupo principal, sin membresía activa, nunca el principal), y el
  chequeo periódico de vencimientos expulsando de verdad de los 3 grupos
  gestionados + idempotencia (no vuelve a expulsar a quien ya se
  desactivó). Desplegado de verdad, journal limpio, migración confirmada
  sobre la base persistente real de staging.
- **Portado el mismo día al working tree del repo real** — ver "Esqueleto
  portado al working tree del repo real" al principio de este archivo.

### Mictlantecuhtli: segundo bot de respaldo/failover (2026-09-02, sesión de continuación)

Fernando pidió revisar a fondo cómo ALFA-1 planteaba "SOMBRA" antes de
construir (ya se había hecho el 2026-09-01 para "Modo de mantenimiento",
esta vez con foco en el bot de respaldo completo). Investigación real
del código, no solo del `.md`: **ALFA-1 nunca construyó el bot de
respaldo independiente** — solo la mitad de monitoreo pasivo
(`heartbeat.py`/`sombra_link.py`, reales; `sombra_simulator.py` solo
simula, no ejecuta nada). El cierre de perímetro real, `/comando`, y el
"contra-interrogatorio" quedaron solo en el documento (marcados con ❌ en
su propia sección 9). Fernando pidió cubrir **todo** lo que el documento
planteaba, no solo la mitad construida — con nombre propio,
**Mictlantecuhtli**, nunca "SOMBRA".

Antes de escribir código: plan formal (modo plan), dado el tamaño (un
segundo proceso con permisos administrativos reales sobre los grupos) y
el potencial destructivo (restringir chats enteros). Plan aprobado por
Fernando antes de empezar.

- **Arquitectura**: proceso separado (`mictlantecuhtli.py`), token
  propio, misma DB compartida (nunca una API HTTP nueva — la opción más
  simple, ya usada implícitamente en todo el resto de Mictlan).
- **Máquina de estados**: 5 fases (`normal`/`alerta`/`critico`/
  `respaldo_activo`/`recuperacion_pendiente`), consolidando las 7 fases
  inconsistentes del documento original de ALFA-1 (el propio documento
  contradice su texto narrativo con su pseudocódigo en los tiempos de
  cada fase). `respaldo_activo` restringe (`set_chat_permissions`) todos
  los grupos gestionados — reversible, nunca banea/expulsa. Enganchada
  con `mantenimiento.esta_en_mantenimiento()`: nunca escala si Mictlan
  está en mantenimiento deliberado — el enganche que esa feature había
  dejado pendiente el 2026-09-01.
- **"Contra-interrogatorio" resuelto** (ALFA-1 lo dejó con un comentario
  literal `# se implementará aquí` sin terminar): `respaldo_activo` es
  una fase "pegajosa" — solo `/reactivar <secreto>` dentro de una
  ventana de 30s puede sacarla de ahí, ni siquiera que el heartbeat del
  bot principal vuelva solo alcanza. Un solo mecanismo de confirmación
  humana para los dos casos (recuperación manual y "confirmar que el
  principal volvió de verdad"), en vez de dos secretos separados.
- **Probado funcionalmente**: 27 aserciones en staging + 12 de lógica en
  el repo real (39 total) — umbrales exactos, pegajosidad de
  `respaldo_activo`, inhibición por mantenimiento, ventana de
  recuperación (secreto correcto/incorrecto/vencida), autorización
  root-only, `/tecuhtli_simular`. Encontrado y corregido en el camino un
  bug real de manejo de timestamps (ver entrada del porteo, arriba).
- **Desplegado de verdad con un token real**: Fernando compartió un
  token de Telegram nuevo (`@respaldomictlanstagg_bot`) — agregado al
  `.env` de staging junto con un `TECUHTLI_SECRETO_RECUPERACION`
  generado para pruebas. Confirmado con `getMe()` que conecta de
  verdad, y el proceso corre en vivo leyendo los heartbeats reales del
  bot principal. Corre como proceso manual (`nohup`), no como servicio
  systemd — la sesión no tiene sudo para crear unidades nuevas (ver
  "Permisos de sudo en el VPS (política)" en `CLAUDE.md`).
- **`DESPLIEGUE_MICTLANTECUHTLI.md`** (nuevo, raíz de este repo):
  instrucciones y comandos exactos para que Fernando convierta esto en
  un servicio systemd real (unidad, `.env`, verificación funcional, y
  las líneas de `visudo` opcionales para que una sesión futura lo
  administre sin pedir contraseña).
- **`mictlan-staging/` pasó a ser su propio repo git**, pusheado a
  `github.com/FranEstAlv/Stagging` (pedido explícito de Fernando, antes
  de armar el servicio) — commit inicial con el código real de staging
  (incluido todo lo de Mictlantecuhtli), excluyendo `.env`, `venv/`,
  `*.db`, `*.log`, `external_modules/`, `datos_compartidos/`, y los
  clones git anidados (`Mictlan/`, `OLIMPO/`, `Docs/`, cada uno con su
  propio remoto). Revisado a mano el diff completo buscando secretos
  antes de commitear — ninguno encontrado (solo nombres de variables de
  entorno, nunca valores).

### Otros módulos base nuevos en `mictlan/` (staging)

- `proxy.py` (21 líneas) — `contexto.proxy` para DataImpulse. **Ya
  probado con credenciales reales**, no solo diseñado (el plan de
  `CLAUDE.md` lo pintaba como pendiente).
- `captcha.py` (144 líneas) — groundwork para resolución de captchas
  (2Captcha/CapSolver/Anti-Captcha). Investigación completa de los 3
  proveedores documentada en `GUIA_SDK_MODULOS_EXTERNOS.md` (raíz de
  `mictlan-staging/`), con propuesta de `CaptchaFacade`
  (`contexto.captcha`) **todavía sin construir** — ver "Decisiones
  abiertas" abajo, hay una pregunta sin responder de Fernando.
- `smsvirtual.py` (73 líneas) — integración con HeroSMS/SMSPool para
  números virtuales, groundwork.
- `canal.py` (105 líneas) — publicación a canal/grupo, con poda
  (`MAX_MENSAJES`, mismo patrón que ya usa OLIMPO en su propio
  `canal.py`, sin acumular sin límite).
- `formato.py` (74 líneas) y `datos.py` (76 líneas) — helpers de
  formateo de mensajes y acceso a `datos_compartidos/` (CSV/SQLite de
  productos, ~78 MB, usado por `panelpub`/`publicadorprod`/las
  `consultaN`).
- `modules/grupos.py` (68 líneas) — primera implementación real del plan
  de "Grupos dinámicos" de `CLAUDE.md`.
- Logging propio en `main.py` de staging: `StreamHandler` a stdout
  (capturado por `journalctl -u mictlan-staging.service`) en nivel
  `TRACE` (más verboso que DEBUG, incluye detalle de red de
  httpx/httpcore), con un filtro `_RedactorToken` que reemplaza el token
  del bot por `***TOKEN***` en cualquier línea antes de escribirla —
  **enfoque distinto** al `RotatingFileHandler` que pinta el plan de
  "Logging propio de Mictlan" en `CLAUDE.md` (a evaluar cuál se porta).

### Huecos reales detectados (de `GUIA_SDK_MODULOS_EXTERNOS.md`, revisando `smspool.py` de ALFA-1 completo)

Antes de poder construir un módulo de venta real (ej. SMSPool) con este
SDK, faltaban dos piezas — confirmado comparando contra el único módulo de
ALFA-1 que vende algo de punta a punta:
1. ~~**`contexto.db`** — persistencia propia por módulo~~ **Resuelto el
   2026-09-01 (sesión de continuación)** — ver "Persistencia propia de
   módulo (contexto.datos.db): construida y probada" más arriba. No se
   siguió al pie de la letra el camino "más barato" que se había
   identificado (sumar escritura a `abrir_sqlite_propio()`, síncrono) —
   Fernando pidió explícitamente considerar muchos usuarios concurrentes y
   tareas independientes por módulo, así que se optó por una conexión
   `aiosqlite` real (async, no bloquea el event loop) con un candado
   propio por módulo, en vez de abrir un archivo síncrono por llamada.
   `trivia` y `compartir` ya lo usan de punta a punta y sobreviven un
   restart. Ya se puede construir un módulo que reconcilie pedidos a medio
   resolver al arrancar, igual que `_reconcile_job` de `smspool.py`.
2. ~~**Ledger de créditos** — sigue sin existir~~ **Resuelto el
   2026-09-01** — ver "Ledger de créditos: construido y probado" más
   abajo. Ya se puede construir un módulo que cobre créditos de verdad,
   no solo simular (como hacía `trivia` con puntaje en memoria).

### Decisión abierta, pendiente de Fernando

`GUIA_SDK_MODULOS_EXTERNOS.md` propone `contexto.captcha` (interfaz única
sobre 2Captcha/CapSolver/Anti-Captcha) pero deja dos preguntas sin
responder antes de construirlo:
1. ¿Con qué proveedor probar primero? (necesita una `clientKey` real de
   alguno de los tres, igual que se hizo con el proxy de DataImpulse).
2. ¿`contexto.captcha` soporta un solo proveedor activo a la vez (una
   variable de entorno global), o un módulo debería poder pedir un
   proveedor específico (ej. uno más barato para imagen-a-texto y otro
   para reCAPTCHA)?

### Limpieza pendiente (detectada, no ejecutada — no se pidió)

- `mictlan-staging/bot.log` (raíz, ~163 KB) es un artefacto de una sesión
  manual anterior a que existiera el servicio systemd actual (última
  línea del 2026-08-31 15:08, el servicio arrancó a las 18:32). Lleno de
  errores `Conflict: terminated by other getUpdates request` de cuando
  corrían dos instancias con el mismo token a la vez. No lo escribe el
  código actual (que loguea a stdout/journalctl) y no expone el token en
  crudo. No se borró porque no se pidió — queda anotado acá para que una
  sesión futura decida si limpiarlo.

## Lo que falta (roadmap, sin fecha confirmada)

Ninguno de estos ítems tiene fecha comprometida — son los próximos
candidatos, en el orden en que se fueron mencionando, no
necesariamente el orden en que se van a construir:

- ~~**SOMBRA-equivalente**~~ **Construido y probado en `mictlan-staging`
  el 2026-09-02, portado al working tree de este repo el mismo día, y
  desplegado en vivo en staging con un token real** — nombre propio,
  **Mictlantecuhtli** (nunca "SOMBRA"). Ver "Mictlantecuhtli
  (implementado)" en `CLAUDE.md`. Falta convertirlo en servicio systemd
  (`DESPLIEGUE_MICTLANTECUHTLI.md`, raíz del repo, tiene los comandos
  exactos) y decidir cuándo/si se despliega en el Mictlan real —
  necesita su propio token de producción.
- `/fuera` (expulsión rápida) y `/callar` (mute rápido). **Forma de
  invocación todavía sin decidir**: ¿comando corto respondiendo a un
  mensaje, al estilo de los comandos de staff de ALFA-1 (ej. `/restar
  responder o ID días`), o acción/botón dentro de `/mando`? No asumir
  ninguna de las dos hasta que Fernando lo confirme explícitamente —
  ambas opciones se le plantearon y todavía no eligió.
- `/menu`, `/precios` (comandos de miembro).
- ~~Sistema de créditos con ledger auditado~~ **Portado al working tree
  de este repo el 2026-09-01 (`mictlan/creditos.py`), sin commitear
  todavía** — ver "Esqueleto portado al working tree del repo real" al
  principio de este archivo. Pendiente: prueba contra PostgreSQL real
  (no se pudo correr esta sesión, ver esa misma sección) y decisión de
  Fernando sobre cuándo commitear.
- ~~**Acciones de membresía dentro de `/mando`**: sumar/restar días,
  banear, asignar rol~~ **Construido y probado en `mictlan-staging` el
  2026-09-01, portado al working tree de este repo el mismo día** —
  `mictlan/membresias.py`, `roles.establecer_rol`, panel de
  `modules/mando/usuarios.py` con paginado y detalle. "Banear" se
  construyó como su propio mecanismo (ver "Baneo y lista negra
  (implementado)" en `CLAUDE.md`), no como una acción menor de membresía.
- ~~**SDK de módulos externos**~~ **Construido, documentado
  (`CONTRATO_SDK_MODULOS.md`) y portado al working tree de este repo el
  2026-09-01, sin commitear** — `mictlan/sdk/` (paquete de 11 archivos),
  ver "Esqueleto portado al working tree del repo real" al principio de
  este archivo y "SDK de módulos externos (implementado)" en `CLAUDE.md`.
  `contexto.captcha`/`contexto.sms` siguen sin construir, bloqueados por
  la misma decisión abierta de Fernando (ver más abajo).
- ~~**Grupos dinámicos reales**~~ **Construido en `mictlan-staging` el
  2026-09-01 y portado al working tree de este repo el mismo día, sin
  commitear** — ver "Esqueleto portado al working tree del repo real" al
  principio de este archivo. La decisión de detección ya no está
  pendiente (Fernando confirmó `ChatMemberHandler` sobre
  `my_chat_member`, no la detección pasiva de ALFA-1).
- ~~**Proxies salientes vía DataImpulse**~~ **Construido, probado con
  credenciales reales en `mictlan-staging`, y portado al working tree de
  este repo el 2026-09-01** — `mictlan/proxy.py`, expuesto como
  `contexto.proxy` vía el SDK.
- **Migraciones de esquema** — diseño en "Migraciones de esquema (plan)"
  de `CLAUDE.md` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` sumado a
  `_SCHEMA`, probado siempre contra la DB descartable antes de tocar la
  de producción).
- ~~**Logging propio de Mictlan**~~ **Construido y probado el 2026-09-01,
  directo en el working tree de este repo** (no pasó por
  `mictlan-staging` — ver la entrada de "Reporte de salud" del mismo día
  para el motivo) — ver "Logging propio de Mictlan (implementado)" en
  `CLAUDE.md`.
- **Backups de PostgreSQL** — diseño en "Backups de PostgreSQL (plan)"
  de `CLAUDE.md` (`pg_dump` programado + retención + procedimiento de
  restauración documentado). Hoy no hay ningún respaldo de la base de
  Mictlan.
- **Bot de staging** — diseño en "Bot de staging (plan)" de `CLAUDE.md`
  (segundo bot/token de Telegram + base de staging propia, para no
  seguir probando cambios nuevos contra el bot y la base de producción).
- ~~**Modo de mantenimiento**~~ **Construido y probado en
  `mictlan-staging` el 2026-09-01, portado al working tree de este repo
  el mismo día** — ver "Modo de mantenimiento (implementado)" en
  `CLAUDE.md`. Sigue sin existir un heartbeat que lo consulte de verdad —
  eso queda como diseño futuro, esta pieza es solo el estado.
- Guardia anti-fuga de usuarios.
- Importación/exportación CSV.
- Paneles de salud/auditoría.
- Difusión por DM (broadcast).
- Sistema de referidos.
- Extracción de datos desde capturas de pantalla.
- Herramientas de fraude/geo por IP.
- Panel de simulacro de seguridad (no destructivo).
- Integrar `Out/ai_assistant.py` (extracción portable de Atenea, ya
  construida en el repo OLIMPO) como asistente dentro de Mictlan.

## Paridad de comandos (ALFA-1 → Mictlan)

| ALFA-1 | Mictlan | Estado |
|---|---|---|
| `/batman` (consola admin) | `/mando` | ✅ Construido |
| `/perfil` + `/saldo` + info personal | `/perfil` (unificado) | ✅ Construido |
| queja/reporte a administradores | `/reporte` | ✅ Construido |
| expulsar usuario | `/fuera` | ⏳ Pendiente (¿comando corto o botón en `/mando`? sin decidir) |
| mutear usuario | `/callar` | ⏳ Pendiente (¿comando corto o botón en `/mando`? sin decidir) |
| `/start` | `/start` | ✅ Construido (mensaje de bienvenida básico) |
| menú de miembro | `/menu` | ⏳ Pendiente |
| lista de precios | `/precios` | ⏳ Pendiente |
| SOMBRA (segundo bot) | sin nombre asignado aún | 📖 Diseño leído, no construido |

Regla de nombres (confirmada por Fernando): cortos, no genéricos, nunca
iguales a los de ALFA-1, nunca tan largos como `/moduleload`.

## Reporte de salud

Este es el mecanismo para que **cualquier sesión nueva** (incluida una
sin memoria de las anteriores) pueda confirmar rápido si el proyecto va
por buen camino, sin tener que releer todo el historial de git a mano.

### Cómo generar una entrada nueva

Al cerrar cada sesión de trabajo relevante sobre Mictlan, agregar una
entrada arriba de todo (más reciente primero) con este formato exacto:

```
### AAAA-MM-DD — <resumen corto de la sesión>
- Commits pusheados a main desde el reporte anterior: <hash corto — mensaje>, ...
- ¿Cada commit se probó contra PostgreSQL real antes de pushear? Sí/No
  (si No: explicar por qué y qué falta probar)
- ¿Se violó alguna regla fija de CLAUDE.md (cero superadmin, silencio
  total, convención install_xxx, DB solo vía db.get_pool(), variables de
  entorno leídas de forma perezosa)? Sí/No — detalle si Sí
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o empezó a mezclar
  más de una responsabilidad (riesgo de repetir el `core.py` de ALFA-1)?
  Sí/No — si Sí, ¿se dividió en sub-paquete o queda pendiente?
- ¿Este archivo (avances/roadmap/paridad) quedó actualizado con el
  trabajo de la sesión? Sí/No
- Semáforo: 🟢 en buen camino / 🟡 hay algo pendiente de resolver /
  🔴 hay una violación de regla fija sin resolver
- Próximo paso sugerido:
```

Semáforo 🔴 significa: no seguir sumando funcionalidad nueva hasta
resolver lo que lo causó — arreglarlo es la prioridad de la siguiente
sesión, antes que cualquier ítem del roadmap.

### Última entrada

### 2026-09-02 — Mictlantecuhtli portado, desplegado en vivo con token real, y `mictlan-staging` pasó a ser su propio repo git
- Commits: **ninguno en `Mictlan/`** — se suma al working tree ya
  pendiente de revisión. Archivos nuevos: `mictlan/heartbeat.py`,
  `mictlan/tecuhtli/` (`__init__.py`, `estado.py`, `acciones.py`,
  `evaluador.py`, `recuperacion.py`), `mictlantecuhtli.py`,
  `DESPLIEGUE_MICTLANTECUHTLI.md`. Modificados: `db.py` (tablas
  `heartbeats`/`tecuhtli_estado`), `main.py` (`install_heartbeat`),
  `.env.example`. **Sí hubo un commit real**, pero en un repo distinto:
  `mictlan-staging/` (la raíz del ambiente de pruebas, hasta ahora sin
  git) se inicializó y se pusheó a `github.com/FranEstAlv/Stagging`
  (repo vacío que Fernando ya tenía creado) — pedido explícito suyo,
  antes de armar el servicio systemd. Un solo commit, "Commit inicial",
  55 archivos.
- ¿Probado contra PostgreSQL real? No, misma limitación de siempre — 12
  aserciones de lógica con el sustituto de SQLite con tipos reales
  (`TIMESTAMPTZ`/`BOOLEAN`). **Esta vez sí hubo despliegue en vivo real**
  con un token de Telegram real (`@respaldomictlanstagg_bot`, provisto
  por Fernando), aunque en `mictlan-staging`, no en el repo real —
  confirmado con `getMe()` que conecta, y el proceso corre leyendo los
  heartbeats reales del bot principal sin errores.
- ¿Regla fija violada? No. Se armó un plan formal (modo plan) antes de
  escribir código, dado el tamaño y el potencial destructivo de la
  pieza — aprobado por Fernando explícitamente antes de empezar. Antes
  de commitear `mictlan-staging/` a su nuevo repo, se revisó a mano el
  diff completo buscando secretos (nombres de variables sí, valores
  reales no) y se confirmó que `.env` no quedó staged.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — cada archivo de `mictlan/tecuhtli/` tiene una
  sola responsabilidad clara (estado, acciones, evaluación, comandos),
  ninguno pasa las ~130 líneas.
- ¿Documento actualizado? Sí — `CLAUDE.md`: nueva sección
  "Mictlantecuhtli (implementado)", corregida la nota sobre qué partes
  de SOMBRA están realmente implementadas en ALFA-1 (antes decía "SÍ
  está implementada" en general; la investigación más profunda de esta
  sesión encontró que solo la mitad de monitoreo pasivo lo está). Este
  archivo: nueva subsección en "Avances en el ambiente de staging",
  resumen del porteo en "Esqueleto portado...", roadmap actualizado
  (ítem tachado).
- Semáforo: 🟢
- Próximo paso sugerido: convertir Mictlantecuhtli en servicio systemd
  de verdad en `mictlan-staging` (`DESPLIEGUE_MICTLANTECUHTLI.md` tiene
  los comandos exactos) — pendiente porque esta sesión no tiene sudo
  para crear unidades nuevas. Para el Mictlan real: decidir cuándo
  desplegarlo, necesita su propio token de producción y que ese bot se
  agregue como admin (con permiso de restringir) en los grupos reales.

### 2026-09-01 — Logging propio de Mictlan (construido directo en el repo real, sin pasar por staging)
- Commits: **ninguno todavía** — se suma al working tree ya pendiente de
  revisión. Archivo nuevo: `mictlan/logging_setup.py`. Modificados:
  `main.py` (llama `configurar_logging()` justo después de
  `load_dotenv()`), `.env.example` (+ `MICTLAN_LOG_PATH`/
  `MICTLAN_LOG_LEVEL`, ambas opcionales).
- **Desviación deliberada del patrón "construir en staging primero"**:
  esta feature se construyó directo en `Mictlan/`, no en
  `mictlan-staging`. Motivo: `mictlan-staging` ya tiene su propia
  configuración de logging (TRACE + redacción de token, inline en su
  `main.py`, marcada explícitamente como "exclusiva de esta copia de
  staging") que resuelve una necesidad distinta (debug detallado en un
  ambiente descartable); el hueco que describía `CLAUDE.md` ("Logging
  propio de Mictlan") era específicamente del Mictlan real. No tiene
  dependencia de Telegram/DB en vivo para validarse, así que no hacía
  falta el bot de staging como intermediario.
- **Aclaración de Fernando (2026-09-01) sobre la metodología, aplicada
  desde esta entrada en adelante**: la prueba contra Postgres real de
  todo lo portado se corre una sola vez al final, integral, contra el
  Mictlan real — no en cada porteo individual. Esta entrada y las
  siguientes ya no marcan semáforo 🟡 por "falta Postgres real" (ver
  detalle en "Metodología de pruebas" de `CLAUDE.md`).
- ¿Probado contra PostgreSQL real? No — no hacía falta ninguna DB para
  esta feature en absoluto (es logging puro de la librería estándar). Sí
  se probó funcionalmente de verdad: 8 aserciones — el archivo rotativo
  se crea y recibe líneas reales, `configurar_logging()` llamado 2 veces
  no duplica handlers (ni duplica líneas en el archivo), el token del
  bot nunca aparece crudo en el log (queda `***TOKEN***`) probado con un
  logger `httpx` simulando el mensaje real que loguea esa librería,
  `MICTLAN_LOG_LEVEL` se respeta, y el `RotatingFileHandler` queda con
  `maxBytes`/`backupCount` configurados. `python -m py_compile` sobre
  todo el repo, limpio.
- ¿Regla fija violada? No. Variables de entorno leídas de forma
  perezosa (dentro de la función, no a nivel de módulo), mismo criterio
  que `ROOT_ID`/`ADMIN_GROUP_ID`. Patrón de guarda anti-duplicado
  adaptado de `OLIMPO/logging_setup.py` (proyecto hermano de Fernando,
  no ALFA-1 — la regla prohibitiva de espejo no aplica a ese archivo).
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `logging_setup.py` es nuevo y chico (~65
  líneas), una sola responsabilidad.
- ¿Documento actualizado? Sí — `CLAUDE.md`: "Logging propio de Mictlan"
  pasó de "(plan)" a "(implementado)", y se agregó la aclaración de
  Fernando sobre el ritmo de la prueba de Postgres en "Metodología de
  pruebas". Este archivo: roadmap actualizado.
- Semáforo: 🟢
- Próximo paso sugerido: con esto, de los 4 huecos de infraestructura
  que quedaban ("Migraciones de esquema", "Logging propio", "Backups de
  PostgreSQL", "Bot de staging"), solo faltan Backups (necesita que
  Fernando defina la retención) y la validación completa de
  Migraciones/Bot de staging contra Postgres real (que ya no bloquea,
  queda para el final). Candidatos sin decisiones abiertas: SOMBRA-
  equivalente, o preguntarle a Fernando por `/fuera`/`/callar` y
  `/menu`/`/precios`.

### 2026-09-01 — Porteo de grupo principal, links de invitación y expulsión por vencimiento al repo real
- Commits: **ninguno todavía** — se suma al working tree ya pendiente de
  revisión (`git status` sigue sin `add`/`commit`). Archivos nuevos:
  `mictlan/invitaciones.py`, `mictlan/vencimientos.py`,
  `mictlan/modules/canales.py`. Modificados: `db.py` (tabla
  `invitaciones` + `ALTER TABLE grupos ADD COLUMN IF NOT EXISTS
  principal`), `membresias.py` (`vencidas()`/`desactivar()`),
  `modules/grupos.py` (`establecer_principal()`/`obtener_principal()`),
  `modules/mando/grupos.py` (botón marcar principal + generar link),
  `modules/mando/__init__.py`, `main.py`.
- ¿Probado contra PostgreSQL real? **No, otra vez** — misma limitación de
  entorno de las dos entradas anteriores (sin sudo a `postgres`, sin rol
  propio, sin `.env` con DSN real). Mismo sustituto que la vez pasada:
  SQLite con `adapters`/`converters` para que `TIMESTAMPTZ`/`BOOLEAN`
  redondeen como `datetime`/`bool` reales. 14 aserciones de lógica
  pasaron. **Límite adicional específico de esta entrada**: la migración
  real (`ALTER TABLE grupos ADD COLUMN IF NOT EXISTS principal ...`) es
  sintaxis pura de Postgres — el arnés de SQLite no la ejecuta ni puede
  (SQLite no soporta esa sintaxis, confirmado). Se revisó a mano contra
  la documentación de Postgres (válida desde 9.6) y se probó el
  equivalente funcional de verdad en `mictlan-staging` contra su base
  persistente real (no una DB nueva vacía) — ver la entrada de staging
  de esta misma sesión.
- ¿Regla fija violada? La metodología de pruebas (arriba), por la misma
  razón de entorno — ninguna otra. Se respetó la instrucción explícita
  de Fernando de dejar fuera la aprobación de ingreso con auto-expulsión
  (existe en ALFA-1, no se pidió) — no se asumió que había que portarla
  también solo porque el espejo la tiene.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `invitaciones.py` (~40 líneas),
  `vencimientos.py` (~30 líneas) y `modules/canales.py` (~120 líneas),
  cada uno una sola responsabilidad clara.
- ¿Documento actualizado? Sí — `CLAUDE.md`: nuevas secciones "Grupo
  principal y links de invitación de un solo uso (implementado)" y
  "Expulsión automática por membresía vencida (implementado)". Este
  archivo: "Qué se portó" ampliado con un resumen de los porteos
  posteriores al inicial, nueva subsección en "Avances en el ambiente de
  staging".
- Semáforo: 🟡 — misma razón que las dos entradas anteriores: nada roto
  ni ninguna regla de código violada, pero la prueba real contra
  Postgres sigue pendiente para todo lo portado hasta ahora (créditos,
  SDK, grupos, membresía/baneo, mantenimiento, y ahora esto).
  Confirmado además que la parte de la migración vía `ALTER TABLE
  IF NOT EXISTS` no se puede ejercitar con el sustituto de SQLite —
  necesita Postgres real para validarse de punta a punta.
- Próximo paso sugerido: sigue siendo correr la prueba real contra
  Postgres de TODO lo portado (no solo esta entrada) antes de cualquier
  commit — necesita sudo completo o un DSN de Fernando. Con eso resuelto:
  revisar el `git diff` completo y decidir si se commitea todo junto o
  separado por tema (van quedando varios temas independientes: esqueleto
  base, SDK, grupos, créditos, membresía/baneo, mantenimiento,
  invitaciones/vencimientos).

### 2026-09-01 — Grupo principal, links de invitación de un solo uso y expulsión automática por membresía vencida, construidos y probados en `mictlan-staging`
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad: 25 aserciones — incluida la
  migración de la columna `principal` sobre una DB con datos
  preexistentes (no una DB nueva vacía), exclusividad del grupo
  principal (nunca 2 a la vez), generación de link end-to-end desde
  `/mando` y desde `/canales`, los 3 gates de `/canales` (silencio fuera
  del grupo principal, aviso sin membresía activa, nunca genera el link
  del principal), y el chequeo periódico de vencimientos expulsando de
  verdad de los 3 grupos gestionados con auditoría correcta
  (`tipo='membresia_vencida'`, no `'baneo'`) + idempotencia. Desplegado
  de verdad (`sudo systemctl restart mictlan-staging.service`), journal
  limpio, migración confirmada por lectura directa de la base
  persistente real (`PRAGMA table_info`), los 11 módulos reales activos
  siguieron activos.
- ¿Regla fija violada? No. Antes de construir, Fernando pidió revisar el
  espejo de ALFA-1 explícitamente — se investigó a fondo (código real,
  archivo:línea) los tres mecanismos (auto-expulsión por tiempo,
  aprobación de ingreso + auto-expulsión, links de un solo uso) antes de
  proponer nada. El diseño final tomó solo lo que Fernando confirmó
  explícitamente (auto-expulsión por tiempo + links), dejando fuera la
  aprobación de ingreso con ventana de 1 minuto de ALFA-1 — no se asumió
  que había que portar los tres solo porque el espejo los tiene los tres.
  `/canales` es un nombre nuevo, distinto de `/invitar`/`/scrapper` de
  ALFA-1 (regla de nombres respetada).
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `invitaciones.py`, `vencimientos.py` y
  `modules/canales.py` son nuevos y chicos, cada uno una sola
  responsabilidad.
- ¿Documento actualizado? Sí — nueva sección en "Avances en el ambiente
  de staging".
- Semáforo: 🟢
- Próximo paso sugerido: portado el mismo día al repo real (ver entrada
  siguiente).

### 2026-09-01 — Porteo de acciones de membresía, baneo/lista negra y modo de mantenimiento al repo real
- Commits: **ninguno todavía** — se suma al working tree ya pendiente de
  revisión de la entrada anterior (`git status` sigue sin `add`/`commit`).
  Archivos nuevos: `mictlan/membresias.py`, `mictlan/moderacion.py`,
  `mictlan/mantenimiento.py`, `mictlan/modules/mando/baneo.py`,
  `mictlan/modules/mando/mantenimiento.py`. Modificados: `db.py` (3
  tablas nuevas), `roles.py` (`establecer_rol`), `modules/mando/usuarios.py`
  (reescrito con paginado/detalle), `modules/mando/__init__.py`, `main.py`.
- ¿Probado contra PostgreSQL real? **No, otra vez** — misma limitación de
  entorno que la entrada anterior (sin sudo a `postgres`, sin rol propio,
  sin `.env` con DSN real, confirmado de nuevo esta sesión). En vez del
  shim de SQLite simple de la entrada anterior, esta vez se armó uno más
  fiel: SQLite con `adapters`/`converters` de `sqlite3` registrados para
  que las columnas `TIMESTAMPTZ`/`BOOLEAN` redondeen como `datetime`/`bool`
  **reales** (no texto/enteros), igual que haría `asyncpg` — para
  ejercitar la aritmética de fechas de `membresias.py`/`mantenimiento.py`
  con el mismo comportamiento de tipos que tendría Postgres. 24
  aserciones de lógica pasaron. **Esto sigue sin ser la prueba real
  contra Postgres** que exige la metodología — queda pendiente igual que
  el resto de lo portado hoy.
- ¿Regla fija violada? La metodología de pruebas (arriba), por la misma
  razón de entorno. Ninguna otra — no se copió código de ALFA-1 (se leyó
  `global_moderation.py`/`deslistar_command.py`/`maintenance.py` como
  espejo, se reescribió de cero), y se corrigieron las diferencias reales
  de portar con cuidado (ver abajo).
- **Correcciones que salieron de portar con cuidado, no copiar y pegar**:
  `membresias.py` y `mantenimiento.py` en `mictlan-staging` parsean/formatean
  fechas a mano (`fin`/`hasta` son `TEXT` ahí, adaptador SQLite propio) —
  en el repo real esas columnas son `TIMESTAMPTZ`, así que la versión
  portada **elimina por completo** ese parseo: `asyncpg` entrega
  `datetime` conscientes de zona horaria directo, la aritmética es
  `datetime + timedelta` sin más. En `modules/mando/usuarios.py` y
  `modules/mando/baneo.py` (`_ver_reporte`), los recortes de string sobre
  fechas (`valor[:10]`) se reemplazaron por `.strftime(...)` sobre el
  `datetime` real, mismo patrón que ya usaba el resto de los módulos
  portados (`modules/grupos.py`). La consulta de "baneado" en la lista de
  usuarios pasó de un `CASE WHEN ... THEN 1 ELSE 0 END` (necesario en
  SQLite) a una expresión booleana nativa de Postgres
  (`b.user_id IS NOT NULL`).
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — mismos tamaños que en `mictlan-staging`
  (`usuarios.py` 213, `baneo.py` 202, `moderacion.py` 173 líneas), todos
  con margen respecto al umbral.
- ¿Documento actualizado? Sí — `CLAUDE.md`: "Modo de mantenimiento" pasó
  de "(plan)" a "(implementado)", se agregaron "Acciones de membresía en
  /mando (implementado)" y "Baneo y lista negra (implementado)". Este
  archivo: nuevas subsecciones en "Avances en el ambiente de staging",
  roadmap actualizado (ambos ítems tachados como construidos+portados).
- Semáforo: 🟡 — misma razón que la entrada anterior: nada roto ni
  ninguna regla de código violada, pero la metodología de pruebas
  obligatoria sigue incumplida por la misma limitación real de entorno,
  ahora sobre el doble de superficie portada.
- Próximo paso sugerido: sigue siendo correr la prueba real contra
  Postgres (de todo lo portado hasta ahora, no solo esta entrada) antes
  de cualquier commit — necesita sudo completo o un DSN de Fernando. Con
  eso resuelto: revisar el `git diff` completo (ya son ~9 archivos
  modificados + ~17 nuevos) y decidir si se commitea todo junto o
  separado por tema.

### 2026-09-01 — Modo de mantenimiento construido y probado en `mictlan-staging`
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad: 24 aserciones contra SQLite real
  — activar por tiempo fijo (30 min/2 h) e indefinido, nunca dos ventanas
  activas a la vez, expiración automática de una ventana vencida,
  finalizar manual, y el panel completo de `/mando` (incluida la
  aparición/desaparición del botón "Finalizar" según el estado).
  Desplegado de verdad (`sudo systemctl restart mictlan-staging.service`),
  journal limpio, los 11 módulos reales activos siguieron activos.
- ¿Regla fija violada? No. Espejo explícito de
  `alfa1/samaritan/ops/maintenance.py` (leído completo) — mismo alcance
  deliberadamente acotado que el original (no detiene el bot, no cierra
  grupos, no expulsa a nadie), reescrito de cero. Solo botones de
  duración fija, sin `ConversationHandler` ni texto libre.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `mantenimiento.py` (~90 líneas) y
  `modules/mando/mantenimiento.py` (~70 líneas), cada uno una sola
  responsabilidad.
- ¿Documento actualizado? Sí — nueva sección "Modo de mantenimiento" en
  "Avances en el ambiente de staging" y el ítem correspondiente del
  roadmap marcado como construido.
- Semáforo: 🟢
- Próximo paso sugerido: portar esto al repo real (sin decisiones
  abiertas) — hecho en la entrada siguiente de esta misma sesión.

### 2026-09-01 — Acciones de membresía en `/mando`: días, rol, baneo/lista negra construidos y probados en `mictlan-staging`
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad: 36 aserciones — SQLite temporal +
  una `Application` real de `python-telegram-bot` (sin red), incluido el
  `ConversationHandler` de baneo completo de punta a punta (callback →
  motivo → foto → blacklist + expulsión real de 3 grupos mockeados),
  cancelación a mitad de flujo, la guardia de reingreso
  (`ChatMemberHandler.CHAT_MEMBER`, con casos positivo/negativo/salida),
  desbaneo, y "ver reporte" enviando la foto real guardada. Desplegado de
  verdad (`sudo systemctl restart mictlan-staging.service`), journal
  limpio, los 11 módulos reales activos siguieron activos.
- ¿Regla fija violada? No. Fernando aclaró explícitamente antes de
  construir que "banear" es expulsión de todos los grupos + reporte
  (motivo + foto) para no reaceptar, **distinto** de una futura expulsión
  automática por membresía vencida — se construyó exactamente esa
  semántica, sin asumir nada. Comparado a fondo con el mecanismo real de
  ALFA-1 (`global_moderation.py`, `deslistar_command.py`, `core.py`
  `list_command`/`list_reason_handler`/`list_image_handler`, todo leído
  completo) y reescrito de cero, nunca copiado — regla prohibitiva de
  espejo respetada.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No, pero `modules/mando/usuarios.py` (213 líneas) y
  el nuevo `modules/mando/baneo.py` (202 líneas) nacieron ya divididos en
  dos archivos en vez de uno solo creciendo — mismo criterio que
  `mando/modulos.py`/`mando/grupos.py`.
- ¿Documento actualizado? Sí — nueva sección en "Avances en el ambiente
  de staging" y el ítem correspondiente del roadmap marcado como
  construido.
- Semáforo: 🟢
- Próximo paso sugerido: portar esto al repo real (hecho en la entrada
  siguiente de esta misma sesión, junto con Modo de mantenimiento).

### 2026-09-01 — Esqueleto portado al repo real + `CONTRATO_SDK_MODULOS.md`
- Commits: **ninguno todavía** — todo el trabajo de esta entrada está en
  el working tree de este repo (`git status` limpio, sin `add`/`commit`),
  a propósito, para que Fernando revise el diff completo antes de decidir
  si se commitea. Ver "Esqueleto portado al working tree del repo real"
  al principio de este archivo para el detalle completo.
- ¿Probado contra PostgreSQL real? **No** — esta sesión no tuvo
  credenciales/sudo para administrar Postgres en este entorno (confirmado
  intentando `sudo -u postgres psql` y leer `pg_hba.conf`, ambos
  rechazados). Se corrieron 20 aserciones de lógica Python con un shim
  SQLite temporal (mismo mecanismo que `mictlan-staging`) en vez de la
  metodología obligatoria de este archivo — **esto NO cumple esa
  metodología**, queda anotado como incumplimiento explícito, no
  disimulado. Se verificó a mano la sintaxis Postgres del esquema nuevo
  y que `asyncpg.ForeignKeyViolationError` existe de verdad (import
  directo). Pendiente antes de commitear: correr la prueba real con
  Postgres desde una sesión con sudo completo, o que Fernando comparta
  un DSN de prueba.
- ¿Regla fija violada? La metodología de pruebas (arriba) — ver detalle.
  Ninguna otra: no se copió ningún módulo de prueba de staging (regla
  explícita de Fernando para esta tarea), `contexto.captcha`/`contexto.sms`
  quedaron fuera por ser una decisión suya sin tomar (no se asumió), y se
  corrigieron 3 cosas que hubieran quedado mal portadas literal (excepción
  `sqlite3.IntegrityError` → `asyncpg.ForeignKeyViolationError`,
  comentario del `Lock` del ledger desactualizado, `_traducir` que ya no
  vivía en `db.py`).
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — el `sdk/` portado ya viene dividido en 11
  archivos (ninguno arriba de 230 líneas), mismo criterio que se aplicó
  en `mictlan-staging`.
- ¿Documento actualizado? Sí — `CONTRATO_SDK_MODULOS.md` nuevo (contrato
  normativo completo del SDK), y en `CLAUDE.md`: las secciones "SDK de
  módulos externos", "Grupos dinámicos" y "Proxies salientes vía
  DataImpulse" pasaron de "(plan)" a "(implementado)"; se corrigió una
  nota incorrecta sobre SOMBRA (decía "nunca implementada en ALFA-1" —
  falso, verificado con el código real: `sombra_link.py`,
  `sombra_simulator.py`, `heartbeat.py`, `maintenance.py`, ~1,400 líneas
  instaladas de verdad en `alfa1_init.py`); "Arquitectura y convenciones"
  y "Modularidad" actualizadas con la estructura real de archivos
  (`modules/mando/` ya no es un solo `mando.py`).
- Semáforo: 🟡 — no es 🔴 porque no hay ninguna regla fija violada sobre
  el *código* (nada de superadmin, nada de scopes peligrosos, nada
  asumido sin decisión), pero la metodología de pruebas obligatoria
  quedó incumplida por una limitación real del entorno, no por
  descuido — hay que resolverla antes de commitear esto.
- Próximo paso sugerido: (1) correr la prueba contra Postgres real antes
  de cualquier commit; (2) que Fernando revise el `git diff` completo;
  (3) decidir si se commitea todo junto o se separa en varios commits
  temáticos (esqueleto base / SDK / grupos / créditos); (4) con eso
  resuelto, los candidatos sin decisiones abiertas siguen siendo
  "Acciones de membresía en /mando" y "Modo de mantenimiento".

### 2026-09-01 — Sección "🏘 Grupos" de `/mando` construida y probada
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git — ver la sección de arriba).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad: 15 aserciones contra SQLite real +
  una `Application` real de `python-telegram-bot` — incluye disparar el
  `ChatMemberHandler` (`my_chat_member`) real para auto-registrar un
  grupo (no un atajo de prueba), activar/desactivar desde la UI nueva
  confirmando la fila persistida después (no solo el texto de respuesta),
  paginación con 9 grupos, y un `chat_id` inexistente cayendo a la lista
  con aviso claro en vez de traceback. Desplegado de verdad
  (`sudo systemctl restart mictlan-staging.service`), journal limpio, los
  11 módulos reales activos siguieron activos.
- ¿Regla fija violada? No. Se reusó el gate de rol `root` + chat
  permitido ya existente en el router de `/mando` (sin duplicar el
  chequeo dentro de `grupos.py`, mismo criterio que `modulos.py`), y se
  reusó `mictlan/paginacion.py` (recién construido) en vez de inventar
  otra forma de paginar.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `mictlan/modules/mando/grupos.py` es nuevo y
  chico (~115 líneas, mismo patrón que `usuarios.py`/`modulos.py` del
  mismo sub-paquete).
- ¿Documento actualizado? Sí — nueva sección "Sección '🏘 Grupos' de
  `/mando`: UI de gestión construida y probada" en "Avances en el
  ambiente de staging", y el ítem "Grupos dinámicos reales" del roadmap
  grande ("Lo que falta") marcado como construido y probado en staging
  (queda pendiente portarlo al repo real).
- Semáforo: 🟢
- Próximo paso sugerido: preguntarle a Fernando qué sigue del roadmap
  grande — quedan listos para construir sin decisiones abiertas
  "Acciones de membresía en /mando" (sumar/restar días, banear, asignar
  rol) y "Modo de mantenimiento"; bloqueados esperando una decisión suya
  `/fuera`+`/callar` (forma de invocación) y `contexto.captcha` del SDK
  (proveedor a probar primero, uno activo vs. varios).

### 2026-09-01 — Paginación 2×3 en paneles con listas de botones
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git — ver la sección de arriba).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad: 33 aserciones — el helper
  `paginacion.py` aislado (conteo de páginas, recorte de grilla,
  controles ⬅️/➡️ en los bordes) y el panel de Módulos con 13 filas reales
  insertadas en `sdk_modulos` y una `Application` real de
  `python-telegram-bot`: navegación entre páginas, "Volver" preservando
  la página de origen, y los controles desapareciendo solos al quedar en
  una sola página tras eliminar módulos. Desplegado de verdad
  (`sudo systemctl restart mictlan-staging.service`), journal limpio, los
  11 módulos reales activos siguieron activos.
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `paginacion.py` es nuevo y chico (~55 líneas,
  una sola responsabilidad: paginar listas de botones). Se aprovechó para
  simplificar el router de `/mando` (`mando/__init__.py`): ya no conoce el
  formato interno de cada sub-sección (antes desempaquetaba
  `accion`/`module_id` a mano), ahora solo le pasa la cola completa del
  `callback_data` a `modulos.py`, que la parsea por su cuenta.
- ¿Documento actualizado? Sí — nueva sección "Paginación 2×3 en paneles
  con listas de botones" en "Avances en el ambiente de staging", y el
  catálogo unificado de comandos actualizado (`/mando` → 🧩 Módulos y
  `panelpub`).
- Semáforo: 🟢
- Próximo paso sugerido: si en algún momento se construye la sección "🏘
  Grupos" de `/mando` (todavía sin UI, ver "Grupos dinámicos (plan)" en
  `CLAUDE.md`) o cualquier otro panel con una lista que pueda crecer, usar
  `mictlan/paginacion.py` desde el principio en vez de un botón por fila
  sin límite.

### 2026-09-01 — Persistencia propia de módulo (`contexto.datos.db`) construida y probada
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git — ver la sección de arriba).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad: 22 aserciones contra SQLite real +
  una `Application` real de `python-telegram-bot` — incluye 50 escrituras
  concurrentes de "usuarios" distintos con el candado propio del módulo
  (0 perdidas, con un control negativo sin candado que sí pierde datos
  para confirmar que el candado hace falta) y la prueba central: `trivia`
  y `compartir` reales sobreviven un "restart" simulado completo
  (conexiones cerradas + caché del SDK vaciada + módulos reimportados),
  con el puntaje/estado de 2 usuarios independientes intacto después.
  Desplegado de verdad (`sudo systemctl restart mictlan-staging.service`),
  journal limpio, los 11 módulos reales activos siguieron activos.
- ¿Regla fija violada? No. Se detectó y corrigió una inconsistencia contra
  el propio SDK: la guía (`GUIA_SDK_MODULOS_EXTERNOS.md`) proponía el
  scope `db.propio`, que hoy queda bloqueado por
  `SCOPES_PREFIJOS_PELIGROSOS` (`db.` está prohibido a propósito) — se
  usó `datos.escribir_propio` en su lugar, mismo namespace que los otros
  scopes de `datos`, y quedó documentado el motivo del cambio de nombre.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `almacen_modulos.py` es nuevo y chico (~140
  líneas, una sola responsabilidad: persistencia propia por módulo).
- ¿Documento actualizado? Sí — nueva sección "Persistencia propia de
  módulo (contexto.datos.db): construida y probada" en "Avances en el
  ambiente de staging", el hueco #1 de "Huecos reales detectados" marcado
  como resuelto, y el catálogo unificado de comandos actualizado
  (`trivia`/`compartir` ya no dependen de memoria de proceso para el dato
  del usuario).
- Semáforo: 🟢
- Próximo paso sugerido: de los 3 huecos originales del SDK solo queda
  `contexto.captcha`, bloqueado por la decisión abierta de Fernando (con
  qué proveedor probar primero, y si soporta uno solo activo o varios a
  la vez). Con `contexto.db` resuelto, ya se puede construir un módulo de
  venta real de punta a punta (ej. el candidato SMSPool de
  `GUIA_SDK_MODULOS_EXTERNOS.md`), incluida la reconciliación de pedidos a
  medio resolver al arrancar.

### 2026-09-01 — Comparación con el SDK de ALFA-1 + ledger de créditos construido y probado
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git — ver la sección de arriba).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad: 20 aserciones contra un SQLite
  temporal + una `Application` real de `python-telegram-bot` — incluye
  una prueba de concurrencia real (5 cobros simultáneos contra un saldo
  que solo alcanza para 4, exactamente 4 pasan) que confirma que el
  `asyncio.Lock` del ledger evita double-spend. Después desplegado de
  verdad (`sudo systemctl restart mictlan-staging.service`), journal
  limpio, los 11 módulos reales activos siguieron activos.
- ¿Regla fija violada? No. Se aplicó explícitamente la regla prohibitiva
  de "ALFA-1 es espejo, nunca código fuente" — la comparación completa de
  esta sesión (código + ~18 docs, leídos completos) se usó solo para
  contrastar decisiones y detectar huecos, nunca para copiar código;
  el ledger de créditos se escribió de cero con convenciones propias.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — `creditos.py` es nuevo y chico (~150 líneas,
  una sola responsabilidad clara).
- ¿Documento actualizado? Sí — se agregaron dos secciones nuevas:
  "Comparación completa con el SDK real de ALFA-1" (hallazgo principal:
  nuestro activar/desactivar de módulos ya es mejor que el de ALFA-1, que
  nunca logra sacar un handler de verdad del `Application` por una
  premisa incorrecta sobre PTB; tabla feature-por-feature del panel de
  administración; 7 candidatos a portar, priorizados) y "Ledger de
  créditos: construido y probado" (diseño, qué se construyó, qué se
  probó). Se actualizó "Huecos reales detectados" (créditos resuelto,
  `contexto.db` sigue abierto con un camino más barato identificado) y el
  catálogo unificado de comandos con `/otorgar` y `creditos_demo`.
- Semáforo: 🟢
- Próximo paso sugerido: de los 3 huecos originales solo queda
  `contexto.db` (persistencia propia de módulo) y la decisión de
  Fernando sobre `contexto.captcha`. El camino más barato para
  `contexto.db`, según lo que confirmó la comparación con ALFA-1, es
  sumar escritura a `contexto.datos.abrir_sqlite_propio()` en vez de
  construir el sistema de scopes-por-tabla del plan original.

### 2026-09-01 — SDK: gestión completa de módulos desde `/mando` + catálogo unificado de comandos
- Commits: ninguno (código y documentación viven en `mictlan-staging/`,
  ambiente descartable sin git — ver la sección de arriba; no se pidió
  commitear en `Mictlan/`).
- ¿Probado contra PostgreSQL real? N/A (staging usa SQLite a propósito).
  Sí se probó funcionalmente de verdad, no solo `py_compile`: script con
  24 aserciones contra un SQLite temporal + una `Application` real de
  `python-telegram-bot` (sin red) — ver detalle en la sección de SDK de
  arriba. Después se desplegó de verdad (`sudo systemctl restart
  mictlan-staging.service`) y se confirmó por journal que los 11 módulos
  reales activos siguieron activos sin interrupción.
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? `mictlan/modules/mando.py` iba a mezclar dos
  secciones reales (Usuarios + Módulos) en un solo archivo — se dividió
  en sub-paquete (`mando/__init__.py` + `usuarios.py` + `modulos.py`)
  siguiendo la regla de modularidad de `CLAUDE.md`, antes de que
  pasara. `mictlan/sdk.py` creció (nuevas clases `_AppRecorder`/
  `_JobQueueRecorder` y funciones de ciclo de vida) — no se dividió esta
  sesión, queda para evaluar si hace falta la próxima vez que se le
  agregue algo.
- ¿Documento actualizado? Sí — se reescribió la sección de SDK con las
  nuevas capacidades (activar/desactivar/eliminar/alternar origen en
  caliente, sin reiniciar el proceso) y se agregó "Catálogo unificado de
  comandos — todos los módulos activos hoy en staging": una referencia
  única con TODOS los comandos que existen hoy en el bot de staging,
  internos y externos, con qué hace cada uno y notas técnicas — escrita
  leyendo el código completo de los 12 módulos externos (antes solo
  estaban documentados sus `permissions`, no su comportamiento real).
- Semáforo: 🟢
- Próximo paso sugerido: con la gestión de módulos ya resuelta, los
  candidatos que quedan son los mismos 3 huecos de siempre —
  `contexto.db` (bloquea que `trivia`/`compartir` sobrevivan un restart),
  el ledger de créditos, y la decisión pendiente de Fernando sobre
  `contexto.captcha` (qué proveedor probar primero, uno global o por
  módulo). Cualquiera de los tres es un buen próximo frente.

### 2026-09-01 — Revisión completa del ambiente de staging + documentación de avances no comiteados
- Commits: ninguno (solo documentación; no se pidió commitear ni pushear
  en esta sesión).
- ¿Probado contra PostgreSQL real? N/A — sesión de solo lectura/revisión,
  ningún cambio de código en `mictlan/` (ni el real ni el de staging).
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? `sdk.py` de staging tiene 494 líneas — supera el
  umbral, pero no se evaluó todavía si mezcla responsabilidades o si
  amerita partirse en sub-paquete (pendiente para cuando se porte al
  Mictlan real).
- ¿Documento actualizado? Sí — se agregó la sección "Avances en el
  ambiente de staging (`mictlan-staging`, sin commitear)" con el
  inventario completo de lo que existe hoy en
  `/home/olimpo/mictlan-staging/mictlan/` (fuera de este repo git) y en
  `external_modules/`: SDK de módulos externos funcional (494 líneas,
  11 módulos de prueba instalados incluyendo uno malicioso de control),
  `proxy.py` probado con DataImpulse real, groundwork de captcha y SMS
  virtual, canal de publicaciones, grupos dinámicos, logging propio con
  redacción de token, y 3 tablas nuevas en el esquema SQLite de staging
  (`sdk_modulos`, `grupos`, `publicaciones_modulo`) que no existen en el
  `db.py` real. Se documentaron también los 2 huecos reales detectados
  en el SDK actual (falta `contexto.db` y ledger de créditos) y la
  decisión abierta sobre `contexto.captcha` (proveedor a probar primero,
  un solo proveedor activo vs. varios) — ambos ya estaban en
  `GUIA_SDK_MODULOS_EXTERNOS.md` (raíz de `mictlan-staging/`) pero no
  reflejados acá. Fernando confirmó explícitamente que
  `mictlan-staging/` es un ambiente descartable, distinto del Mictlan
  real (que corre en `/home/olimpo/mictlan`), y que estos avances se
  portan "poco a poco", no de una sola vez.
- Semáforo: 🟢 — nada roto, el servicio de staging corre sano (verificado
  con `systemctl status` y `journalctl`, sin errores en el journal
  actual). Se detectó un artefacto viejo sin relación con el servicio
  actual (`bot.log` en la raíz, de una sesión manual anterior con
  conflictos de `getUpdates` duplicado) — no es un problema activo, solo
  quedó anotado como limpieza pendiente.
- Próximo paso sugerido: decidir con Fernando qué se porta primero al
  Mictlan real (candidatos: `proxy.py`, ya probado y sin dependencias
  pendientes; o resolver primero el hueco de `contexto.db` en el SDK de
  staging antes de seguir sumando módulos ahí). Aparte, resolver la
  pregunta abierta de `contexto.captcha` para poder avanzar ese frente en
  staging.

### 2026-08-31 — Reglas de conducta obligatorias (por qué existen)
- Commits: (documentación, ver commit de esta entrada en el historial
  de `main`)
- ¿Probado contra PostgreSQL real? N/A — solo documentación.
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — sin cambios de código.
- ¿Documento actualizado? Sí — se agregó al principio de `CLAUDE.md` la
  sección "Reglas de conducta obligatorias", pedida explícitamente por
  Fernando después de tener problemas con una sesión anterior en el VPS
  que actuaba por iniciativa propia en vez de seguir instrucciones
  exactas. Manda sobre el resto del archivo: ejecutar exactamente lo
  pedido sin ampliar el alcance, leer cualquier archivo COMPLETO cuando
  se indique leerlo (nunca un resumen o muestreo parcial), no asumir
  decisiones de diseño no confirmadas, no tomar acciones no pedidas
  (commit/push/crear/borrar), no reinterpretar instrucciones, parar y
  preguntar ante información faltante, no opinar salvo que se pida, y
  reportar con exactitud qué se hizo.
- Semáforo: 🟢
- Próximo paso sugerido: cualquier sesión que note que estas reglas se
  están incumpliendo (propias o de una sesión anterior) debe señalarlo
  explícitamente en vez de seguir adelante como si nada.

### 2026-08-31 — Regla prohibitiva de ALFA-1 como espejo + lista de archivos de referencia
- Commits: (documentación, ver commit de esta entrada en el historial
  de `main`)
- ¿Probado contra PostgreSQL real? N/A — solo documentación.
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — sin cambios de código.
- ¿Documento actualizado? Sí — `CLAUDE.md` suma la sección "Regla
  prohibitiva: ALFA-1 es espejo, nunca código fuente" (tono explícito de
  PROHIBIDO: nunca copiar/pegar código, estructura, nombres o textos de
  ALFA-1 a Mictlan) junto con una lista curada y verificada (rutas
  reales confirmadas, no supuestas) de archivos de `alfa1/` para usar
  como referencia de comparación — documentación de arquitectura, SDK
  de módulos, grupos dinámicos, créditos, mantenimiento/heartbeat/SOMBRA,
  bugs conocidos, y el bug sin resolver de `extra.py`.
- Semáforo: 🟢
- Próximo paso sugerido: con esto queda cerrada la fase de
  documentación de base. Al retomar en el VPS: confirmar sudo acotado
  configurado, y arrancar con el primer ítem del roadmap.

### 2026-08-31 — Revisión de alfa1/docs/ + lecciones nuevas incorporadas
- Commits: (documentación, ver commit de esta entrada en el historial
  de `main`)
- ¿Probado contra PostgreSQL real? N/A — solo documentación.
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — sin cambios de código.
- ¿Documento actualizado? Sí. Se revisó la carpeta completa de
  documentación de ALFA-1 (`alfa1/docs/`, `alfa1/future/`, y los `.md`
  de su raíz) buscando lecciones no capturadas todavía. Se incorporaron
  a `CLAUDE.md`: prefijos de `callback_data` reservados por módulo
  (`mando:`, `svc:`, `reporte:`), la regla de separación estricta de
  canales/chats por propósito, un bug real de parseo de listas de IDs
  desde variables de entorno, la lección sobre capas de parches y
  ambigüedad de "quién manda" en el código, el contrato real de
  `permissions` como scopes (no comandos ni roles) para el futuro SDK,
  la advertencia de que el aislamiento de módulos externos sería solo
  por convención y no por proceso, la disyuntiva sin resolver sobre
  cómo detectar grupos nuevos (`ChatMemberHandler` inmediato vs.
  detección pasiva conservadora de ALFA-1), y un nuevo plan de "Modo de
  mantenimiento" independiente de SOMBRA. Aparte de la documentación de
  Mictlan: se detectó lo que parece ser una credencial real
  (`FOFA_API_KEY`) expuesta como ejemplo en
  `alfa1/future/ALFA1_INTEGRACION_DESDE_CERO.md` — no es un tema de
  Mictlan, se le avisó a Fernando directamente en el chat para que la
  revise/rote, no se tocó el archivo.
- Semáforo: 🟢
- Próximo paso sugerido: con esto, la documentación de base de Mictlan
  está razonablemente completa para que Fernando pase a trabajar
  directamente en el VPS. Al retomar: confirmar que el sudo acotado
  quedó configurado como se documentó, y elegir un primer ítem del
  roadmap (candidatos: `/fuera`/`/callar` una vez decidida su forma de
  invocación, o el modo de mantenimiento, que es chico y no depende de
  ninguna otra decisión pendiente).

### 2026-08-31 — Migraciones, logging, backups, staging + política de sudo en el VPS
- Commits: (documentación, ver commit de esta entrada en el historial
  de `main`)
- ¿Probado contra PostgreSQL real? N/A — solo documentación, ningún
  archivo de `mictlan/` cambió.
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — sin cambios de código.
- ¿Documento actualizado? Sí — se sumaron a `CLAUDE.md` las secciones
  "Migraciones de esquema (plan)", "Logging propio de Mictlan (plan)",
  "Backups de PostgreSQL (plan)" y "Bot de staging (plan)" (los cuatro
  huecos que señalé al revisar qué faltaba detallar), más "Permisos de
  sudo en el VPS (política)" — el alcance exacto de NOPASSWD que
  Fernando va a configurar en el VPS (`systemctl start/stop/restart/
  status mictlan.service` y `journalctl -u mictlan.service`, nada de
  HADES ni de Postgres como superusuario). Este archivo suma el roadmap
  correspondiente a los cuatro huecos.
- Semáforo: 🟢
- Próximo paso sugerido: Fernando va a aplicar la política de sudo en el
  VPS y arrancar a trabajar ahí directamente. Antes de sumar
  funcionalidad nueva, la siguiente sesión debería confirmar que el
  archivo `/etc/sudoers.d/` en el VPS coincide con lo documentado acá
  (no asumirlo). Pendiente además una revisión rápida de
  `alfa1/docs/` en busca de lecciones no capturadas todavía — en curso
  al cerrar esta entrada.

### 2026-08-31 — Documentación ampliada: modularidad, SDK, grupos dinámicos, proxy DataImpulse
- Commits: (cambio solo de documentación, ver commit de esta entrada en
  el historial de `main`)
- ¿Probado contra PostgreSQL real? N/A — no se tocó código, solo
  `CLAUDE.md`/`PROGRESO.md`. Se verificó una sola afirmación factual
  contra el repo real antes de escribirla: `alfa1/samaritan/core.py`
  tiene 14,874 líneas, 486 funciones/métodos y 139 `add_handler`, medido
  con `wc -l`/`grep -c` directo sobre el archivo, no supuesto.
- ¿Regla fija violada? No.
- ¿Algún archivo de `mictlan/` superó ~300-400 líneas o mezcla
  responsabilidades? No — sigue sin cambios de código en esta entrada.
- ¿Documento actualizado? Sí — se agregaron a `CLAUDE.md` las secciones
  "Modularidad: nunca un `core.py`" (con la evidencia de arriba y reglas
  concretas de cuándo partir un módulo en sub-paquete), "SDK de módulos
  externos (plan)", "Grupos dinámicos (plan)" y "Proxies salientes vía
  DataImpulse (plan)". En este archivo se detalló el roadmap
  correspondiente, se marcó como **abierta** (no decidida) la forma de
  invocación de `/fuera`/`/callar`, y se sumó el chequeo de modularidad
  al formato del reporte de salud.
- Semáforo: 🟢
- Próximo paso sugerido: `/fuera`/`/callar` (primero decidir con
  Fernando la forma de invocación), o retomar el bug de `extra.py` en
  `alfa1` (bloqueado esperando que Fernando pegue el resultado de
  `grep -n "^CODIGO,"` sobre una fila real que falle). El SDK, los
  grupos dinámicos y el proxy de DataImpulse quedan como diseño listo
  para construir cuando se prioricen — no son bloqueantes de nada más.
