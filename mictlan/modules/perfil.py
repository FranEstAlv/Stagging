from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from .. import creditos, db, roles
from ..mensajes import enviar_mensaje_servicio


async def perfil_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    await roles.registrar_usuario(user.id, user.username)
    rol = await roles.obtener_rol(user.id)
    saldo = await creditos.saldo(user.id)

    pool = db.get_pool()
    async with pool.acquire() as conn:
        membresia = await conn.fetchrow(
            "SELECT fin, activa FROM membresias WHERE user_id = $1", user.id
        )

    if membresia and membresia["activa"] and membresia["fin"] is not None:
        # 'fin' llega como TEXT plano de SQLite (ver db.py de staging) --
        # nunca datetime, nunca .strftime() directo (mismo criterio que
        # _formatear_fecha() en modules/mando/usuarios.py).
        estado_membresia = f"activa hasta {membresia['fin'][:10]}"
    else:
        estado_membresia = "sin membresía activa"

    texto = (
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Rol: {roles.emoji_rol(rol)}\n"
        f"📅 Membresía: {estado_membresia}\n"
        f"💰 Saldo: {saldo} créditos"
    )
    await enviar_mensaje_servicio(context, message.chat_id, texto)


def install_perfil(app) -> None:
    app.add_handler(CommandHandler("perfil", perfil_command))


__all__ = ["install_perfil"]
