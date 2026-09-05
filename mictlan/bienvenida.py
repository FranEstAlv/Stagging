from __future__ import annotations

import os
import random

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import CallbackQueryHandler, ChatMemberHandler, ContextTypes

from . import db, formato, roles
from .modules import grupos as grupos_mod

# Captcha de bienvenida -- espejo del concepto de ALFA-1
# (samaritan/services/captcha.py: silencia al usuario nuevo, le presenta
# un reto de opcion multiple, y lo expulsa si no responde a tiempo),
# reescrito de cero con las convenciones de Mictlan -- ver la regla
# prohibitiva de espejo en CLAUDE.md. Se aplica a CUALQUIER grupo con
# grupos.modo_ingreso = 'captcha' (elegido desde /mando > Grupos), no solo
# al principal -- alternativa a mictlan/ingreso_admin.py (modo
# 'aprobacion'), nunca ambos a la vez para el mismo chat. Distinto en
# varios puntos deliberados, no una copia:
#   - Reto de aritmetica generado al azar (nunca un banco de trivia fijo
#     sobre el grupo, que no existe en Mictlan).
#   - Sin contador regresivo editado en vivo -- un solo job de expiracion
#     alcanza para "auto-expulsion si no responde a tiempo", que es lo
#     pedido; el refresco periodico del mensaje es UI extra no pedida.
#   - Administrador/root queda exento (mismo criterio de "staff de
#     confianza" que ya aplica en el resto de /mando), en vez del chequeo
#     de admin nativo de Telegram por chat que usa ALFA-1 -- Mictlan no
#     tiene ese concepto, tiene roles propios.
#
# "Expulsar" aca es EXCLUSIVAMENTE un kick del grupo principal (ban
# inmediato + unban en el acto, para no bloquear un reingreso futuro) --
# distinto en todo sentido de un baneo real (mictlan/moderacion.py, con
# motivo + blacklist) y de la expulsion por membresia vencida
# (mictlan/vencimientos.py): sin motivo, sin blacklist, nunca bloquea
# reingreso. Reutiliza la tabla "expulsiones" solo como bitacora comun
# (tipo='captcha_vencido'), nunca la funcion de moderacion.py que expulsa
# de TODOS los grupos gestionados -- este kick es de un solo chat, el que
# tiene modo_ingreso='captcha'.

_ESTADOS_MIEMBRO = {"creator", "administrator", "member"}
CB_PREFIJO = "bienvenida"
_JOB_PREFIJO = "bienvenida_expira"

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


def _timeout_segundos() -> int:
    return int(os.environ.get("CAPTCHA_BIENVENIDA_TIMEOUT_SEGUNDOS", "180"))


def _job_name(chat_id: int, user_id: int) -> str:
    return f"{_JOB_PREFIJO}:{chat_id}:{user_id}"


def _generar_reto() -> tuple[str, str, list[str]]:
    a, b = random.randint(1, 20), random.randint(1, 20)
    correcta = str(a + b)
    opciones = {correcta}
    while len(opciones) < 4:
        opciones.add(str(a + b + random.randint(-10, 10)))
    lista = list(opciones)
    random.shuffle(lista)
    return f"¿Cuánto es {a} + {b}?", correcta, lista


def _teclado(user_id: int, opciones: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(o, callback_data=f"{CB_PREFIJO}:{user_id}:{o}") for o in opciones]]
    )


def _texto_reto(pregunta: str) -> str:
    minutos = _timeout_segundos() // 60
    return (
        f"👋 Bienvenido.\n\n"
        f"Para poder escribir en el grupo, resolvé:\n\n{formato.negrita(pregunta)}\n\n"
        f"⚠️ Si no respondés en {minutos} minutos, vas a ser expulsado automáticamente."
    )


async def _obtener_activo(chat_id: int, user_id: int) -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT * FROM captchas_bienvenida WHERE chat_id = $1 AND user_id = $2 AND activo = $3",
            chat_id,
            user_id,
            True,
        )
    return dict(fila) if fila else None


async def _marcar_resuelto(chat_id: int, user_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE captchas_bienvenida SET activo = $1, resuelto_en = now() WHERE chat_id = $2 AND user_id = $3",
            False,
            chat_id,
            user_id,
        )


def _cancelar_job(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> None:
    if not context.job_queue:
        return
    for job in context.job_queue.get_jobs_by_name(_job_name(chat_id, user_id)):
        job.schedule_removal()


async def _aplicar_captcha(usuario, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    if usuario.is_bot:
        return
    rol = await roles.obtener_rol(usuario.id)
    if roles.alcanza_rol(rol, roles.ROLE_ADMIN):
        return  # staff de confianza -- no se le exige captcha

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id, user_id=usuario.id, permissions=ChatPermissions(can_send_messages=False)
        )
    except TelegramError:
        return  # sin permiso de restringir en este chat -- no dejar al usuario colgado sin reto

    pregunta, correcta, opciones = _generar_reto()
    mensaje = await context.bot.send_message(
        chat_id=chat_id,
        text=_texto_reto(pregunta),
        parse_mode=ParseMode.HTML,
        reply_markup=_teclado(usuario.id, opciones),
    )

    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO captchas_bienvenida (chat_id, user_id, respuesta_correcta, message_id, activo, resuelto_en)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET
                respuesta_correcta = excluded.respuesta_correcta,
                message_id = excluded.message_id,
                activo = excluded.activo,
                creado_en = now(),
                resuelto_en = excluded.resuelto_en
            """,
            chat_id,
            usuario.id,
            correcta,
            mensaje.message_id,
            True,
            None,
        )

    if context.job_queue:
        _cancelar_job(context, chat_id, usuario.id)
        context.job_queue.run_once(
            _expirar_captcha,
            _timeout_segundos(),
            name=_job_name(chat_id, usuario.id),
            data={"chat_id": chat_id, "user_id": usuario.id, "message_id": mensaje.message_id},
        )


async def _nuevo_miembro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resultado = update.chat_member
    if not resultado:
        return
    grupo = await grupos_mod.obtener(resultado.chat.id)
    if not grupo or grupo["modo_ingreso"] != "captcha":
        return
    era_miembro = resultado.old_chat_member.status in _ESTADOS_MIEMBRO
    es_miembro = resultado.new_chat_member.status in _ESTADOS_MIEMBRO
    if era_miembro or not es_miembro:
        return
    await _aplicar_captcha(resultado.new_chat_member.user, resultado.chat.id, context)


async def _expirar_captcha(context: ContextTypes.DEFAULT_TYPE) -> None:
    datos = context.job.data
    chat_id, user_id, message_id = datos["chat_id"], datos["user_id"], datos["message_id"]
    activo = await _obtener_activo(chat_id, user_id)
    if activo is None:
        return  # ya resuelto (o cancelado) antes de que corriera el job

    resultado = "expulsado"
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
    except TelegramError as exc:
        resultado = f"error: {exc}"[:200]

    await _marcar_resuelto(chat_id, user_id)
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO expulsiones (user_id, chat_id, tipo, motivo, admin_id, resultado)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            chat_id,
            "captcha_vencido",
            None,
            None,
            resultado,
        )
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="⛔ Tiempo agotado. Fuiste expulsado por no resolver el captcha.",
        )
    except TelegramError:
        pass


async def _callback_respuesta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, objetivo_id_str, opcion = query.data.split(":", 2)
    objetivo_id = int(objetivo_id_str)
    if query.from_user.id != objetivo_id:
        await query.answer("Este captcha no es para vos.", show_alert=True)
        return

    chat_id = query.message.chat_id
    activo = await _obtener_activo(chat_id, objetivo_id)
    if activo is None:
        await query.answer("Este captcha ya no está activo.", show_alert=True)
        return

    if opcion != activo["respuesta_correcta"]:
        await query.answer("Respuesta incorrecta ❌ Seguís silenciado.", show_alert=True)
        return

    _cancelar_job(context, chat_id, objetivo_id)
    await _marcar_resuelto(chat_id, objetivo_id)
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id, user_id=objetivo_id, permissions=_PERMISOS_COMPLETOS
        )
    except TelegramError:
        pass
    await query.answer("Verificación correcta.", show_alert=True)
    try:
        await query.message.edit_text("✅ Verificación correcta. Ya podés escribir.")
    except TelegramError:
        pass


def install_bienvenida(app) -> None:
    # group=1 (nunca 0, el default de moderacion.py): dos ChatMemberHandler
    # sobre CHAT_MEMBER en el MISMO grupo compiten por el mismo update -- PTB
    # solo corre el primero que matchea dentro de un grupo. En grupos
    # distintos, ambos corren siempre, sin pisarse (verificado con una
    # Application real, ver PROGRESO.md).
    app.add_handler(ChatMemberHandler(_nuevo_miembro, ChatMemberHandler.CHAT_MEMBER), group=1)
    app.add_handler(CallbackQueryHandler(_callback_respuesta, pattern=f"^{CB_PREFIJO}:"))


__all__ = ["install_bienvenida"]
