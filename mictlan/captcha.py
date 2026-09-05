from __future__ import annotations

import asyncio
import os

import httpx

# Los 3 proveedores comparten el mismo esqueleto (clientKey + createTask ->
# getTaskResult, errorId=0/status="ready" como exito) -- confirmado leyendo
# la documentacion oficial de cada uno. Lo unico que cambia de verdad es el
# nombre exacto del "type" de tarea (mayusculas distintas en CapSolver).

_PROVEEDORES = {
    "2captcha": {"base_url": "https://api.2captcha.com", "env": "TWOCAPTCHA_API_KEY"},
    "capsolver": {"base_url": "https://api.capsolver.com", "env": "CAPSOLVER_API_KEY"},
    "anticaptcha": {"base_url": "https://api.anti-captcha.com", "env": "ANTICAPTCHA_API_KEY"},
}

_TIPOS_TAREA = {
    "recaptcha_v2": {
        "2captcha": "RecaptchaV2TaskProxyless",
        "anticaptcha": "RecaptchaV2TaskProxyless",
        "capsolver": "ReCaptchaV2TaskProxyLess",
    },
    # Cloudflare Turnstile: la pagina telegram.org/support lo exige
    # (sitekey 0x4AAAAAABeXKow67DnvUBPD); los 3 proveedores lo soportan
    # segun sus docs oficiales (ver GUIA_SDK_MODULOS_EXTERNOS.md).
    "turnstile": {
        "2captcha": "TurnstileTaskProxyless",
        "anticaptcha": "TurnstileTaskProxyless",
        "capsolver": "AntiTurnstileTaskProxyLess",
    },
    "imagen": {
        "2captcha": "ImageToTextTask",
        "anticaptcha": "ImageToTextTask",
        "capsolver": "ImageToTextTask",
    },
}


class ProveedorDesconocido(Exception):
    pass


class CaptchaAPIError(Exception):
    pass


def proveedores_disponibles() -> list[str]:
    return [p for p, cfg in _PROVEEDORES.items() if os.environ.get(cfg["env"])]


def _cfg(proveedor: str) -> dict:
    cfg = _PROVEEDORES.get(proveedor)
    if not cfg:
        raise ProveedorDesconocido(proveedor)
    return cfg


def _api_key(proveedor: str) -> str:
    cfg = _cfg(proveedor)
    key = os.environ.get(cfg["env"], "")
    if not key:
        raise CaptchaAPIError(f"{cfg['env']} no configurada")
    return key


def tipo_tarea(concepto: str, proveedor: str) -> str:
    mapa = _TIPOS_TAREA.get(concepto, {})
    if proveedor not in mapa:
        raise ProveedorDesconocido(f"{proveedor} no soporta la tarea '{concepto}'")
    return mapa[proveedor]


def _mounts(proxies: dict | None) -> dict:
    return {p: httpx.AsyncHTTPTransport(proxy=u) for p, u in (proxies or {}).items()}


async def _post(proveedor: str, path: str, payload: dict, proxies: dict | None, timeout: float) -> dict:
    async with httpx.AsyncClient(mounts=_mounts(proxies), timeout=timeout) as client:
        r = await client.post(f"{_cfg(proveedor)['base_url']}{path}", json=payload)
        r.raise_for_status()
        return r.json() or {}


async def balance(proveedor: str, proxies: dict | None = None) -> float:
    data = await _post(
        proveedor, "/getBalance", {"clientKey": _api_key(proveedor)}, proxies, timeout=15
    )
    if data.get("errorId"):
        raise CaptchaAPIError(data.get("errorDescription") or str(data))
    return float(data.get("balance", 0))


async def _crear_tarea(proveedor: str, task: dict, proxies: dict | None) -> str:
    payload = {"clientKey": _api_key(proveedor), "task": task}
    data = await _post(proveedor, "/createTask", payload, proxies, timeout=15)
    if data.get("errorId"):
        raise CaptchaAPIError(data.get("errorDescription") or str(data))
    task_id = data.get("taskId")
    if not task_id:
        raise CaptchaAPIError(f"respuesta sin taskId: {data}")
    return str(task_id)


async def _resultado_tarea(
    proveedor: str, task_id: str, proxies: dict | None, intentos: int = 20, espera: float = 3
) -> dict:
    for _ in range(intentos):
        data = await _post(
            proveedor,
            "/getTaskResult",
            {"clientKey": _api_key(proveedor), "taskId": task_id},
            proxies,
            timeout=15,
        )
        if data.get("errorId"):
            raise CaptchaAPIError(data.get("errorDescription") or str(data))
        if data.get("status") == "ready":
            return data.get("solution") or {}
        await asyncio.sleep(espera)
    raise CaptchaAPIError(f"timeout esperando resultado de {proveedor} (task {task_id})")


async def resolver_recaptcha_v2(
    proveedor: str, sitekey: str, url: str, proxies: dict | None = None
) -> str:
    task = {
        "type": tipo_tarea("recaptcha_v2", proveedor),
        "websiteURL": url,
        "websiteKey": sitekey,
    }
    task_id = await _crear_tarea(proveedor, task, proxies)
    solucion = await _resultado_tarea(proveedor, task_id, proxies)
    return solucion.get("gRecaptchaResponse", "")


async def resolver_turnstile(
    proveedor: str, sitekey: str, url: str, proxies: dict | None = None
) -> str:
    """Resuelve un Cloudflare Turnstile (ej. telegram.org/support).

    Devuelve el token para POSTear a /support/captcha, que lo valida y
    marca la cookie stel_ssid como verificada (ver JS onTurnstileSuccess
    en la propia pagina). El token se pide Proxyless: la verificacion la
    hace el proveedor con su propia IP, el POST posterior si sale por
    nuestro proxy."""
    task = {
        "type": tipo_tarea("turnstile", proveedor),
        "websiteURL": url,
        "websiteKey": sitekey,
    }
    task_id = await _crear_tarea(proveedor, task, proxies)
    solucion = await _resultado_tarea(proveedor, task_id, proxies)
    return solucion.get("token", "")


async def resolver_imagen(proveedor: str, imagen_base64: str, proxies: dict | None = None) -> str:
    task = {"type": tipo_tarea("imagen", proveedor), "body": imagen_base64}
    task_id = await _crear_tarea(proveedor, task, proxies)
    solucion = await _resultado_tarea(proveedor, task_id, proxies)
    return solucion.get("text", "")


__all__ = [
    "ProveedorDesconocido",
    "CaptchaAPIError",
    "proveedores_disponibles",
    "balance",
    "resolver_recaptcha_v2",
    "resolver_turnstile",
    "resolver_imagen",
]
