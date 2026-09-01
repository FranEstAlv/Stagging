from __future__ import annotations

import os

from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType, ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from ... import roles
from ...mensajes import agregar_boton_cerrar, enviar_mensaje_servicio
from . import grupos, mantenimiento, modulos, usuarios

# Consola /mando dividida en sub-paquete apenas sumo una segunda seccion
# real (Modulos) ademas de Usuarios -- ver "Modularidad: nunca un core.py"
# en CLAUDE.md. Cada seccion vive en su propio archivo (usuarios.py,
# modulos.py, grupos.py) y expone su propio callback_data namespace bajo
# "mando:"; este __init__.py solo hace de gate de permiso + router, nunca
# logica de negocio propia.

CB_MENU = "mando:menu"

TEXTO_MENU = "🛠 <b>Consola Mictlan</b>"


def _chat_permitido(chat: Chat | None) -> bool:
    if chat is None:
        return False
    if chat.type == ChatType.PRIVATE:
        return True
    return chat.id == int(os.environ["ADMIN_GROUP_ID"])


def _teclado_menu_base() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👥 Usuarios", callback_data=usuarios.CB_USUARIOS)],
            [InlineKeyboardButton("🧩 Módulos", callback_data=modulos.CB_MODULOS)],
            [InlineKeyboardButton("🏘 Grupos", callback_data=grupos.CB_GRUPOS)],
            [InlineKeyboardButton("🛠 Mantenimiento", callback_data=mantenimiento.CB_MANTENIMIENTO)],
        ]
    )


async def _editar_seguro(query, texto: str, teclado: InlineKeyboardMarkup) -> None:
    try:
        await query.edit_message_text(texto, parse_mode=ParseMode.HTML, reply_markup=teclado)
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise
        await query.answer("Sin cambios ⏸")


async def mando_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat
    if not user or not message:
        return
    if not _chat_permitido(chat):
        return
    rol = await roles.obtener_rol(user.id)
    if not roles.alcanza_rol(rol, roles.ROLE_ROOT):
        return
    await enviar_mensaje_servicio(context, message.chat_id, TEXTO_MENU, teclado=_teclado_menu_base())


async def mando_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    chat = update.effective_chat
    if not query or not user:
        return
    if not _chat_permitido(chat):
        return
    rol = await roles.obtener_rol(user.id)
    if not roles.alcanza_rol(rol, roles.ROLE_ROOT):
        await query.answer()
        return
    await query.answer()

    data = query.data or ""
    if data == CB_MENU:
        await _editar_seguro(query, TEXTO_MENU, agregar_boton_cerrar(_teclado_menu_base()))
        return

    # Namespace por seccion: "mando:usuarios:<...>", "mando:mod:<...>",
    # "mando:grp:<...>", "mando:mnt:<...>" (variable, formato propio de
    # cada seccion) -- cada una parsea lo suyo, este router solo mira el
    # segundo segmento.
    partes = data.split(":")
    seccion = partes[1] if len(partes) > 1 else None

    if seccion == "usuarios":
        texto, teclado = await usuarios.manejar(context, partes[2:])
        await _editar_seguro(query, texto, teclado)
        return

    if seccion == "mod":
        texto, teclado = await modulos.manejar(context.application, partes[2:])
        await _editar_seguro(query, texto, teclado)
        return

    if seccion == "grp":
        texto, teclado = await grupos.manejar(context, user.id, partes[2:])
        await _editar_seguro(query, texto, teclado)
        return

    if seccion == "mnt":
        texto, teclado = await mantenimiento.manejar(user.id, partes[2:])
        await _editar_seguro(query, texto, teclado)
        return


def install_mando(app) -> None:
    app.add_handler(CommandHandler("mando", mando_command))
    app.add_handler(CallbackQueryHandler(mando_callback, pattern=r"^mando:"))


__all__ = ["install_mando"]
