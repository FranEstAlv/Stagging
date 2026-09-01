from __future__ import annotations

from .. import proxy
from .excepciones import ProxyNoConfigurado


class ProxyFacade:
    """Expuesto como contexto.proxy -- unico punto de salida a internet via
    DataImpulse para un modulo que lo necesite. El permiso se chequea al
    usarlo, no al leer el atributo -- listar contexto.proxy nunca falla
    por si solo."""

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


__all__ = ["ProxyFacade"]
