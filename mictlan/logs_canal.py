from __future__ import annotations

import os

from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from . import db

# Canal de logs -- espejo del concepto de ALFA-1 (samaritan/core.py:
# send_log_event/LOG_CHANNEL_ID), reescrito de cero. Mejora deliberada:
# cada evento se persiste en logs_eventos (ver db.py) ANTES de intentar
# el envio a Telegram -- un LOGS_CHANNEL_ID mal configurado, un canal
# borrado, o un rate-limit puntual de la API nunca hace perder el
# evento, a diferencia de ALFA-1, donde send_log_event solo vive en el
# historial del chat (si ese envio falla, el evento desaparece --
# excepto los errores no manejados, que ahi si tienen su propia tabla
# aparte, runtime_errors).


def _canal_id() -> int | None:
    valor = os.environ.get("LOGS_CHANNEL_ID")
    return int(valor) if valor else None


async def enviar_log(context: ContextTypes.DEFAULT_TYPE, texto: str) -> None:
    """Nunca levanta -- un fallo de logging no puede tumbar el flujo
    principal (mismo criterio que ALFA-1). Guarda primero en DB, despues
    intenta el envio a Telegram; si LOGS_CHANNEL_ID no esta configurado,
    o el envio falla, el evento de todos modos ya quedo en logs_eventos."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO logs_eventos (texto) VALUES ($1)", texto)

    canal_id = _canal_id()
    if not canal_id:
        return
    try:
        await context.bot.send_message(chat_id=canal_id, text=texto, parse_mode=ParseMode.HTML)
    except Exception:
        pass  # ya quedo en logs_eventos -- el evento no se perdio


__all__ = ["enviar_log"]
