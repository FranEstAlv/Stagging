from __future__ import annotations

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ChatMemberHandler, ContextTypes

from . import db
from .modules import grupos as grupos_mod

# Baneo + lista negra. "Banear" acá significa EXCLUSIVAMENTE expulsar
# (kick) de todos los grupos/canales gestionados (tabla grupos) + guardar
# un reporte (motivo + foto) para que un admin sepa por que no debe volver
# a aceptar a ese usuario -- nunca se confunde con la futura expulsion
# automatica por membresia vencida (esa es solo por tiempo, sin motivo,
# sin blacklist).

_ESTADOS_MIEMBRO = {"creator", "administrator", "member"}


async def expulsar_de_todos_los_grupos(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    *,
    tipo: str,
    motivo: str | None = None,
    admin_id: int | None = None,
) -> dict:
    """Expulsa a user_id de cada grupo/canal registrado en la tabla
    'grupos' (todos los que el bot conoce, sin filtrar por 'activo' --
    ese flag solo gatea paneles de administracion, no si el bot es admin
    de verdad ahi; si el bot no tiene permiso en alguno, esa fila queda
    con el error real en 'expulsiones', no rompe el resto). Registra un
    resultado por grupo, insert-only, igual que creditos_ledger."""
    grupos = await grupos_mod.listar()
    pool = db.get_pool()
    ok = 0
    fallidos = 0
    for g in grupos:
        chat_id = g["chat_id"]
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            resultado = "expulsado"
            ok += 1
        except TelegramError as exc:
            resultado = f"error: {exc}"[:200]
            fallidos += 1
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO expulsiones (user_id, chat_id, tipo, motivo, admin_id, resultado)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id,
                chat_id,
                tipo,
                motivo,
                admin_id,
                resultado,
            )
    return {"ok": ok, "fallidos": fallidos, "total": len(grupos)}


async def reingresar_a_todos_los_grupos(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict:
    """Levanta el ban de Telegram en cada grupo gestionado -- usado al
    desbanear. unban_chat_member NO reagrega al usuario solo, solo permite
    que vuelva a entrar si alguien lo invita o el link sigue vigente."""
    grupos = await grupos_mod.listar()
    ok = 0
    fallidos = 0
    for g in grupos:
        try:
            await context.bot.unban_chat_member(chat_id=g["chat_id"], user_id=user_id, only_if_banned=True)
            ok += 1
        except TelegramError:
            fallidos += 1
    return {"ok": ok, "fallidos": fallidos, "total": len(grupos)}


async def esta_en_blacklist(user_id: int) -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT user_id, motivo, foto_file_id, admin_id, creado_en FROM blacklist WHERE user_id = $1 AND activo = $2",
            user_id,
            True,
        )
    return dict(fila) if fila else None


async def agregar_a_blacklist(user_id: int, motivo: str, foto_file_id: str, admin_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO blacklist (user_id, motivo, foto_file_id, admin_id, activo)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO UPDATE SET
                motivo = excluded.motivo,
                foto_file_id = excluded.foto_file_id,
                admin_id = excluded.admin_id,
                creado_en = now(),
                activo = excluded.activo
            """,
            user_id,
            motivo,
            foto_file_id,
            admin_id,
            True,
        )


async def quitar_de_blacklist(user_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE blacklist SET activo = $1 WHERE user_id = $2", False, user_id)


async def _reingreso_bloqueado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Guardia contra reingreso: si alguien en blacklist activa entra (o
    lo agregan) a cualquier grupo gestionado, se lo expulsa de inmediato
    ahi mismo. Distinto del ChatMemberHandler.MY_CHAT_MEMBER de
    modules/grupos.py (ese detecta altas del BOT, este detecta altas de
    un MIEMBRO cualquiera -- son campos de Update distintos)."""
    resultado = update.chat_member
    if not resultado:
        return
    era_miembro = resultado.old_chat_member.status in _ESTADOS_MIEMBRO
    es_miembro = resultado.new_chat_member.status in _ESTADOS_MIEMBRO
    if era_miembro or not es_miembro:
        return
    usuario = resultado.new_chat_member.user
    if usuario.is_bot:
        return
    entrada = await esta_en_blacklist(usuario.id)
    if entrada is None:
        return
    chat_id = resultado.chat.id
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=usuario.id)
        resultado_texto = "reingreso_bloqueado"
    except TelegramError as exc:
        resultado_texto = f"error_bloqueo_reingreso: {exc}"[:200]
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO expulsiones (user_id, chat_id, tipo, motivo, admin_id, resultado)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            usuario.id,
            chat_id,
            "baneo",
            entrada["motivo"],
            entrada["admin_id"],
            resultado_texto,
        )


def install_moderacion(app) -> None:
    app.add_handler(ChatMemberHandler(_reingreso_bloqueado, ChatMemberHandler.CHAT_MEMBER))


__all__ = [
    "expulsar_de_todos_los_grupos",
    "reingresar_a_todos_los_grupos",
    "esta_en_blacklist",
    "agregar_a_blacklist",
    "quitar_de_blacklist",
    "install_moderacion",
]
