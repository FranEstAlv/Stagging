from __future__ import annotations

from datetime import datetime, timedelta

from . import db

# Modo de mantenimiento -- espejo del concepto de ALFA-1
# (samaritan/ops/maintenance.py), reescrito de cero. Por diseno (igual que
# el original) esto es SOLO un estado consultable: no detiene el bot, no
# cierra grupos, no expulsa a nadie. Sirve para que una fase futura
# (heartbeat/chequeo de salud, ver "Modo de mantenimiento (plan)" en
# CLAUDE.md -- todavia no existe en Mictlan) pueda distinguir una pausa
# deliberada de una caida real vía esta_en_mantenimiento().

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def _parsear(valor: str) -> datetime:
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return datetime.strptime(valor, FORMATO_FECHA)


def tiempo_restante(hasta: str | None) -> str:
    if not hasta:
        return "sin límite"
    segundos = int((_parsear(hasta) - datetime.utcnow()).total_seconds())
    if segundos <= 0:
        return "vencido"
    minutos = segundos // 60
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto} min" if resto else f"{horas} h"


async def _expirar_vencidas() -> None:
    ahora = datetime.utcnow().strftime(FORMATO_FECHA)
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE mantenimiento SET activo = $1, finalizado_en = hasta
            WHERE activo = $2 AND hasta IS NOT NULL AND hasta <= $3
            """,
            False,
            True,
            ahora,
        )


async def estado_actual() -> dict:
    await _expirar_vencidas()
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT id, activo, iniciado_en, hasta, finalizado_en, motivo, admin_id FROM mantenimiento ORDER BY id DESC LIMIT 1"
        )
    return dict(fila) if fila else {"activo": False}


async def esta_en_mantenimiento() -> bool:
    estado = await estado_actual()
    return bool(estado.get("activo"))


async def activar(minutos: int | None, admin_id: int) -> None:
    """minutos=None es mantenimiento indefinido (sin 'hasta'). Cierra
    cualquier ventana activa previa antes de abrir la nueva -- nunca dos
    ventanas activas a la vez."""
    ahora = datetime.utcnow()
    hasta = (ahora + timedelta(minutes=minutos)).strftime(FORMATO_FECHA) if minutos else None
    motivo = f"mantenimiento_{minutos}_minutos" if minutos else "mantenimiento_indefinido"
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE mantenimiento SET activo = $1, finalizado_en = now() WHERE activo = $2",
            False,
            True,
        )
        await conn.execute(
            "INSERT INTO mantenimiento (activo, iniciado_en, hasta, motivo, admin_id) VALUES ($1, $2, $3, $4, $5)",
            True,
            ahora.strftime(FORMATO_FECHA),
            hasta,
            motivo,
            admin_id,
        )


async def desactivar(admin_id: int) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE mantenimiento SET activo = $1, finalizado_en = now(), finalizado_por = $2 WHERE activo = $3",
            False,
            admin_id,
            True,
        )


__all__ = ["estado_actual", "esta_en_mantenimiento", "activar", "desactivar", "tiempo_restante"]
