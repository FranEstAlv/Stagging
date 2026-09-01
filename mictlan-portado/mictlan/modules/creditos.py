from __future__ import annotations

import os

import asyncpg
from telegram import Chat, Update
from telegram.constants import ChatType
from telegram.ext import CommandHandler, ContextTypes

from .. import creditos, roles
from ..mensajes import enviar_mensaje_servicio

USO = "Uso: /otorgar &lt;user_id&gt; &lt;cantidad&gt; [motivo]"

# Unico punto del bot que puede acuñar creditos (creditos.otorgar) --
# nunca expuesto a un modulo externo via contexto.creditos (ver sdk/).
# Gateado a root + mismo chat que /mando (DM o grupo de gestion) porque
# acuñar creditos es una accion mas sensible que ver el propio perfil.


def _chat_permitido(chat: Chat | None) -> bool:
    if chat is None:
        return False
    if chat.type == ChatType.PRIVATE:
        return True
    return chat.id == int(os.environ["ADMIN_GROUP_ID"])


async def otorgar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat
    if not user or not message:
        return
    if not _chat_permitido(chat):
        return
    rol = await roles.obtener_rol(user.id)
    if not roles.alcanza_rol(rol, roles.ROLE_ROOT):
        return  # silencio total, mismo patron que /mando

    args = context.args or []
    if len(args) < 2:
        await enviar_mensaje_servicio(context, message.chat_id, USO)
        return
    try:
        destino_id = int(args[0])
        cantidad = int(args[1])
    except ValueError:
        await enviar_mensaje_servicio(context, message.chat_id, USO)
        return
    if cantidad <= 0:
        await enviar_mensaje_servicio(context, message.chat_id, "La cantidad debe ser positiva.")
        return
    motivo = " ".join(args[2:]) or "otorgado manualmente desde /otorgar"

    try:
        tx_id = await creditos.otorgar(destino_id, cantidad, motivo, admin_id=user.id)
    except asyncpg.ForeignKeyViolationError:
        await enviar_mensaje_servicio(
            context,
            message.chat_id,
            f"❌ <code>{destino_id}</code> no está registrado todavía "
            "(tiene que usar /start o /perfil primero).",
        )
        return

    nuevo_saldo = await creditos.saldo(destino_id)
    await enviar_mensaje_servicio(
        context,
        message.chat_id,
        f"✅ Otorgados {cantidad} créditos a <code>{destino_id}</code>.\n"
        f"Nuevo saldo: {nuevo_saldo}\n"
        f"Motivo: {motivo}\n"
        f"<code>{tx_id}</code>",
    )


def install_creditos(app) -> None:
    app.add_handler(CommandHandler("otorgar", otorgar_command))


__all__ = ["install_creditos"]
