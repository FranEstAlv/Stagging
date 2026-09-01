from __future__ import annotations

from .. import creditos

# Archivo propio (aunque chico) para que la asimetria deliberada de este
# facade -- nunca expone otorgar() -- quede visualmente aislada y facil de
# auditar de un vistazo, sin mezclarse entre los demas facades.


class CreditosFacade:
    """Expuesto como contexto.creditos -- API de cobro para modulos
    externos. Deliberadamente asimetrica respecto a mictlan.creditos: NUNCA
    expone otorgar() (acuñar creditos nuevos), solo cobrar() (spend real,
    revalidado server-side) y reembolsar() (reverso de un cobro propio).
    Leccion directa de revisar el SDK real de ALFA-1 (ver PROGRESO.md,
    comparacion 2026-09-01) -- ahi el unico camino documentado para que un
    modulo cobrara era un atajo sin gate (bot_data['credit_service']) que
    SI dejaba acuñar creditos. Ese boquete no existe aca: el metodo
    otorgar() ni siquiera esta importado en este archivo."""

    def __init__(self, contexto: "ContextoModulo"):
        self._contexto = contexto

    async def saldo(self, user_id: int) -> int:
        self._contexto._requiere("creditos.leer_saldo")
        return await creditos.saldo(user_id)

    async def cobrar(self, user_id: int, cantidad: int, motivo: str) -> str:
        self._contexto._requiere("creditos.cobrar")
        return await creditos.cobrar(user_id, cantidad, motivo, module_id=self._contexto.module_id)

    async def reembolsar(self, tx_id: str, motivo: str = "reembolso") -> str:
        self._contexto._requiere("creditos.cobrar")
        return await creditos.reembolsar(tx_id, motivo, module_id=self._contexto.module_id)


__all__ = ["CreditosFacade"]
