from __future__ import annotations

import os

from telegram import ChatPermissions
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..modules import grupos as grupos_mod

# Acciones reales de Mictlantecuhtli sobre los grupos gestionados.
# "Restringir" usa set_chat_permissions (nadie puede escribir mientras
# dura) -- reversible, no destructivo: a diferencia de moderacion.py
# (baneo/expulsion de un usuario puntual), esto nunca banea ni expulsa a
# nadie, solo pausa la actividad del chat completo mientras el bot
# principal esta caido.


async def avisar(context: ContextTypes.DEFAULT_TYPE, texto: str) -> None:
    try:
        admin_group_id = int(os.environ["ADMIN_GROUP_ID"])
    except (KeyError, ValueError):
        return
    try:
        await context.bot.send_message(chat_id=admin_group_id, text=texto)
    except TelegramError:
        pass


async def restringir_todos_los_grupos(context: ContextTypes.DEFAULT_TYPE) -> dict:
    grupos = await grupos_mod.listar()
    ok = 0
    fallidos = 0
    for g in grupos:
        try:
            await context.bot.set_chat_permissions(
                chat_id=g["chat_id"], permissions=ChatPermissions(can_send_messages=False)
            )
            ok += 1
        except TelegramError:
            fallidos += 1
    return {"ok": ok, "fallidos": fallidos, "total": len(grupos)}


async def liberar_todos_los_grupos(context: ContextTypes.DEFAULT_TYPE) -> dict:
    grupos = await grupos_mod.listar()
    ok = 0
    fallidos = 0
    for g in grupos:
        try:
            await context.bot.set_chat_permissions(
                chat_id=g["chat_id"], permissions=ChatPermissions(can_send_messages=True)
            )
            ok += 1
        except TelegramError:
            fallidos += 1
    return {"ok": ok, "fallidos": fallidos, "total": len(grupos)}


__all__ = ["avisar", "restringir_todos_los_grupos", "liberar_todos_los_grupos"]
