from __future__ import annotations

import html
import os

from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ... import moderacion, roles
from ...mensajes import agregar_boton_cerrar
from .usuarios import CB_BANEAR_PREFIJO, CB_REPORTE_PREFIJO

# Flujo de baneo (motivo + foto de evidencia) y visor del reporte -- viven
# aparte de usuarios.py porque no encajan en su contrato manejar(partes) ->
# (texto, teclado): un ConversationHandler necesita sus propios
# entry_points/states/fallbacks registrados directo en la Application, y
# 'reporte' manda una foto nueva (context.bot.send_photo), no puede
# editar el panel de texto existente. Se registran en main.py ANTES de
# install_mando(app) para que intercepten "mando:usuarios:banear:..." y
# "mando:usuarios:reporte:..." antes de que el router generico de mando
# los reciba (dentro del mismo grupo de handlers, PTB solo corre el
# primero que matchea).

MOTIVO, FOTO = range(2)


def _chat_permitido(chat: Chat | None) -> bool:
    if chat is None:
        return False
    if chat.type == ChatType.PRIVATE:
        return True
    return chat.id == int(os.environ["ADMIN_GROUP_ID"])


async def _autorizado(update: Update) -> bool:
    user = update.effective_user
    if not user or not _chat_permitido(update.effective_chat):
        return False
    rol = await roles.obtener_rol(user.id)
    return roles.alcanza_rol(rol, roles.ROLE_ROOT)


async def _iniciar_baneo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    if not await _autorizado(update):
        await query.answer()
        return ConversationHandler.END
    await query.answer()

    partes = (query.data or "").split(":")
    if len(partes) < 5 or not partes[3].isdigit():
        return ConversationHandler.END
    target_id = int(partes[3])
    pagina_origen = int(partes[4]) if partes[4].isdigit() else 0
    context.user_data["baneo"] = {"user_id": target_id, "pagina_origen": pagina_origen}

    teclado = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancelar", callback_data=f"{CB_BANEAR_PREFIJO}:cancelar")]])
    await query.edit_message_text(
        f"🚫 <b>Banear</b>\n<code>{target_id}</code>\n\nEnviá el motivo del baneo (texto).",
        parse_mode=ParseMode.HTML,
        reply_markup=teclado,
    )
    return MOTIVO


async def _recibir_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    datos = context.user_data.get("baneo")
    mensaje = update.effective_message
    if not datos or not mensaje:
        return ConversationHandler.END
    motivo = (mensaje.text or "").strip()
    if not motivo:
        await mensaje.reply_text("❌ El motivo no puede estar vacío. Enviá el motivo del baneo:")
        return MOTIVO
    datos["motivo"] = motivo
    await mensaje.reply_text("🖼 Ahora enviá la foto de evidencia:")
    return FOTO


async def _foto_invalida(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mensaje = update.effective_message
    if mensaje:
        await mensaje.reply_text("❌ Enviá una foto (no texto). O escribí 'cancelar' para abortar.")
    return FOTO


async def _recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    datos = context.user_data.get("baneo")
    mensaje = update.effective_message
    user = update.effective_user
    if not datos or not mensaje or not mensaje.photo or not user:
        return ConversationHandler.END

    foto_file_id = mensaje.photo[-1].file_id
    user_id = datos["user_id"]
    motivo = datos["motivo"]

    await moderacion.agregar_a_blacklist(user_id, motivo, foto_file_id, user.id)
    sync = await moderacion.expulsar_de_todos_los_grupos(
        context, user_id, tipo="baneo", motivo=motivo, admin_id=user.id
    )
    context.user_data.pop("baneo", None)

    aviso_fallos = f" ({sync['fallidos']} con error)" if sync["fallidos"] else ""
    await mensaje.reply_text(
        f"✅ <code>{user_id}</code> baneado y agregado a la lista negra.\n"
        f"Expulsado de {sync['ok']}/{sync['total']} grupos{aviso_fallos}.\n"
        f"Motivo: {html.escape(motivo)}",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def _cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("baneo", None)
    mensaje = update.effective_message
    if mensaje:
        await mensaje.reply_text("❎ Baneo cancelado.")
    return ConversationHandler.END


async def _cancelar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("baneo", None)
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.edit_message_text("❎ Baneo cancelado.")
        except Exception:
            pass
    return ConversationHandler.END


async def _ver_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    if not await _autorizado(update):
        await query.answer()
        return
    await query.answer()

    partes = (query.data or "").split(":")
    if len(partes) < 4 or not partes[3].isdigit():
        return
    target_id = int(partes[3])
    entrada = await moderacion.esta_en_blacklist(target_id)
    if entrada is None:
        await query.message.reply_text("⚠️ Ese usuario ya no está en la lista negra.")
        return

    caption = (
        f"📋 <b>Reporte de baneo</b>\n<code>{target_id}</code>\n\n"
        f"Motivo: {html.escape(entrada['motivo'])}\n"
        f"Admin: <code>{entrada['admin_id']}</code>\n"
        f"Fecha: {entrada['creado_en'].strftime('%Y-%m-%d')}"
    )
    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=entrada["foto_file_id"],
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=agregar_boton_cerrar(None),
    )


def install_baneo(app) -> None:
    conversacion = ConversationHandler(
        entry_points=[CallbackQueryHandler(_iniciar_baneo, pattern=rf"^{CB_BANEAR_PREFIJO}:\d+:\d+$")],
        states={
            MOTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, _recibir_motivo)],
            FOTO: [
                MessageHandler(filters.PHOTO, _recibir_foto),
                MessageHandler(filters.ALL & ~filters.COMMAND, _foto_invalida),
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", _cancelar),
            MessageHandler(filters.Regex(r"(?i)^cancelar$"), _cancelar),
            CallbackQueryHandler(_cancelar_callback, pattern=rf"^{CB_BANEAR_PREFIJO}:cancelar$"),
        ],
        conversation_timeout=300,
    )
    app.add_handler(conversacion)
    app.add_handler(CallbackQueryHandler(_ver_reporte, pattern=rf"^{CB_REPORTE_PREFIJO}:"))


__all__ = ["install_baneo"]
