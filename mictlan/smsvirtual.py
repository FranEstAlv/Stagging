from __future__ import annotations

import os

import httpx

# HeroSMS y SMSPool: numeros virtuales para SMS/OTP. Cada uno con su propio
# formato de auth y respuesta -- no comparten esqueleto como los captcha.

_PROVEEDORES = {
    "herosms": {"env": "HEROSMS_API_KEY"},
    "smspool": {"env": "SMSPOOL_API_KEY"},
}


class ProveedorDesconocido(Exception):
    pass


class SmsAPIError(Exception):
    pass


def proveedores_disponibles() -> list[str]:
    return [p for p, cfg in _PROVEEDORES.items() if os.environ.get(cfg["env"])]


def _api_key(proveedor: str) -> str:
    cfg = _PROVEEDORES.get(proveedor)
    if not cfg:
        raise ProveedorDesconocido(proveedor)
    key = os.environ.get(cfg["env"], "")
    if not key:
        raise SmsAPIError(f"{cfg['env']} no configurada")
    return key


def _mounts(proxies: dict | None) -> dict:
    return {p: httpx.AsyncHTTPTransport(proxy=u) for p, u in (proxies or {}).items()}


async def balance(proveedor: str, proxies: dict | None = None) -> str:
    """Devuelve el saldo como string -- cada proveedor lo entrega en un
    formato distinto (HeroSMS: texto plano; SMSPool: JSON)."""
    key = _api_key(proveedor)
    async with httpx.AsyncClient(mounts=_mounts(proxies), timeout=15) as client:
        if proveedor == "herosms":
            r = await client.get(
                "https://hero-sms.com/stubs/handler_api.php",
                params={"action": "getBalance", "api_key": key},
            )
            r.raise_for_status()
            texto = r.text.strip()
            if texto.startswith("ACCESS_BALANCE:"):
                return texto.split(":", 1)[1]
            raise SmsAPIError(f"respuesta inesperada de herosms: {texto}")
        elif proveedor == "smspool":
            r = await client.post("https://api.smspool.net/request/balance", data={"key": key})
            r.raise_for_status()
            data = r.json() or {}
            if "balance" not in data:
                raise SmsAPIError(f"respuesta inesperada de smspool: {data}")
            return str(data["balance"])
        else:
            raise ProveedorDesconocido(proveedor)


__all__ = [
    "ProveedorDesconocido",
    "SmsAPIError",
    "proveedores_disponibles",
    "balance",
]
