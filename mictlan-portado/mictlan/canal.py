from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from . import db


async def obtener_config(module_id: str, destino: str = "principal") -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT * FROM publicaciones_modulo WHERE module_id = $1 AND destino = $2",
            module_id,
            destino,
        )
    return dict(fila) if fila else None


async def obtener_destinos_activos(module_id: str) -> list[dict]:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        filas = await conn.fetch(
            "SELECT * FROM publicaciones_modulo WHERE module_id = $1 AND activo = $2 ORDER BY destino",
            module_id,
            True,
        )
    return [dict(f) for f in filas]


async def _existe_fila(module_id: str, destino: str) -> bool:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT 1 FROM publicaciones_modulo WHERE module_id = $1 AND destino = $2",
            module_id,
            destino,
        )
    return fila is not None


async def fijar_activo(module_id: str, destino: str, activo: bool) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        if await _existe_fila(module_id, destino):
            await conn.execute(
                "UPDATE publicaciones_modulo SET activo = $1 WHERE module_id = $2 AND destino = $3",
                activo, module_id, destino,
            )
        else:
            await conn.execute(
                "INSERT INTO publicaciones_modulo (module_id, destino, activo) VALUES ($1, $2, $3)",
                module_id, destino, activo,
            )


async def fijar_periodicidad(module_id: str, destino: str, minutos: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        if await _existe_fila(module_id, destino):
            await conn.execute(
                "UPDATE publicaciones_modulo SET periodicidad_minutos = $1 WHERE module_id = $2 AND destino = $3",
                minutos, module_id, destino,
            )
        else:
            await conn.execute(
                "INSERT INTO publicaciones_modulo (module_id, destino, periodicidad_minutos) VALUES ($1, $2, $3)",
                module_id, destino, minutos,
            )


async def fijar_csv(module_id: str, destino: str, archivo: str, campo: str) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        if await _existe_fila(module_id, destino):
            await conn.execute(
                "UPDATE publicaciones_modulo SET csv_archivo = $1, csv_campo = $2 WHERE module_id = $3 AND destino = $4",
                archivo, campo, module_id, destino,
            )
        else:
            await conn.execute(
                "INSERT INTO publicaciones_modulo (module_id, destino, csv_archivo, csv_campo) VALUES ($1, $2, $3, $4)",
                module_id, destino, archivo, campo,
            )


def teclado(
    boton_texto: str | None, boton_url: str | None, botones_extra: list[tuple[str, str]] | None
) -> InlineKeyboardMarkup | None:
    filas = []
    if boton_texto and boton_url:
        filas.append([InlineKeyboardButton(boton_texto, url=boton_url)])
    if botones_extra:
        for texto, url in botones_extra:
            filas.append([InlineKeyboardButton(texto, url=url)])
    return InlineKeyboardMarkup(filas) if filas else None


__all__ = [
    "obtener_config",
    "obtener_destinos_activos",
    "fijar_activo",
    "fijar_periodicidad",
    "fijar_csv",
    "teclado",
]
