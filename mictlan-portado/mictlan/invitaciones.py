from __future__ import annotations

from telegram.ext import ContextTypes

from . import db

# Links de invitacion de un solo uso. member_limit=1 ya le basta a
# Telegram para invalidar el link despues del primer ingreso, asi que
# este modulo no necesita un listener de chat_member ni revocar/rotar
# nada a mano -- decision explicita de Fernando de mantener solo el panel
# de generar/actualizar, sin deteccion automatica de uso.
#
# Dos flujos distintos generan links via este modulo:
# - mictlan/modules/mando/grupos.py: root, solo para el grupo principal.
# - mictlan/modules/canales.py: comando /canales, miembro con membresia
#   activa, solo para grupos/canales secundarios.


async def generar_link(context: ContextTypes.DEFAULT_TYPE, chat_id: int, creado_por: int) -> str:
    """Requiere que el bot sea administrador del chat con permiso de
    invitar -- si no, TelegramError (dejado propagar, el llamador decide
    como mostrarlo)."""
    enlace = await context.bot.create_chat_invite_link(chat_id=chat_id, member_limit=1)
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO invitaciones (chat_id, invite_link, creado_por) VALUES ($1, $2, $3)",
            chat_id,
            enlace.invite_link,
            creado_por,
        )
    return enlace.invite_link


async def ultimo_link(chat_id: int) -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT invite_link, creado_por, creado_en FROM invitaciones WHERE chat_id = $1 ORDER BY id DESC LIMIT 1",
            chat_id,
        )
    return dict(fila) if fila else None


__all__ = ["generar_link", "ultimo_link"]
