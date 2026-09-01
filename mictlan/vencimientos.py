from __future__ import annotations

from telegram.ext import ContextTypes

from . import membresias, moderacion

# Expulsion automatica por membresia vencida -- espejo del concepto de
# ALFA-1 (samaritan/core.py, auto_expel_expired_users, job periodico cada
# 1 hora), reescrito de cero. A diferencia de "banear" (mictlan/moderacion.py),
# esto es EXCLUSIVAMENTE por tiempo: sin motivo, sin entrada en blacklist,
# nunca bloquea reingreso -- si el usuario paga de nuevo y un admin le
# suma dias, puede volver a entrar como cualquier otro. Usa el mismo
# expulsar_de_todos_los_grupos() que el baneo (tipo='membresia_vencida'
# en vez de 'baneo' en la tabla expulsiones), confirmado explicitamente
# por Fernando: "cuando la membresia vence se debe retirar al miembro de
# todo el ecosistema" -- todos los grupos/canales gestionados, no solo el
# principal.

INTERVALO_SEGUNDOS = 3600  # cada hora, mismo ritmo que auto_expel_expired_users de ALFA-1


async def _chequeo_periodico(context: ContextTypes.DEFAULT_TYPE) -> None:
    vencidos = await membresias.vencidas()
    for v in vencidos:
        await moderacion.expulsar_de_todos_los_grupos(context, v["user_id"], tipo="membresia_vencida")
        await membresias.desactivar(v["user_id"])


def install_vencimientos(app) -> None:
    app.job_queue.run_repeating(_chequeo_periodico, interval=INTERVALO_SEGUNDOS, first=10)


__all__ = ["install_vencimientos", "INTERVALO_SEGUNDOS"]
