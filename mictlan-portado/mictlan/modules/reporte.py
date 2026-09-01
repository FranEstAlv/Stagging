from __future__ import annotations

import html
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from .. import db, roles
from ..mensajes import agregar_boton_cerrar, enviar_mensaje_servicio

USO = "Uso: /reporte tu mensaje aquí"
CONFIRMACION = "✅ Reporte recibido, los administradores lo revisarán."


def _cb_atender(reporte_id: int) -> str:
    return f"reporte:atender:{reporte_id}"


async def reporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    texto = " ".join(context.args) if context.args else ""
    if not texto.strip():
        await enviar_mensaje_servicio(context, message.chat_id, USO)
        return

    await roles.registrar_usuario(user.id, user.username)

    pool = db.get_pool()
    async with pool.acquire() as conn:
        reporte_id = await conn.fetchval(
            "INSERT INTO reportes (user_id, texto) VALUES ($1, $2) RETURNING id",
            user.id,
            texto,
        )

    username = f"@{user.username}" if user.username else "(sin username)"
    texto_admin = (
        f"🚩 <b>Reporte #{reporte_id}</b>\n"
        f"De: <code>{user.id}</code> {html.escape(username)}\n\n"
        f"{html.escape(texto)}"
    )
    teclado = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Atendido", callback_data=_cb_atender(reporte_id))]]
    )
    await enviar_mensaje_servicio(
        context, int(os.environ["ADMIN_GROUP_ID"]), texto_admin, teclado=teclado
    )
    await enviar_mensaje_servicio(context, message.chat_id, CONFIRMACION)


async def reporte_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not user or not query.data:
        return

    rol = await roles.obtener_rol(user.id)
    if not roles.alcanza_rol(rol, roles.ROLE_ADMIN):
        await query.answer()
        return

    reporte_id = int(query.data.rsplit(":", 1)[1])

    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT atendido, texto, user_id FROM reportes WHERE id = $1", reporte_id
        )
        if fila is None:
            await query.answer()
            return
        if fila["atendido"]:
            await query.answer("Ya estaba atendido ⏸")
            return
        await conn.execute(
            "UPDATE reportes SET atendido = true, atendido_por = $1, atendido_en = now() WHERE id = $2",
            user.id,
            reporte_id,
        )

    await query.answer("Marcado como atendido ✅")
    username = f"@{user.username}" if user.username else str(user.id)
    texto_nuevo = (
        f"🚩 <b>Reporte #{reporte_id}</b>\n"
        f"De: <code>{fila['user_id']}</code>\n\n"
        f"{html.escape(fila['texto'])}\n\n"
        f"✅ Atendido por {html.escape(username)}"
    )
    teclado = agregar_boton_cerrar(None)
    try:
        await query.edit_message_text(texto_nuevo, parse_mode="HTML", reply_markup=teclado)
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


def install_reporte(app) -> None:
    app.add_handler(CommandHandler("reporte", reporte_command))
    app.add_handler(CallbackQueryHandler(reporte_callback, pattern=r"^reporte:atender:\d+$"))


__all__ = ["install_reporte"]
