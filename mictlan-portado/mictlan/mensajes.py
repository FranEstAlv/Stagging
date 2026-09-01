from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

TIEMPO_AUTOBORRADO_SEG = 1800
CERRAR_CALLBACK = "svc:cerrar"


def agregar_boton_cerrar(teclado: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup:
    filas = list(teclado.inline_keyboard) if teclado else []
    filas.append([InlineKeyboardButton("✖️ Cerrar", callback_data=CERRAR_CALLBACK)])
    return InlineKeyboardMarkup(filas)


async def enviar_mensaje_servicio(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    texto: str,
    *,
    teclado: InlineKeyboardMarkup | None = None,
    parse_mode: str = ParseMode.HTML,
):
    mensaje = await context.bot.send_message(
        chat_id=chat_id,
        text=texto,
        parse_mode=parse_mode,
        reply_markup=agregar_boton_cerrar(teclado),
    )
    if context.job_queue:
        context.job_queue.run_once(
            _autoborrar_job,
            TIEMPO_AUTOBORRADO_SEG,
            data={"chat_id": chat_id, "message_id": mensaje.message_id},
        )
    return mensaje


async def _autoborrar_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    datos = context.job.data
    try:
        await context.bot.delete_message(chat_id=datos["chat_id"], message_id=datos["message_id"])
    except Exception:
        pass


async def cerrar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass


def install_mensajes(app) -> None:
    app.add_handler(CallbackQueryHandler(cerrar_callback, pattern=f"^{CERRAR_CALLBACK}$"))


__all__ = ["enviar_mensaje_servicio", "install_mensajes", "agregar_boton_cerrar", "CERRAR_CALLBACK"]
