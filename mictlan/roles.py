from __future__ import annotations

from . import db

ROLE_MEMBER = "miembro"
ROLE_SELLER = "vendedor"
ROLE_ADMIN = "administrador"
ROLE_ROOT = "root"

_ROLE_ORDER = {
    ROLE_MEMBER: 0,
    ROLE_SELLER: 1,
    ROLE_ADMIN: 2,
    ROLE_ROOT: 3,
}

# Unico lugar que traduce un rol a algo VISIBLE para el usuario -- nunca
# el nombre del rol como texto plano en ningun mensaje o boton (regla de
# Fernando, 2026-09-01: ningun panel/menu revela "root"/"administrador"/
# "vendedor" explicitamente, ni siquiera en /mando o /perfil, mismo
# espiritu que la regla fija de "cero superadmin" de mas arriba, llevada
# a cualquier nombre de rol, no solo ese). Cualquier texto que antes
# interpolara {rol} directo debe usar emoji_rol(rol) en su lugar.
EMOJI_ROL = {
    ROLE_MEMBER: "👤",
    ROLE_SELLER: "💼",
    ROLE_ADMIN: "🛠",
    ROLE_ROOT: "👑",
}


def emoji_rol(rol: str) -> str:
    return EMOJI_ROL.get(rol, "❔")


async def registrar_usuario(user_id: int, username: str | None) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO usuarios (user_id, username) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET
                username = excluded.username,
                actualizado_en = now()
            """,
            user_id,
            username,
        )


async def obtener_rol(user_id: int) -> str:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT rol FROM usuarios WHERE user_id = $1", user_id)
    return row["rol"] if row else ROLE_MEMBER


def alcanza_rol(rol: str, minimo: str) -> bool:
    return _ROLE_ORDER.get(rol, 0) >= _ROLE_ORDER.get(minimo, 0)


async def establecer_rol(user_id: int, rol: str) -> None:
    if rol not in _ROLE_ORDER:
        raise ValueError(f"rol invalido: {rol!r}")
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE usuarios SET rol = $1, actualizado_en = now() WHERE user_id = $2",
            rol,
            user_id,
        )


async def asegurar_root(user_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO usuarios (user_id, rol) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET rol = $2
            """,
            user_id,
            ROLE_ROOT,
        )
