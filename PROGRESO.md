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
