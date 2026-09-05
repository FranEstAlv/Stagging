from __future__ import annotations

from telegram import Update
from telegram.ext import ChatMemberHandler, ContextTypes

from .. import db, logs_canal

# Deteccion automatica de grupos/canales -- se dispara con my_chat_member,
# el evento real de alta del bot en un chat (lo agregan, lo hacen admin,
# etc). Decision ya tomada (ver "Grupos dinamicos (plan)" en CLAUDE.md,
# quedaba como decision abierta entre esto y deteccion pasiva por mensaje
# -- Fernando confirmo el flujo "agrego el bot con permisos de admin y
# automaticamente se registra", que es exactamente este evento).
#
# Siempre queda inactivo (activo=0) hasta que un admin/root lo prenda a
# proposito -- que cualquiera meta al bot a un chat no le da poderes ahi.


async def _my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    resultado = update.my_chat_member
    if not resultado:
        return
    chat = resultado.chat
    nuevo_estado = resultado.new_chat_member.status
    if nuevo_estado not in ("member", "administrator"):
        return  # lo sacaron o quedo restringido -- no es una alta

    pool = db.get_pool()
    async with pool.acquire() as conn:
        existente = await conn.fetchrow("SELECT chat_id FROM grupos WHERE chat_id = $1", chat.id)
        if existente is not None:
            return
        await conn.execute(
            "INSERT INTO grupos (chat_id, nombre, tipo, activo) VALUES ($1, $2, $3, $4)",
            chat.id,
            chat.title or chat.username or str(chat.id),
            chat.type,
            False,
        )
    await logs_canal.enviar_log(
        context,
        f"➕ <b>GRUPO NUEVO DETECTADO</b>\nChat: <code>{chat.id}</code>\n"
        f"Nombre: {chat.title or chat.username or chat.id}\nTipo: {chat.type} — queda inactivo hasta que un admin lo active.",
    )


async def listar(solo_activos: bool = False) -> list[dict]:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        if solo_activos:
            filas = await conn.fetch("SELECT * FROM grupos WHERE activo = $1 ORDER BY agregado_en DESC", True)
        else:
            filas = await conn.fetch("SELECT * FROM grupos ORDER BY agregado_en DESC")
    return [dict(f) for f in filas]


async def activar(chat_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE grupos SET activo = $1 WHERE chat_id = $2", True, chat_id)


async def desactivar(chat_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE grupos SET activo = $1 WHERE chat_id = $2", False, chat_id)


async def establecer_principal(chat_id: int) -> None:
    """Marca chat_id como EL grupo principal -- nunca hay mas de uno a la
    vez, asi que primero se limpia cualquier otro que lo fuera. El grupo
    principal es el unico para el que /mando genera un link de invitacion
    (ver modules/mando/grupos.py) y el unico donde funciona el comando
    /canales (ver modules/canales.py)."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE grupos SET principal = $1 WHERE principal = $2", False, True)
        await conn.execute("UPDATE grupos SET principal = $1 WHERE chat_id = $2", True, chat_id)


async def obtener_principal() -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow("SELECT * FROM grupos WHERE principal = $1", True)
    return dict(fila) if fila else None


async def obtener(chat_id: int) -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow("SELECT * FROM grupos WHERE chat_id = $1", chat_id)
    return dict(fila) if fila else None


_MODOS_INGRESO_VALIDOS = {"ninguno", "captcha", "aprobacion"}


async def establecer_modo_ingreso(chat_id: int, modo: str) -> None:
    """Elige, POR GRUPO, cual de los dos gates de nuevo miembro se aplica --
    el captcha de aritmetica (mictlan/bienvenida.py) o la aprobacion manual
    de un admin/vendedor (mictlan/ingreso_admin.py) -- nunca ambos a la vez
    para el mismo chat. 'ninguno' deja el grupo sin gate, mismo default que
    cualquier grupo recien detectado."""
    if modo not in _MODOS_INGRESO_VALIDOS:
        raise ValueError(f"modo_ingreso invalido: {modo!r}")
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE grupos SET modo_ingreso = $1 WHERE chat_id = $2", modo, chat_id)


def install_grupos(app) -> None:
    app.add_handler(ChatMemberHandler(_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))


__all__ = [
    "install_grupos",
    "listar",
    "activar",
    "desactivar",
    "establecer_principal",
    "obtener_principal",
    "obtener",
    "establecer_modo_ingreso",
]
