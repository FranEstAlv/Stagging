# PROGRESO — repo `Stagging` (github.com/FranEstAlv/Stagging)

Bitácora de qué se probó manualmente en este ambiente y cómo — para que
"funciona" nunca dependa solo de que alguien lo cuente de palabra. Mismo
espíritu que el `PROGRESO.md` del Mictlan oficial (fecha, qué se probó,
resultado), adaptado: acá no hay PostgreSQL ni un flujo de commits
propio que trackear — el método de prueba estándar es **SQLite temporal
+ una `Application` real de `python-telegram-bot` (nunca solo
`py_compile`)**, y el resultado se confirma además desplegando de verdad
(`sudo systemctl restart mictlan-staging.service` + revisar
`journalctl` sin errores).

Este repo es un **snapshot del código de un ambiente de pruebas
descartable** — no el Mictlan oficial (`github.com/FranEstAlv/Mictlan`).
Nada de acá se mueve a ese repo sin decidirlo explícitamente antes; ver
`.gitignore` para qué queda afuera siempre (`.env`, `venv/`, `*.db`,
`*.log`, `external_modules/`, `datos_compartidos/`, y los clones
`Mictlan/`/`OLIMPO/`/`Docs/`, cada uno con su propio repo/remoto).

Entradas en orden cronológico inverso (más reciente primero).

---

## Esqueleto funcional del proyecto (snapshot 2026-09-05)

**Esto es una foto de un momento puntual, no un documento vivo** — puede
quedar desactualizado apenas se agregue/cambie una feature. Nunca
reemplaza leer el código real (`mictlan/`, `main.py`); sirve para
orientarse rápido sobre qué existe y dónde, no como fuente de verdad.

**Núcleo** (`mictlan/`): `db.py` — pool `aiosqlite` + esquema completo
(`usuarios`, `membresias`, `blacklist`, `expulsiones`, `mantenimiento`,
`reportes`, `sdk_modulos`, `grupos`, `publicaciones_modulo`,
`creditos_ledger`, `invitaciones`, `heartbeats`, `tecuhtli_estado`,
`captchas_bienvenida`, `pendientes_ingreso`), traductor de sintaxis
Postgres→SQLite, migraciones de columnas + backfills. `roles.py` —
jerarquía miembro/vendedor/administrador/root y el único punto que
traduce rol→emoji (nunca texto plano). `mensajes.py` — envío de mensajes
de servicio con botón "Cerrar" + autoborrado a 30 min. `formato.py` —
helpers de HTML de Telegram (negrita, cursiva, link, etc.).
`paginacion.py` — paginador genérico 2×3 reusable por cualquier panel.
`logs_canal.py` — canal de logs (`LOGS_CHANNEL_ID`, opcional): persiste
CADA evento en `logs_eventos` (insert-only) antes de intentar mandarlo a
Telegram, así un canal mal configurado nunca pierde el evento. Registra
absolutamente toda interacción (cada mensaje, cada callback, vía
`main.py::_log_update`) además de los eventos semánticos ya cableados en
moderación/captcha/ingreso/mantenimiento/grupos/errores. Invisible desde
adentro del propio bot a propósito — ningún panel/comando lo menciona.

**Membresía, moderación e ingreso de nuevo miembro**: `membresias.py`
(ajuste de días, vencidas()), `moderacion.py` (baneo real = expulsión de
todos los grupos + blacklist con motivo/foto, guardia de reingreso),
`vencimientos.py` (job cada hora, expulsión automática por membresía
vencida, sin blacklist), `invitaciones.py` (links de un solo uso,
`member_limit=1`), `modules/grupos.py` (detección automática de
grupos/canales vía `my_chat_member`, grupo principal exclusivo, y el
selector `modo_ingreso` por grupo: `ninguno`/`captcha`/`aprobacion`).
Dos gates alternativos de nuevo miembro, nunca ambos a la vez para el
mismo chat: `bienvenida.py` (captcha de aritmética con botones, kick con
des-baneo si vence el plazo) e `ingreso_admin.py` (aviso a
`ADMIN_GROUP_ID` con botón "Aceptar", ban real sin des-banear si nadie
acepta en 1 minuto — espejo del mecanismo real de ALFA-1). Los tres
guardianes de `ChatMemberHandler.CHAT_MEMBER` (blacklist, captcha,
aprobación) viven en handler-groups distintos (0/1/2) a propósito.

**Consola `/mando`** (`modules/mando/`): `__init__.py` — router +
gate de permiso (DM o `ADMIN_GROUP_ID`, rol root). `usuarios.py` —
panel paginado, detalle con membresía/rol/baneo, ajuste de días,
cambio de rol. `baneo.py` — `ConversationHandler` motivo→foto,
registrado antes del router genérico. `grupos.py` — panel de
grupos, activar/desactivar, marcar principal, selector de
`modo_ingreso`, generar link de invitación. `modulos.py` — gestión en
caliente del SDK de módulos externos (activar/desactivar/eliminar/
alternar origen/detectar). `mantenimiento.py` — ventanas fijas (30
min/2h/indefinido).

**Comandos de miembro** (fuera de `/mando`): `modules/perfil.py`
(`/perfil` — rol, membresía, saldo), `modules/reporte.py` (`/reporte` —
guarda + notifica a `ADMIN_GROUP_ID` con botón "Atendido"),
`modules/canales.py` (`/canales` — miembro con membresía activa, dentro
del grupo principal, se autogenera un link a un grupo/canal secundario),
`modules/creditos.py` (`/otorgar` — root-only, acuña créditos).

**Créditos** (`creditos.py`): ledger insert-only, saldo derivado de
`SUM(delta)`, candado global (`asyncio.Lock`) para evitar doble gasto
bajo concurrencia. `otorgar()` (acuña, solo interno/root) separado de
`cobrar()`/`reembolsar()` (los únicos expuestos a módulos externos vía
el SDK).

**SDK de módulos externos** (`sdk/`, paquete de 12 archivos de una sola
responsabilidad): `scopes.py` (allowlist de permisos + prefijos
peligrosos bloqueados), `manifiestos.py` (lee `manifest.json`),
`importador.py` (import dinámico del `.py`), `ciclo_vida.py`
(activar/desactivar/eliminar en caliente, `remove_handler` real +
cancelación de jobs, guardia contra reimportación), `contexto.py`
(`ContextoModulo`, ensambla los facades), `facades_externos.py`
(`ProxyFacade`/`CaptchaFacade`/`SmsFacade`), `facades_creditos.py`
(asimetría deliberada, sin `otorgar()`), `facades_datos.py`
(`DatosFacade` de solo lectura + `AlmacenPropioFacade` escribible),
`facades_canal.py` (`CanalFacade`, publicación multi-destino),
`recorders.py` (wrappers de `Application`/`job_queue` para poder
desinstalar), `excepciones.py`, `rutas.py`. Infraestructura de apoyo:
`almacen_modulos.py` (un SQLite propio por módulo, WAL, candado propio),
`datos.py` (lectura de CSV/SQLite de referencia, propios/compartidos),
`canal.py` (config de publicación por módulo/destino), `proxy.py`
(DataImpulse), `captcha.py` (resolución de captchas de terceros vía
2Captcha/Anti-Captcha/CapSolver, incluido Cloudflare Turnstile),
`smsvirtual.py` (HeroSMS/SMSPool). Estas dos últimas piezas son
servicios que el propio BOT consume — sin relación con
`bienvenida.py`/`ingreso_admin.py` pese al nombre parecido de
`captcha.py`. **Ciclo de vida corregido 2026-09-05**: entrypoint `async
def` ahora se rechaza explícito (antes fallaba en silencio, sin
registrar nada); `activar_modulo()` es idempotente (antes una doble
activación sin desactivar en el medio dejaba handlers huérfanos sin
referencia); `sys.path` se limpia al eliminar un módulo (antes crecía
para siempre). Guía completa y normativa (instrucciones
obligatorias/prohibitivas a nivel atómico) en
`GUIA_SDK_MODULOS_EXTERNOS.md`, reescrita el mismo día.

**Mictlantecuhtli** (segundo bot de respaldo/failover, proceso separado):
`heartbeat.py` (instalado en el bot PRINCIPAL, late cada 60s, poda a
500 filas), `mictlantecuhtli.py` (entrypoint propio, mismo
`DATABASE_URL`, sin sdk/roles.asegurar_root), `tecuhtli/estado.py`
(máquina de 5 fases por umbrales), `tecuhtli/evaluador.py` (job cada
30s, fase `respaldo_activo` "pegajosa"), `tecuhtli/acciones.py`
(restringir/liberar todos los grupos gestionados, nunca banea/expulsa),
`tecuhtli/recuperacion.py` (`/reactivar` con secreto + ventana de 30s,
`/tecuhtli_simular`).

**Entrypoint** (`main.py`): arma la `Application`, `load_dotenv()`,
logging propio con redacción de token, registra cada `install_xxx(app)`
en orden (baneo antes que mando por el `ConversationHandler`),
`allowed_updates=Update.ALL_TYPES` (necesario para `chat_member`).

---

### 2026-09-05 (tarde) — Canal de logs, 3 fixes del SDK de módulos y reescritura de la guía SDK

- **Qué se probó**:
  - `mictlan/modules/perfil.py`: fix de `AttributeError` real en
    `/perfil` (`.strftime()` sobre `membresia['fin']`, que llega como
    `TEXT` plano de SQLite, no `datetime` — mismo criterio que
    `_formatear_fecha()` de `modules/mando/usuarios.py`).
  - `mictlan/logs_canal.py` (nuevo): canal de logs con persistencia
    garantizada (`logs_eventos` insert-only, escrito ANTES de intentar
    el envío a Telegram — mejora deliberada sobre `send_log_event` de
    ALFA-1, que solo vive en el historial del chat). Conectado a: error
    handler global (`main.py`), moderación (expulsión de todos los
    grupos, reingreso bloqueado), captcha vencido, ingreso
    aceptado/expulsado, grupo nuevo detectado, mantenimiento
    activar/desactivar. Extendido después (a pedido explícito) para
    registrar **absolutamente toda interacción** vía
    `main.py::_log_update`, no solo los eventos curados. Confirmado por
    grep que ningún panel/comando/menú del bot menciona el canal de
    logs en texto visible al usuario — por seguridad, invisible desde
    adentro del propio bot.
  - `mictlan/sdk/importador.py` + `mictlan/sdk/ciclo_vida.py`: 3 huecos
    reales del runtime del SDK, encontrados en una auditoría a fondo
    pedida explícitamente — entrypoint `async def` que fallaba en
    silencio (ahora se rechaza con `ModuloInvalido` antes de marcar el
    módulo activo), `activar_modulo()` no idempotente (una doble
    activación sin desactivar en el medio dejaba handlers huérfanos sin
    referencia en el `Application`), `sys.path` que nunca se limpiaba
    al eliminar un módulo.
- **Cómo**: 2 aserciones (`/perfil`), 12 + 3 aserciones (`logs_canal.py`
  + el logging total), 8 aserciones (los 3 fixes del SDK, creando
  módulos de prueba reales en `external_modules/`, borrados al
  terminar) — todas con SQLite temporal + `Application` real, Bot API
  mockeada con `AsyncMock`.
- **Resultado**: ✅ todas. Desplegado en cada paso (`systemctl restart
  mictlan-staging.service`), journal limpio, los 11 módulos externos
  reales (`eco`/`trivia`/`search`/`cuentatlg`/etc.) siguieron activos
  sin interrupción tras los fixes del SDK.
- **Documentación**: `GUIA_SDK_MODULOS_EXTERNOS.md` reescrita por
  completo (la versión del 31/08 había quedado obsoleta) — cambio de
  enfoque a instrucciones `OBLIGATORIO`/`PROHIBIDO` a nivel atómico,
  con cita exacta de archivo:línea detrás de cada regla no obvia.

### 2026-09-05 — Captcha de bienvenida generalizado + ingreso por aprobación de admin + selector de modo por grupo

- **Qué se probó**: `mictlan/bienvenida.py` (captcha de aritmética con
  botones al entrar a un grupo, generalizado para aplicar a CUALQUIER
  grupo con `grupos.modo_ingreso='captcha'`, ya no solo el principal);
  `mictlan/ingreso_admin.py` (espejo del mecanismo real de ALFA-1,
  `samaritan/core.py`: `send_welcome_message`/`pending_new_members`/
  `activate_button_handler`/`auto_expel_unapproved_member` — nuevo
  miembro silenciado, aviso con botón "✅ Aceptar" a `ADMIN_GROUP_ID`
  (adaptación pedida por Fernando: ALFA-1 lo manda al grupo privado,
  Mictlan al grupo de gestión), gateado a rol ≥ vendedor, ventana de 1
  minuto, **ban real sin des-banear** si nadie acepta a tiempo — a
  diferencia del captcha normal, que sí des-banea/kickea); nuevo panel
  en `/mando > Grupos` para elegir `modo_ingreso` por grupo
  (`ninguno`/`captcha`/`aprobacion`), con backfill que preserva el
  captcha ya activo en el grupo principal sin pisar un modo ya elegido a
  propósito.
- **Cómo**: 19 aserciones (`bienvenida.py`) + 20 aserciones
  (`ingreso_admin.py` + selector de modo), ambas con SQLite temporal +
  una `Application` real de `python-telegram-bot` (Bot API mockeada con
  `AsyncMock`, nunca red real) — incluye el caso de administrador/root
  exento, click de un usuario no destinatario, timeout idempotente
  (job que corre después de que ya se resolvió), y la convivencia de los
  tres guardianes de `ChatMemberHandler.CHAT_MEMBER`
  (`moderacion.py`/`bienvenida.py`/`ingreso_admin.py`) en handler-groups
  separados (0/1/2) — sin esa separación, python-telegram-bot solo
  ejecuta el primero que matchea dentro de un mismo grupo y los otros
  dos nunca correrían.
- **Resultado**: ✅ 19/19 y ✅ 20/20. Desplegado (`systemctl restart
  mictlan-staging.service`), journal limpio en ambos redeploys.

### 2026-09-02 — Mictlantecuhtli: heartbeat, máquina de estados, recuperación

- **Qué se probó**: `mictlan/heartbeat.py` (escritura real de latidos +
  poda a 500 filas), `mictlan/tecuhtli/estado.py` (cálculo de fase por
  umbrales: normal/alerta/critico/respaldo_activo), `evaluador.py`
  (transiciones automáticas, fase `respaldo_activo` "pegajosa" — no baja
  sola aunque el heartbeat vuelva), enganche con `mantenimiento.py`
  (nunca escala si Mictlan está en mantenimiento deliberado),
  `recuperacion.py` (`/reactivar` con ventana de 30s + secreto,
  `/tecuhtli_simular`), autorización root-only.
- **Cómo**: 27 aserciones automatizadas (SQLite temporal, cliente de
  Telegram mockeado) — umbrales exactos, restricción real de grupos
  simulada (`set_chat_permissions`), ventana de recuperación
  correcta/incorrecta/vencida, silencio total para usuarios sin rol
  root.
- **Despliegue real**: token de Telegram real provisto por Fernando
  (`@respaldomictlanstagg_bot`), agregado a `.env`. Confirmado con
  `getMe()` que conecta de verdad. Corre en vivo como proceso manual
  (`nohup python mictlantecuhtli.py &`) — **todavía no es un servicio
  systemd** (ver `Mictlan/DESPLIEGUE_MICTLANTECUHTLI.md` para los
  comandos exactos de cómo convertirlo). Confirmado leyendo la base real
  que calcula el estado correcto (`normal`) a partir de los heartbeats
  reales del bot principal.
- **Resultado**: ✅ 27/27 aserciones, proceso corriendo sin errores.

### 2026-09-02 — Grupo principal, links de invitación de un solo uso, expulsión automática por membresía vencida

- **Qué se probó**: `grupos.establecer_principal()`/`obtener_principal()`
  (exclusividad — nunca 2 grupos principales a la vez), migración de la
  columna `principal` sobre una base **con datos preexistentes** (no
  una DB nueva vacía), `invitaciones.generar_link()` (member_limit=1),
  panel de `/mando` (solo genera link para el grupo principal), comando
  `/canales` (miembro con membresía activa, dentro del grupo principal,
  nunca genera el link del propio principal), `vencimientos.py`
  (expulsión automática de **todos** los grupos gestionados cuando la
  membresía vence, auditada con `tipo='membresia_vencida'`, distinta de
  un baneo — nunca bloquea reingreso).
- **Cómo**: 25 aserciones automatizadas (SQLite temporal + Application
  real).
- **Resultado**: ✅ 25/25. Desplegado (`systemctl restart`), journal
  limpio, migración confirmada por lectura directa de la base
  persistente real (`PRAGMA table_info`).

### 2026-09-02 — Privacidad: ningún nombre de rol como texto plano

- **Qué se probó**: `/perfil`, detalle de usuario y submenú "Cambiar rol"
  de `/mando` — que nunca aparezca la palabra "root"/"administrador"/
  "vendedor"/"miembro" en ningún mensaje o botón, solo el emoji
  correspondiente (`roles.emoji_rol()`).
- **Cómo**: 6 aserciones de regresión nuevas sumadas a la suite existente
  (39 aserciones totales corridas, incluidas guardas explícitas
  buscando esas palabras en el texto/botones generados).
- **Resultado**: ✅ 39/39.

### 2026-09-01 — Acciones de membresía en `/mando` (días, rol) + baneo/lista negra

- **Qué se probó**: `membresias.ajustar_dias()` (+7/+30/-7/-30, sin
  membresía previa restar es no-op), `roles.establecer_rol()`, panel
  paginado de usuarios con detalle, y el flujo completo de baneo:
  `ConversationHandler` (motivo → foto → blacklist + expulsión real de
  todos los grupos), cancelación a mitad de flujo, guardia de
  reingreso (`ChatMemberHandler.CHAT_MEMBER` re-expulsa a un usuario en
  blacklist que vuelve a entrar), desbaneo, "ver reporte" (reenvía la
  foto real).
- **Cómo**: 36 aserciones automatizadas (SQLite temporal + una
  `Application` real de principio a fin, incluido el `ConversationHandler`
  completo).
- **Resultado**: ✅ 36/36. Desplegado, journal limpio.

### 2026-09-01 — Modo de mantenimiento

- **Qué se probó**: activar por tiempo fijo (30 min/2 h) e indefinido,
  nunca dos ventanas activas a la vez, expiración automática, finalizar
  manual, panel completo de `/mando`.
- **Cómo**: 24 aserciones automatizadas.
- **Resultado**: ✅ 24/24. Desplegado, journal limpio.

### 2026-09-01 — SDK de módulos externos: gestión completa desde `/mando`

- **Qué se probó**: activar/desactivar/eliminar/alternar origen de un
  módulo externo **en caliente** (sin reiniciar el proceso) — incluye
  confirmar que activar/desactivar sacan de verdad el handler del
  `Application` (`remove_handler`) y cancelan jobs programados, no solo
  un guard que lo silencia.
- **Cómo**: 24 aserciones (SQLite temporal + `Application` real, sin
  red).
- **Resultado**: ✅ 24/24. Desplegado, los 11 módulos externos reales
  activos siguieron activos sin interrupción.

### 2026-09-01 — Comparación con el SDK de ALFA-1 + ledger de créditos

- **Qué se probó**: `creditos.py` (insert-only, saldo derivado de
  `SUM(delta)`) bajo concurrencia real — 5 cobros simultáneos
  (`asyncio.gather`) contra un saldo que solo alcanza para 4.
- **Cómo**: 20 aserciones, incluida la prueba de condición de carrera
  real.
- **Resultado**: ✅ 20/20 — exactamente 4 cobros pasan, el 5º falla por
  saldo insuficiente. Desplegado.

### 2026-09-01 — Persistencia propia de módulo (`contexto.datos.db`)

- **Qué se probó**: 50 escrituras concurrentes de "usuarios" distintos
  con candado propio del módulo (control negativo sin candado, que sí
  pierde datos, para confirmar que el candado hace falta), y que
  `trivia`/`compartir` sobreviven un "restart" simulado completo
  (conexiones cerradas + caché del SDK vaciada + módulos reimportados).
- **Cómo**: 22 aserciones.
- **Resultado**: ✅ 22/22. Desplegado.

### 2026-09-01 — Paginación 2×3 + sección "Grupos" de `/mando`

- **Qué se probó**: paginador genérico (`paginacion.py`) con 13 filas
  reales, navegación, "Volver" preservando página de origen; detección
  automática de grupos (`ChatMemberHandler` sobre `my_chat_member` real,
  no un atajo de prueba), activar/desactivar desde la UI persistiendo
  de verdad.
- **Cómo**: 33 + 15 aserciones (dos entregas).
- **Resultado**: ✅ 48/48 combinadas. Desplegado.

---

## Cómo agregar una entrada nueva

```
### AAAA-MM-DD — <resumen corto>
- **Qué se probó**: ...
- **Cómo**: cantidad de aserciones y método (SQLite temporal +
  Application real / despliegue en vivo con token real / etc.).
- **Resultado**: ✅ o ❌ + detalle. Si se desplegó de verdad, decir si el
  journal quedó limpio.
```

Antes de cada `git push` a este repo: confirmar explícitamente (no dar
por hecho) que `.gitignore` sigue excluyendo `.env` y cualquier archivo
con secretos reales — ver la entrada correspondiente en el historial de
commits para el chequeo hecho cada vez.
