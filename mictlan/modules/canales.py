from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from .. import invitaciones, membresias
from ..mensajes import agregar_boton_cerrar, enviar_mensaje_servicio
from . import grupos as grupos_mod

# Comando /canales: cualquier miembro con membresia ACTIVA, usado DENTRO
# del grupo principal, se autogenera un link de invitacion de un solo uso
# a un grupo/canal SECUNDARIO -- nunca al principal (ese link solo lo
# genera root desde /mando, ver modules/mando/grupos.py). Confirmado
# explicitamente por Fernando (2026-09-01): el panel de /mando administra
# EXCLUSIVAMENTE el link del grupo principal; este comando cubre los
# secundarios, self-service, sin pasar por un admin.
#
# Espejo del caso "/scrapper" de ALFA-1 (miembro activo se autogenera un
# link a un canal secundario) -- reescrito de cero, sin el listener de
# auto-revocacion/rotacion que tiene ALFA-1 (decision explicita: solo el
# panel de generar, ver mictlan/invitaciones.py).

CB_CANALES = "canales"


def _cb(*partes) -> str:
    return ":".join((CB_CANALES, *(str(p) for p in partes)))


async def _es_miembro_activo(user_id: int) -> bool:
    membresia = await membresias.obtener(user_id)
    return bool(membresia and membresia["activa"])


async def _vista_lista(nota: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    principal = await grupos_mod.obtener_principal()
    secundarios = [
        g
        for g in await grupos_mod.listar(solo_activos=True)
        if not principal or g["chat_id"] != principal["chat_id"]
    ]

    lineas = ["🔗 <b>Canales</b>"]
    if nota:
        lineas.append("")
        lineas.append(nota)
    lineas.append("")
    if not secundarios:
        lineas.append("(sin grupos/canales secundarios activos todavía)")
    else:
        lineas.append("Elegí a dónde querés tu link de invitación (un solo uso):")
    texto = "\n".join(lineas)

    filas = [
        [InlineKeyboardButton(html.escape(g["nombre"] or str(g["chat_id"])), callback_data=_cb("link", g["chat_id"]))]
        for g in secundarios
    ]
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def _editar_seguro(query, texto: str, teclado: InlineKeyboardMarkup) -> None:
    try:
        await query.edit_message_text(texto, parse_mode=ParseMode.HTML, reply_markup=teclado)
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise
        await query.answer("Sin cambios ⏸")


async def canales_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat
    if not user or not message or not chat:
        return

    principal = await grupos_mod.obtener_principal()
    if principal is None or chat.id != principal["chat_id"]:
        return  # solo responde dentro del grupo principal -- silencio en cualquier otro chat

    if not await _es_miembro_activo(user.id):
        await enviar_mensaje_servicio(context, message.chat_id, "⚠️ Necesitás una membresía activa para esto.")
        return

    texto, teclado = await _vista_lista()
    await enviar_mensaje_servicio(context, message.chat_id, texto, teclado=teclado)


async def canales_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    if not await _es_miembro_activo(user.id):
        await query.answer("Necesitás una membresía activa.", show_alert=True)
        return
    await query.answer()

    partes = (query.data or "").split(":")
    if len(partes) < 3 or partes[1] != "link" or not partes[2].lstrip("-").isdigit():
        return
    chat_id = int(partes[2])

    principal = await grupos_mod.obtener_principal()
    if principal and chat_id == principal["chat_id"]:
        return  # nunca genera el link del principal desde aca

    try:
        link = await invitaciones.generar_link(context, chat_id, user.id)
    except TelegramError as exc:
        texto, teclado = await _vista_lista(f"⚠️ No se pudo generar el link: {exc}")
        await _editar_seguro(query, texto, teclado)
        return

    texto, teclado = await _vista_lista(f"🔗 Tu link (un solo uso): {link}")
    await _editar_seguro(query, texto, teclado)


def install_canales(app) -> None:
    app.add_handler(CommandHandler("canales", canales_command))
    app.add_handler(CallbackQueryHandler(canales_callback, pattern=rf"^{CB_CANALES}:"))


__all__ = ["install_canales"]
