from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import db

# Ajuste de dias de membresia -- usado desde la seccion "Usuarios" de
# /mando (botones +7/+30/-7/-30, ver modules/mando/usuarios.py). 'fin' es
# TIMESTAMPTZ real (no texto): asyncpg lo entrega como datetime consciente
# de zona horaria, asi que la aritmetica de fechas es directa, sin parsear
# ni formatear nada a mano.


async def obtener(user_id: int) -> dict | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT user_id, inicio, fin, activa FROM membresias WHERE user_id = $1",
            user_id,
        )
    return dict(fila) if fila else None


async def ajustar_dias(user_id: int, dias: int) -> dict | None:
    """Suma (dias > 0) o resta (dias < 0) dias a la membresia del usuario,
    recalculando 'activa' contra la hora actual. Si el usuario todavia no
    tiene membresia, restar dias no hace nada (no hay nada de donde
    restar); sumar dias le crea una membresia nueva que arranca ahora."""
    actual = await obtener(user_id)
    ahora = datetime.now(timezone.utc)
    pool = db.get_pool()

    if actual is None:
        if dias <= 0:
            return None
        nuevo_fin = ahora + timedelta(days=dias)
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO membresias (user_id, inicio, fin, activa) VALUES ($1, $2, $3, $4)",
                user_id,
                ahora,
                nuevo_fin,
                True,
            )
        return await obtener(user_id)

    nuevo_fin = actual["fin"] + timedelta(days=dias)
    activa = nuevo_fin > ahora
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE membresias SET fin = $1, activa = $2 WHERE user_id = $3",
            nuevo_fin,
            activa,
            user_id,
        )
    return await obtener(user_id)


async def vencidas() -> list[dict]:
    """Membresias activas cuyo 'fin' ya paso -- candidatas a expulsion
    automatica de todo el ecosistema, ver mictlan/vencimientos.py."""
    ahora = datetime.now(timezone.utc)
    pool = db.get_pool()
    async with pool.acquire() as conn:
        filas = await conn.fetch(
            "SELECT user_id, fin FROM membresias WHERE activa = $1 AND fin <= $2",
            True,
            ahora,
        )
    return [dict(f) for f in filas]


async def desactivar(user_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE membresias SET activa = $1 WHERE user_id = $2", False, user_id)


__all__ = ["obtener", "ajustar_dias", "vencidas", "desactivar"]
