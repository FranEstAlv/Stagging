from __future__ import annotations

import asyncio
import uuid

from . import db

# Ledger de creditos, mismo nivel que db.py/roles.py. Insert-only: el saldo
# de un usuario nunca se guarda como columna aparte, siempre se deriva de
# SUM(delta) sobre creditos_ledger -- ver el comentario del esquema en
# db.py. Inspirado en CreditService de ALFA-1 pero con una asimetria
# deliberada: este modulo SI tiene otorgar() (acuñar creditos), pero
# contexto.creditos del SDK (mictlan/sdk/facades_creditos.py) NUNCA lo
# expone a un modulo externo -- solo cobrar()/reembolsar(). Leccion
# directa de revisar el SDK real de ALFA-1: ahi el unico camino
# documentado para que un modulo cobrara era un atajo sin gate
# (bot_data["credit_service"]) que SI dejaba acuñar. Ese boquete no
# existe aca porque el metodo simplemente no esta expuesto por fuera de
# este archivo.

# Guarda la seccion critica de leer-saldo-y-decidir dentro de un unico
# candado -- sin esto, dos await de _insertar() para el mismo usuario
# podrian interlazarse entre el SELECT del saldo y el INSERT del
# movimiento (asyncio puede cambiar de tarea en cualquier await) y
# permitir un doble gasto. Un Lock de proceso alcanza porque todo el bot
# corre en un unico proceso Python (un solo event loop) -- el pool de
# conexiones de Postgres no cambia eso: el Lock serializa la SECCION
# CRITICA de Python, no las conexiones de la DB en si. Si algun dia
# Mictlan corriera en multiples procesos/workers, este Lock ya no
# alcanzaria y haria falta un lock a nivel de base de datos (ej.
# `SELECT ... FOR UPDATE`) -- no asumir que este Lock escala mas alla de
# un solo proceso.
_LEDGER_LOCK = asyncio.Lock()


class SaldoInsuficiente(Exception):
    pass


class TransaccionInexistente(Exception):
    pass


async def saldo(user_id: int) -> int:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        valor = await conn.fetchval(
            "SELECT COALESCE(SUM(delta), 0) FROM creditos_ledger WHERE user_id = $1",
            user_id,
        )
    return int(valor or 0)


async def historial(user_id: int, limite: int = 20) -> list[dict]:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        filas = await conn.fetch(
            """
            SELECT tx_id, delta, saldo_resultante, motivo, module_id, admin_id, reembolso_de, creado_en
            FROM creditos_ledger
            WHERE user_id = $1
            ORDER BY id DESC
            LIMIT $2
            """,
            user_id,
            limite,
        )
    return [dict(f) for f in filas]


async def _insertar(
    user_id: int,
    delta: int,
    motivo: str,
    *,
    module_id: str | None = None,
    admin_id: int | None = None,
    reembolso_de: str | None = None,
) -> str:
    """Asume que ya se corrio dentro de _LEDGER_LOCK -- no lo toma de
    nuevo, para que otorgar/cobrar/reembolsar puedan controlar el alcance
    exacto de la seccion critica (cobrar necesita leer el saldo Y decidir
    dentro del mismo candado, no solo insertar)."""
    tx_id = uuid.uuid4().hex
    actual = await saldo(user_id)
    nuevo_saldo = actual + delta
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO creditos_ledger
                (tx_id, user_id, delta, saldo_resultante, motivo, module_id, admin_id, reembolso_de)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            tx_id,
            user_id,
            delta,
            nuevo_saldo,
            motivo,
            module_id,
            admin_id,
            reembolso_de,
        )
    return tx_id


async def otorgar(user_id: int, cantidad: int, motivo: str, *, admin_id: int) -> str:
    """Acuña creditos nuevos. SOLO se llama desde codigo interno gateado
    por rol root (ver mictlan/modules/creditos.py, /otorgar) -- nunca
    exponer esta funcion (ni un wrapper de ella) a traves de
    contexto.creditos del SDK."""
    if cantidad <= 0:
        raise ValueError("cantidad debe ser positiva")
    async with _LEDGER_LOCK:
        return await _insertar(user_id, cantidad, motivo, admin_id=admin_id)


async def cobrar(user_id: int, cantidad: int, motivo: str, *, module_id: str) -> str:
    """Descuenta creditos reales, con revalidacion server-side dentro del
    mismo candado que el insert -- nunca confiar en un saldo leido antes
    (ej. el que se le mostro al usuario en una pantalla de confirmacion)."""
    if cantidad <= 0:
        raise ValueError("cantidad debe ser positiva")
    async with _LEDGER_LOCK:
        actual = await saldo(user_id)
        if actual < cantidad:
            raise SaldoInsuficiente(
                f"user_id={user_id} tiene {actual}, se intento cobrar {cantidad}"
            )
        return await _insertar(user_id, -cantidad, motivo, module_id=module_id)


async def reembolsar(tx_id: str, motivo: str, *, module_id: str) -> str:
    """Reembolsa un cobro propio del modulo -- nunca el de otro modulo, y
    nunca dos veces el mismo tx_id."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        original = await conn.fetchrow("SELECT * FROM creditos_ledger WHERE tx_id = $1", tx_id)
    if original is None:
        raise TransaccionInexistente(f"tx_id '{tx_id}' no existe")
    if original["module_id"] != module_id:
        raise TransaccionInexistente(
            f"tx_id '{tx_id}' no pertenece al modulo '{module_id}'"
        )
    if original["delta"] >= 0:
        raise ValueError("solo se puede reembolsar un cobro (delta negativo)")

    async with _LEDGER_LOCK:
        pool = db.get_pool()
        async with pool.acquire() as conn:
            ya_reembolsado = await conn.fetchrow(
                "SELECT tx_id FROM creditos_ledger WHERE reembolso_de = $1", tx_id
            )
        if ya_reembolsado is not None:
            raise TransaccionInexistente(f"tx_id '{tx_id}' ya fue reembolsado")
        return await _insertar(
            original["user_id"],
            -original["delta"],
            motivo,
            module_id=module_id,
            reembolso_de=tx_id,
        )


__all__ = [
    "SaldoInsuficiente",
    "TransaccionInexistente",
    "saldo",
    "historial",
    "otorgar",
    "cobrar",
    "reembolsar",
]
