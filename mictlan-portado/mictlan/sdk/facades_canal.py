from __future__ import annotations

from .. import canal
from .excepciones import PublicacionNoConfigurada


class CanalFacade:
    """Expuesto como contexto.canal -- publica en el/los grupo(s)/canal(es)
    configurados para ESTE modulo (tabla publicaciones_modulo), sin que el
    modulo necesite saber el chat_id de antemano. Resuelto por
    configuracion editable (chat_id, boton, plantilla, activo,
    periodicidad) por destino, no hardcodeado en el modulo.

    Un modulo puede tener varios "destinos" (etiquetas libres, ej. 'canal'
    y 'principal') -- publicar_texto/publicar_foto apuntan a uno solo
    (default 'principal'); publicar_a_todos() reparte al mismo tiempo
    entre todos los destinos activos del modulo."""

    def __init__(self, contexto: "ContextoModulo"):
        self._contexto = contexto

    async def config(self, destino: str = "principal") -> dict:
        self._contexto._requiere("canal.publicar")
        cfg = await canal.obtener_config(self._contexto.module_id, destino)
        if cfg is None:
            raise PublicacionNoConfigurada(
                f"El modulo '{self._contexto.module_id}' no tiene destino '{destino}' en publicaciones_modulo"
            )
        if not cfg["activo"]:
            raise PublicacionNoConfigurada(
                f"El destino '{destino}' de '{self._contexto.module_id}' esta desactivado"
            )
        if not cfg["chat_id"]:
            raise PublicacionNoConfigurada(
                f"El destino '{destino}' de '{self._contexto.module_id}' no tiene chat_id configurado"
            )
        return cfg

    async def destinos_activos(self) -> list[dict]:
        self._contexto._requiere("canal.publicar")
        return await canal.obtener_destinos_activos(self._contexto.module_id)

    async def plantilla(self, destino: str = "principal") -> str | None:
        cfg = await self.config(destino)
        return cfg.get("plantilla_texto")

    async def publicar_texto(
        self,
        context,
        texto: str,
        destino: str = "principal",
        botones_extra: list[tuple[str, str]] | None = None,
    ):
        cfg = await self.config(destino)
        teclado = canal.teclado(cfg["boton_texto"], cfg["boton_url"], botones_extra)
        return await context.bot.send_message(
            chat_id=cfg["chat_id"], text=texto, parse_mode="HTML", reply_markup=teclado
        )

    async def publicar_foto(
        self,
        context,
        foto,
        texto: str,
        destino: str = "principal",
        botones_extra: list[tuple[str, str]] | None = None,
    ):
        cfg = await self.config(destino)
        teclado = canal.teclado(cfg["boton_texto"], cfg["boton_url"], botones_extra)
        return await context.bot.send_photo(
            chat_id=cfg["chat_id"],
            photo=foto,
            caption=texto,
            parse_mode="HTML",
            reply_markup=teclado,
        )

    async def publicar_a_todos(
        self,
        context,
        texto: str | None = None,
        foto: str | None = None,
        botones_extra: list[tuple[str, str]] | None = None,
    ) -> dict[str, dict]:
        """Publica en TODOS los destinos activos del modulo a la vez.
        Ningun destino caido tumba a los demas -- cada uno se intenta por
        separado y el resultado se reporta individualmente.

        Devuelve {destino: {"ok": bool, "error": str | None}}."""
        self._contexto._requiere("canal.publicar")
        destinos = await canal.obtener_destinos_activos(self._contexto.module_id)
        resultados: dict[str, dict] = {}
        for cfg in destinos:
            destino = cfg["destino"]
            if not cfg["chat_id"]:
                resultados[destino] = {"ok": False, "error": "sin chat_id configurado"}
                continue
            teclado = canal.teclado(cfg["boton_texto"], cfg["boton_url"], botones_extra)
            try:
                if foto is not None:
                    await context.bot.send_photo(
                        chat_id=cfg["chat_id"],
                        photo=foto,
                        caption=texto,
                        parse_mode="HTML",
                        reply_markup=teclado,
                    )
                else:
                    await context.bot.send_message(
                        chat_id=cfg["chat_id"], text=texto, parse_mode="HTML", reply_markup=teclado
                    )
                resultados[destino] = {"ok": True, "error": None}
            except Exception as exc:
                resultados[destino] = {"ok": False, "error": str(exc)}
        return resultados

    # -- Administracion del propio modulo (para paneles de configuracion) --
    # A diferencia de config()/publicar_*, estos metodos NUNCA levantan
    # PublicacionNoConfigurada por estar inactivo/incompleto -- un panel
    # necesita poder MOSTRAR y EDITAR un destino apagado, no solo usarlo.
    # Siempre operan sobre self._contexto.module_id -- un modulo no puede
    # tocar la config de otro modulo aunque lo intente.

    async def estado(self, destino: str) -> dict | None:
        self._contexto._requiere("canal.publicar")
        return await canal.obtener_config(self._contexto.module_id, destino)

    async def alternar_activo(self, destino: str) -> bool:
        """Prende/apaga el destino, devuelve el nuevo estado."""
        self._contexto._requiere("canal.publicar")
        actual = await canal.obtener_config(self._contexto.module_id, destino)
        nuevo = not bool(actual["activo"]) if actual else True
        await canal.fijar_activo(self._contexto.module_id, destino, nuevo)
        return nuevo

    async def fijar_periodicidad(self, destino: str, minutos: int) -> None:
        self._contexto._requiere("canal.publicar")
        await canal.fijar_periodicidad(self._contexto.module_id, destino, minutos)

    async def fijar_csv(self, destino: str, archivo: str, campo: str) -> None:
        self._contexto._requiere("canal.publicar")
        await canal.fijar_csv(self._contexto.module_id, destino, archivo, campo)


__all__ = ["CanalFacade"]
