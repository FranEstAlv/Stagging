from __future__ import annotations

import logging

from .. import roles
from ..mensajes import enviar_mensaje_servicio
from .excepciones import PermisoNoConcedido
from .facades_canal import CanalFacade
from .facades_creditos import CreditosFacade
from .facades_datos import DatosFacade
from .facades_externos import CaptchaFacade, ProxyFacade, SmsFacade


class ContextoModulo:
    """Superficie acotada que un modulo (interno o externo) puede usar sin
    tocar db.py/roles.py directamente. Cada metodo exige el scope
    correspondiente declarado en el manifest. Solo ensambla los facades de
    los demas archivos de sdk/ -- ninguna logica de negocio propia vive
    aca aparte de obtener_rol/registrar_usuario/enviar_mensaje_servicio
    (las 3 unicas cosas que no ameritan su propio facade)."""

    def __init__(self, module_id: str, permisos: set[str]):
        self.module_id = module_id
        self.permisos = permisos
        self.logger = logging.getLogger(f"mictlan.modulos.{module_id}")

    def _requiere(self, permiso: str) -> None:
        if permiso not in self.permisos:
            raise PermisoNoConcedido(
                f"El modulo '{self.module_id}' no tiene el permiso '{permiso}'"
            )

    async def obtener_rol(self, user_id: int) -> str:
        self._requiere("usuarios.leer_rol")
        return await roles.obtener_rol(user_id)

    async def registrar_usuario(self, user_id: int, username: str | None) -> None:
        self._requiere("usuarios.registrar")
        await roles.registrar_usuario(user_id, username)

    async def enviar_mensaje_servicio(self, context, chat_id: int, texto: str, **kwargs):
        self._requiere("mensajes.enviar")
        return await enviar_mensaje_servicio(context, chat_id, texto, **kwargs)

    @property
    def proxy(self) -> ProxyFacade:
        return ProxyFacade(self)

    @property
    def captcha(self) -> CaptchaFacade:
        return CaptchaFacade(self)

    @property
    def sms(self) -> SmsFacade:
        return SmsFacade(self)

    @property
    def creditos(self) -> CreditosFacade:
        return CreditosFacade(self)

    @property
    def datos(self) -> DatosFacade:
        return DatosFacade(self)

    @property
    def canal(self) -> CanalFacade:
        return CanalFacade(self)


__all__ = ["ContextoModulo"]
