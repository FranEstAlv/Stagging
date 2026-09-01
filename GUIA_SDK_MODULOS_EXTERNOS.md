# Guía — Contrato SDK para módulos externos que llaman un servicio HTTP externo

Documento de staging, no del Mictlan real todavía. Se escribe acá porque
"todo lo desarrollamos en pruebas, si funciona lo replicamos igual al
real" — cuando esto quede validado, se porta tal cual a `CLAUDE.md` del
repo `mictlan` (sección "SDK de módulos externos").

Basada en dos fuentes reales, no en teoría:
- `mictlan/sdk.py` de esta carpeta (`ContextoModulo`, scopes, `contexto.proxy`
  ya probado con DataImpulse real).
- `alfa1/samaritan/services/smspool.py` (1450 líneas) — el único módulo de
  ALFA-1 que de verdad llama a un servicio HTTP externo de punta a punta,
  cobra créditos, persiste historial y sobrevive un reinicio a mitad de
  una compra. Se usa como espejo (regla de `CLAUDE.md`: nunca copiar
  código, sí copiar la lección).

## Resultado de revisar smspool.py: 2 huecos reales en el SDK actual

Antes de la receta paso a paso, lo más importante que salió de leer
smspool.py completo: **hoy el SDK de Mictlan no alcanza para construir
un módulo de ese nivel**. Le faltan dos cosas que smspool.py sí tiene:

1. **Persistencia propia del módulo.** smspool.py tiene 4 tablas propias
   (`smspool_orders`, `smspool_config`, `smspool_price_brackets`,
   `smspool_available_services`) vía `core.get_db_connection()` crudo.
   `contexto` de Mictlan hoy no da forma de crear ni tocar ninguna tabla
   — todo lo que no sea `usuarios.*`/`mensajes.enviar`/`proxy.usar` está
   bloqueado por diseño (a propósito, fase conservadora). Sin esto, un
   módulo real no puede recordar un pedido si el proceso se reinicia.
2. **Créditos.** smspool.py cobra y reembolsa vía
   `context.application.bot_data["credit_service"]` (`svc.spend()`,
   `svc.mint()`). Mictlan todavía no tiene el ledger de créditos
   (`CLAUDE.md` lo tiene como plan, "Lo bueno — replicar"). Sin esto,
   ningún módulo que cobre por una acción se puede construir de verdad,
   solo simular.

**Recomendación concreta**: antes de construir un módulo de venta real
(SMSPool o cualquier otro del inventario de `Docs/`), el próximo paso de
SDK debería ser agregar `contexto.db` (scope `db.propio`, acotado a
tablas que el módulo declaró en su manifest) — es lo mínimo para que un
módulo sobreviva un restart, que es exactamente lo que smspool.py
resuelve con su job de reconciliación al arrancar (`_reconcile_job`,
línea 913). El ledger de créditos puede esperar más — se puede simular
con `contexto.obtener_rol`/mensajes mientras tanto, igual que hicimos con
`trivia` (puntaje en memoria, sin plata real de por medio).

## Paso a paso — módulo que llama un servicio HTTP externo

Esto es lo que SÍ se puede construir hoy, con el SDK tal cual está.

### 1. Manifest (`external_modules/<id>/manifest.json`)

```json
{
  "module_id": "mi_servicio",
  "nombre": "Nombre legible",
  "version": "1.0.0",
  "entrypoint": "mi_servicio:install_modulo",
  "permissions": ["mensajes.enviar", "proxy.usar"],
  "env": ["MI_SERVICIO_API_KEY"]
}
```

- `permissions` son scopes, nunca comandos ni roles (regla ya fijada en
  `mictlan/sdk.py`, lección de los parches R2.31.8.28.1/.28.2 de ALFA-1).
- `env` es informativo (documenta qué variable necesita el módulo) — el
  SDK no lo valida todavía, es responsabilidad del propio módulo leerla.

### 2. La API key del servicio — nunca la lee el SDK, la lee el módulo

Mismo patrón que `_api_key()` en smspool.py (línea 46) y que
`mictlan/proxy.py`: lectura perezosa, dentro de la función, nunca a nivel
de módulo.

```python
import os

def _api_key() -> str:
    return os.environ.get("MI_SERVICIO_API_KEY", "")
```

El SDK no gatea esto con un scope — es la credencial del *servicio
externo*, no un recurso de Mictlan. Si falta, el propio módulo debe
devolver un mensaje claro (ver `proxycheck.py`, `_proxyinfo_command` como
ejemplo del patrón "avisar qué falta", no un traceback).

### 3. HTTP siempre vía `contexto.proxy`, con `httpx`, nunca `aiohttp` directo

smspool.py usa `aiohttp.ClientSession()` sin proxy (tiene sentido, es de
antes de que existiera esta pieza). En Mictlan, cualquier módulo que
salga a un servicio de terceros de consumo/volumen debe salir por
DataImpulse — mismo criterio que ya validamos con `proxycheck`:

```python
import httpx

async def _post(contexto, path: str, data: dict) -> dict:
    proxies = contexto.proxy.httpx()
    mounts = {p: httpx.AsyncHTTPTransport(proxy=u) for p, u in proxies.items()}
    async with httpx.AsyncClient(mounts=mounts, timeout=15) as client:
        r = await client.post(f"{BASE_URL}{path}", data={"key": _api_key(), **data})
        r.raise_for_status()
        return r.json() or {}
```

Envolver esto en un `try/except` en cada callsite (no acá adentro) para
poder responderle al usuario con un mensaje claro en vez de un
traceback — smspool.py hace esto en *cada* llamada a `_api_post`
(líneas 723, 767, 846, 936, 1183, 1212, 1361, 1391).

### 4. Nunca confiar en caché de sesión para montos/decisiones críticas

smspool.py cachea `_FLOW[user.id]` (servicio/país elegidos) para no
volver a preguntar, **pero antes de cobrar créditos** (acción "buy",
línea 1159) revalida todo server-side: stock (`/sms/stock`), balance real
(`svc.get_balance`), y solo después descuenta. La caché es para UX, la
verdad siempre se re-consulta antes de una acción irreversible.

### 5. Idempotencia con estado en memoria acotado, no en base

`_ACTIVE: dict[str, dict]` (línea 31) evita procesar dos veces el mismo
pedido (por ejemplo, dos aprietes rápidos de "Verificar ahora"). Está
acotado por la cantidad de pedidos *activos* simultáneos (se borra al
resolver éxito/fallo/cancelación) — no es el anti-patrón de caché sin
límite que advierte `CLAUDE.md`, porque tiene ciclo de vida completo
documentado. Cualquier módulo con un flujo de "acción en progreso"
debería seguir este mismo patrón: dict acotado por elementos activos,
nunca por usuarios históricos.

### 6. Reembolsar en cualquier camino de fallo, sin excepción

Cada `return` de error en la rama "buy" de smspool.py (líneas 1219,
1228, 1238, 1296) reembolsa antes de avisarle al usuario. Regla dura para
cualquier módulo que cobre algo: si la acción no se completó, no se
queda con el cobro — sin importar en qué paso falló.

### 7. Reconciliación al arrancar, para lo que quedó a medias

`_reconcile_job` (línea 913) corre 30s después de instalar el módulo:
busca pedidos `pending` más viejos que `_MAX_ORDER_AGE_MIN` (25 min, no
resueltos porque el proceso se reinició a mitad de un polling) y los
cierra (éxito si ya había llegado el código, reembolso si no). Sin esto,
un restart del bot deja créditos cobrados sin resolver para siempre. Este
es justo el motivo #1 del hueco de persistencia mencionado arriba — sin
`contexto.db`, no hay dónde guardar el pedido para poder reconciliarlo
después de un restart.

### 8. Namespace de callback_data y grupo de handlers

smspool usa el prefijo `sms:` (nunca colisiona con `mando:`/`svc:`/
`reporte:`/`trivia:`/etc.) y registra sus handlers en
`group=-40` (ejecuta antes que el grupo por default) — en Mictlan hoy
`sdk.py` registra todo en el grupo por default (0); si en algún momento
un módulo necesita prioridad de handler, se puede pasar explícito en
`app.add_handler(..., group=N)` desde el propio módulo (el SDK no lo
restringe, `install_modulo` recibe el `app` real).

## Servicios externos revisados (de `Docs/`)

Leídos completos: 2Captcha, CapSolver, Anti-Captcha (resolución de
captchas), Bright Data y Decodo (proxy/scraping). DataImpulse ya está
integrado y probado con credenciales reales.

### Captchas — los 3 comparten el mismo esqueleto

| | 2Captcha | CapSolver | Anti-Captcha |
|---|---|---|---|
| Base URL | `api.2captcha.com` | `api.capsolver.com` | `api.anti-captcha.com` |
| Auth | `clientKey` en el body JSON | igual | igual |
| Flujo | `createTask` → `getTaskResult` | igual | igual |
| Éxito | `errorId=0`, `status="ready"` | igual | igual |
| En progreso | `status="processing"` | igual | igual |
| SDK Python oficial | `2captcha-python` | `capsolver` (con discrepancia: la propia doc de CapSolver no lo lista como oficial en una página, aunque el repo se autodenomina oficial) | `anticaptchaofficial` |

**El único dato que cambia de verdad entre los tres es el nombre exacto
del `type` de tarea** — mismo concepto, string distinto:

| Tarea | 2Captcha / Anti-Captcha | CapSolver |
|---|---|---|
| reCAPTCHA v2 sin proxy | `RecaptchaV2TaskProxyless` | `ReCaptchaV2TaskProxyLess` |
| reCAPTCHA v3 sin proxy | `RecaptchaV3TaskProxyless` | `ReCaptchaV3TaskProxyLess` |
| Cloudflare Turnstile | `TurnstileTaskProxyless` | *(no confirmado en la doc leída — no asumir sin verificar)* |
| Imagen a texto | `ImageToTextTask` | igual |

Ojo con las mayúsculas (`Recaptcha` vs `ReCaptcha`, `Proxyless` vs
`ProxyLess`) — es una diferencia real entre proveedores, no un typo de
las docs.

### Proxies de terceros — mismo formato que DataImpulse

Tanto **Bright Data** (modo proxy puro, no Web Unlocker) como **Decodo**
usan exactamente el mismo formato `usuario:password@host:puerto` que ya
tiene `mictlan/proxy.py`:

- DataImpulse: `http://usuario:password@gw.dataimpulse.com:823`
- Bright Data: `http://brd-customer-<ID>-zone-<ZONA>:<PASS>@brd.superproxy.io:44445`
- Decodo: `http://user-<USUARIO>:<PASS>@gate.decodo.com:7000`

Los tres soportan targeting geográfico metido en el username (DataImpulse
`__cr.<pais>`, Decodo `-country-xx`, Bright Data vía nombre de zona) y
sesiones "sticky" con un sufijo de sesión. Bright Data además tiene un
segundo modo (Web Unlocker, `POST api.brightdata.com/request` con Bearer
token) para sitios con anti-bot fuerte — no es un proxy tradicional, es
más parecido a los servicios de captcha en forma (un solo endpoint POST).

## Propuesta: `contexto.captcha`, mismo criterio que `contexto.proxy`

No implementado todavía — esto es la propuesta a confirmar antes de
tocar `mictlan/sdk.py` de nuevo.

```python
class CaptchaFacade:
    """contexto.captcha -- interfaz unica sobre cualquier proveedor que
    siga el patron createTask/getTaskResult. El proveedor activo se
    define en .env (CAPTCHA_PROVIDER=2captcha|capsolver|anticaptcha),
    nunca hardcodeado dentro de un modulo -- mismo criterio que ya usa
    contexto.proxy con DataImpulse."""

    async def resolver_recaptcha_v2(self, sitekey: str, url: str) -> str: ...
    async def resolver_turnstile(self, sitekey: str, url: str) -> str: ...
    async def resolver_imagen(self, imagen_base64: str) -> str: ...
```

Internamente, una tabla `_PROVEEDORES` (base_url + mapa de `type` de
tarea por proveedor, por la diferencia de mayúsculas de arriba) + la
misma lógica `createTask` → poll `getTaskResult` (con el mismo backoff
documentado: reintentar en 3-5s mientras `status="processing"`).
Permiso nuevo: `captcha.resolver`.

**Necesito definir con vos antes de construirlo:**
1. ¿Con qué proveedor probamos primero — me pasás una `clientKey` real de
   alguno de los tres (igual que hiciste con el proxy), o armo el
   contrato completo primero y lo dejamos sin probar con red real hasta
   que tengas una cuenta?
2. ¿`contexto.captcha` debe soportar un solo proveedor activo a la vez
   (variable de entorno global), o un módulo debería poder pedir un
   proveedor específico si alguna vez conviene (por ejemplo, uno más
   barato para imagen-a-texto y otro para reCAPTCHA)?

## Checklist para revisar cualquier módulo nuevo antes de darlo por bueno

- [ ] ¿Lee su API key de forma perezosa, nunca a nivel de módulo?
- [ ] ¿Sale a internet vía `contexto.proxy`, no con su propio cliente HTTP suelto?
- [ ] ¿Revalida server-side antes de cualquier cobro/acción irreversible?
- [ ] ¿Tiene un dict acotado (no ilimitado) para evitar procesar dos veces la misma acción?
- [ ] ¿Reembolsa en *todos* los caminos de fallo, no solo el camino feliz?
- [ ] ¿Sobrevive un restart de Mictlan a mitad de una operación? (si la respuesta es "no" porque no hay dónde persistir, es señal de que hace falta `contexto.db` antes de seguir)
- [ ] ¿Su `callback_data` usa un prefijo propio sin colisionar con los reservados?
