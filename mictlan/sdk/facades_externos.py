from __future__ import annotations

from .. import captcha, proxy, smsvirtual
from .excepciones import ProxyNoConfigurado

# Facades de servicios de terceros a los que un modulo puede salir --
# agrupadas en un solo archivo porque las 3 comparten el mismo criterio de
# diseño (proveedor elegido por llamada, nunca uno global fijo) y ninguna
# por separado justifica su propio archivo.


class ProxyFacade:
    """Expuesto como contexto.proxy -- unico punto de salida a internet via
    DataImpulse para un modulo que lo necesite (ver 'Proxies salientes via
    DataImpulse (plan)' en CLAUDE.md). El permiso se chequea al usarlo, no
    al leer el atributo -- listar contexto.proxy nunca falla por si solo."""

    def __init__(self, contexto: "ContextoModulo"):
        self._contexto = contexto

    def url(self) -> str:
        self._contexto._requiere("proxy.usar")
        try:
            return proxy.obtener_proxy_url()
        except KeyError as exc:
            raise ProxyNoConfigurado(
                "DATAIMPULSE_PROXY_URL no esta configurado en .env"
            ) from exc

    def httpx(self) -> dict:
        self.url()
        return proxy.proxies_httpx()


class CaptchaFacade:
    """Expuesto como contexto.captcha -- interfaz unica sobre 2Captcha,
    CapSolver y Anti-Captcha (los 3 comparten el patron createTask ->
    getTaskResult). Un modulo elige el proveedor por llamada -- puede usar
    uno solo o los 3 a la vez, no hay un proveedor global fijo."""

    def __init__(self, contexto: "ContextoModulo"):
        self._contexto = contexto

    def proveedores_disponibles(self) -> list[str]:
        return captcha.proveedores_disponibles()

    async def balance(self, proveedor: str) -> float:
        self._contexto._requiere("captcha.resolver")
        return await captcha.balance(proveedor, proxies=self._contexto.proxy.httpx())

    async def resolver_recaptcha_v2(self, proveedor: str, sitekey: str, url: str) -> str:
        self._contexto._requiere("captcha.resolver")
        return await captcha.resolver_recaptcha_v2(
            proveedor, sitekey, url, proxies=self._contexto.proxy.httpx()
        )

    async def resolver_imagen(self, proveedor: str, imagen_base64: str) -> str:
        self._contexto._requiere("captcha.resolver")
        return await captcha.resolver_imagen(
            proveedor, imagen_base64, proxies=self._contexto.proxy.httpx()
        )

    async def resolver_turnstile(self, proveedor: str, sitekey: str, url: str) -> str:
        self._contexto._requiere("captcha.resolver")
        return await captcha.resolver_turnstile(
            proveedor, sitekey, url, proxies=self._contexto.proxy.httpx()
        )


class SmsFacade:
    """Expuesto como contexto.sms -- interfaz sobre HeroSMS y SMSPool.
    Mismo criterio que CaptchaFacade: proveedor por llamada, no global."""

    def __init__(self, contexto: "ContextoModulo"):
        self._contexto = contexto

    def proveedores_disponibles(self) -> list[str]:
        return smsvirtual.proveedores_disponibles()

    async def balance(self, proveedor: str) -> str:
        self._contexto._requiere("sms.usar")
        return await smsvirtual.balance(proveedor, proxies=self._contexto.proxy.httpx())


__all__ = ["ProxyFacade", "CaptchaFacade", "SmsFacade"]
