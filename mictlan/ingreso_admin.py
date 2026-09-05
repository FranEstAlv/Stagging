from __future__ import annotations

import os

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import CallbackQueryHandler, ChatMemberHandler, ContextTypes

from . import db, roles
from .modules import grupos as grupos_mod

# Ingreso por aprobacion de administrador -- espejo del mecanismo real de
# ALFA-1 (samaritan/core.py: send_welcome_message + pending_new_members +
# activate_button_handler + auto_expel_unapproved_member), reescrito de
# cero con las convenciones de Mictlan -- ver la regla prohibitiva de
# espejo en CLAUDE.md. Confirmado explicitamente por Fernando: "es el
# mismo diseno de alfa1 ... lo unico que cambia es que alfa1 manda el
# boton de aceptar miembro al grupo privado y mictlan lo hara al grupo
# admin". Todo lo demas se mantiene igual que el original:
#   - Nuevo miembro queda silenciado (can_send_messages=False) al entrar.
#   - Boton unico "Aceptar" (ALFA-1 tampoco tiene un boton de rechazo
#     explicito -- el rechazo es siempre por vencimiento del plazo).
#   - Ventana de 1 minuto exacta (CAPTCHA_BIENVENIDA_TIMEOUT_SEGUNDOS de
#     bienvenida.py es un concepto DISTINTO, no se reusa aca).
#   - Si nadie acepta a tiempo: BAN real, sin unban -- a diferencia del
#     captcha normal (bienvenida.py), que si des-banea (kick, no ban). Es
#     el mismo comportamiento real de auto_expel_unapproved_member en
#     ALFA-1 (ban_chat_member sin unban posterior).
#   - Solo se les exige aprobacion a miembros nuevos que no sean ya
#     administrador/root (mismo criterio que bienvenida.py) -- ALFA-1 no
#     tiene ese concepto de rol propio, exime por acceso admin nativo de
#     Telegram; Mictlan lo hace por rol interno.
# Alternativa a mictlan/bienvenida.py (modo 'captcha'): un grupo usa UNA
# sola de las dos segun grupos.modo_ingreso, elegido desde /mando > Grupos.
#
# El link de invitacion de un solo uso que menciona el diseno original ya
# existe en Mictlan (mictlan/invitaciones.py, generado desde /mando >
# Grupos) -- no se duplica aca. ALFA-1 tampoco ata ese link a un usuario
# puntual: aplica este gate a CUALQUIER ingreso nuevo del grupo, venga o
# no por un link rastreado, y este modulo hace exactamente lo mismo.

_ESTADOS_MIEMBRO = {"creator", "administrator", "member"}
CB_PREFIJO = "ingreso"
_JOB_PREFIJO = "ingreso_expira"
TIMEOUT_SEGUNDOS = 60  # 1 minuto, igual que auto_expel_unapproved_member de ALFA-1

_PERMISOS_COMPLETOS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
    can_invite_users=True,
)


def _admin_group_id() -> int:
    return int(os.environ["ADMIN_GROUP_ID"])


def _job_name(chat_id: int, user_id: int) -> str:
    return f"{_JOB_PREFIJO}:{chat_id}:{user_id}"


def _texto_pendiente(nombre: str, user_id: int, chat_nombre: str) -> str:
    return (
        f"📥 <b>Nuevo ingreso pendiente de aprobación</b>\n\n"
        f"Usuario: {nombre} (<code>{user_id}</code>)\n"
        f"Grupo: {chat_nombre}\n\n"
        f"⏳ Si ningún admin/vendedor lo acepta en 1 minuto, será expulsado automáticamente."
    )


def _teclado(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Aceptar", callback_data=f"{CB_PREFIJO}:{chat_id}:{user_id}")]]
    )


async def _obtener_pendiente(chat_id: int, user_id: int) -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT * FROM pendientes_ingreso WHERE chat_id = $1 AND user_id = $2 AND aprobado = $3",
            chat_id,
            user_id,
            False,
        )
    return dict(fila) if fila else None


def _cancelar_job(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> None:
    if not context.job_queue:
        return
    for job in context.job_queue.get_jobs_by_name(_job_name(chat_id, user_id)):
        job.schedule_removal()


async def _nuevo_miembro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resultado = update.chat_member
    if not resultado:
        return
    grupo = await grupos_mod.obtener(resultado.chat.id)
    if not grupo or grupo["modo_ingreso"] != "aprobacion":
        return
    era_miembro = resultado.old_chat_member.status in _ESTADOS_MIEMBRO
    es_miembro = resultado.new_chat_member.status in _ESTADOS_MIEMBRO
    if era_miembro or not es_miembro:
        return

    usuario = resultado.new_chat_member.user
    if usuario.is_bot:
        return
    rol = await roles.obtener_rol(usuario.id)
    if roles.alcanza_rol(rol, roles.ROLE_ADMIN):
        return  # staff de confianza -- no se le exige aprobacion

    chat_id = resultado.chat.id
    if await _obtener_pendiente(chat_id, usuario.id) is not None:
        return  # ya esta pendiente -- Telegram puede duplicar el evento de ingreso

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id, user_id=usuario.id, permissions=ChatPermissions(can_send_messages=False)
        )
    except TelegramError:
        return  # sin permiso de restringir en este chat -- no dejar un pendiente sin poder actuar

    nombre = f"@{usuario.username}" if usuario.username else (usuario.first_name or str(usuario.id))
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO pendientes_ingreso (chat_id, user_id, username, aprobado)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET
                username = excluded.username,
                creado_en = now(),
                aprobado = excluded.aprobado
            """,
            chat_id,
            usuario.id,
            usuario.username,
            False,
        )

    mensaje = await context.bot.send_message(
        chat_id=_admin_group_id(),
        text=_texto_pendiente(nombre, usuario.id, resultado.chat.title or str(chat_id)),
        parse_mode="HTML",
        reply_markup=_teclado(chat_id, usuario.id),
    )

    if context.job_queue:
        _cancelar_job(context, chat_id, usuario.id)
        context.job_queue.run_once(
            _expirar_pendiente,
            TIMEOUT_SEGUNDOS,
            name=_job_name(chat_id, usuario.id),
            data={"chat_id": chat_id, "user_id": usuario.id, "message_id": mensaje.message_id},
        )


async def _expirar_pendiente(context: ContextTypes.DEFAULT_TYPE) -> None:
    datos = context.job.data
    chat_id, user_id, message_id = datos["chat_id"], datos["user_id"], datos["message_id"]
    pendiente = await _obtener_pendiente(chat_id, user_id)
    if pendiente is None:
        return  # ya fue aceptado antes de que corriera el job

    resultado = "expulsado"
    try:
        # Ban real, SIN unban -- a diferencia del kick de bienvenida.py, es
        # el mismo comportamiento de auto_expel_unapproved_member en ALFA-1.
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
    except TelegramError as exc:
        resultado = f"error: {exc}"[:200]

    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM pendientes_ingreso WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
        await conn.execute(
            """
            INSERT INTO expulsiones (user_id, chat_id, tipo, motivo, admin_id, resultado)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            chat_id,
            "ingreso_no_aprobado",
            None,
            None,
            resultado,
        )
    try:
        await context.bot.edit_message_text(
            chat_id=_admin_group_id(),
            message_id=message_id,
            text=f"⛔ <code>{user_id}</code> expulsado — nadie lo aceptó en 1 minuto.",
            parse_mode="HTML",
        )
    except TelegramError:
        pass


async def _callback_aceptar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not user:
        return
    rol = await roles.obtener_rol(user.id)
    if not roles.alcanza_rol(rol, roles.ROLE_SELLER):  # mismo piso que "administrador o seller" en ALFA-1
        await query.answer()
        return

    _, chat_id_str, user_id_str = query.data.split(":", 2)
    chat_id, target_id = int(chat_id_str), int(user_id_str)

    pendiente = await _obtener_pendiente(chat_id, target_id)
    if pendiente is None:
        await query.answer("Ya no está pendiente (aceptado o expulsado antes).", show_alert=True)
        return

    _cancelar_job(context, chat_id, target_id)
    try:
        await context.bot.restrict_chat_member(chat_id=chat_id, user_id=target_id, permissions=_PERMISOS_COMPLETOS)
    except TelegramError:
        pass

    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE pendientes_ingreso SET aprobado = $1 WHERE chat_id = $2 AND user_id = $3",
            True,
            chat_id,
            target_id,
        )

    await query.answer("Aceptado.", show_alert=True)
    try:
        nombre_admin = f"@{user.username}" if user.username else str(user.id)
        await query.message.edit_text(f"✅ <code>{target_id}</code> aceptado por {nombre_admin}.", parse_mode="HTML")
    except TelegramError:
        pass


def install_ingreso_admin(app) -> None:
    # group=2: distinto de moderacion.py (0) y bienvenida.py (1) -- los tres
    # escuchan ChatMemberHandler.CHAT_MEMBER, PTB solo corre el primero que
    # matchea DENTRO de un mismo grupo, asi que necesitan grupos separados
    # para que los tres se evaluen siempre (cada uno filtra por su propio
    # criterio -- blacklist, modo_ingreso='captcha', modo_ingreso='aprobacion').
    app.add_handler(ChatMemberHandler(_nuevo_miembro, ChatMemberHandler.CHAT_MEMBER), group=2)
    app.add_handler(CallbackQueryHandler(_callback_aceptar, pattern=f"^{CB_PREFIJO}:"))


__all__ = ["install_ingreso_admin"]
