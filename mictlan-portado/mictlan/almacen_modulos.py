from __future__ import annotations

import asyncio
import logging
import re

import aiosqlite

from . import datos

logger = logging.getLogger("mictlan.almacen_modulos")

# La base principal (mictlan/db.py) es Postgres real via asyncpg, que ya
# entiende $1/now() nativamente -- no necesita traduccion. Pero el
# almacen PROPIO de un modulo sigue siendo SQLite (deliberado, ver
# docstring del modulo abajo), asi que expone la misma sintaxis $1/now()
# que el resto del bot solo por consistencia de API -- traduciendola aca
# adentro a la sintaxis real de SQLite (?/CURRENT_TIMESTAMP).
_PLACEHOLDER_RE = re.compile(r"\$(\d+)")


def _traducir(query: str, args: tuple):
    """Convierte sintaxis Postgres ($1, now()) a la de sqlite3 (?, CURRENT_TIMESTAMP),
    preservando la reutilizacion del mismo parametro en varias posiciones."""
    query = query.replace("now()", "CURRENT_TIMESTAMP")
    orden: list[int] = []

    def _reemplazar(m: re.Match) -> str:
        orden.append(int(m.group(1)) - 1)
        return "?"

    query = _PLACEHOLDER_RE.sub(_reemplazar, query)
    return query, tuple(args[i] for i in orden)

# Persistencia propia y privada de cada modulo externo -- deliberadamente
# SQLite, incluso en produccion con Postgres como base principal: cada
# modulo tiene su propio archivo aislado (external_modules/<id>/estado/),
# nunca comparte tabla ni conexion con el resto del bot. Diseño:
#
# - UN archivo SQLite por modulo, nunca compartido con otro modulo ni con
#   las tablas core de Postgres -- aislamiento fisico real, no solo un
#   scope de permiso.
# - UNA conexion aiosqlite persistente por modulo, abierta una sola vez y
#   reusada durante toda la vida del proceso. aiosqlite corre en su propio
#   hilo con una cola interna, asi que muchas peticiones concurrentes de
#   USUARIOS distintos contra el MISMO modulo nunca corrompen el archivo.
# - Conexiones (y candados) separadas POR modulo, no una global
#   compartida: un modulo con mucho trafico nunca hace esperar a otro
#   modulo sin relacion -- tareas de verdad independientes.
# - WAL + synchronous=NORMAL: cada commit sobrevive un crash del proceso
#   sin dejar el archivo a medias.
_conexiones: dict[str, aiosqlite.Connection] = {}
_locks: dict[str, asyncio.Lock] = {}

NOMBRE_ARCHIVO = "estado.db"


def _lock_de(module_id: str) -> asyncio.Lock:
    lock = _locks.get(module_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[module_id] = lock
    return lock


async def _conexion_cruda(module_id: str) -> aiosqlite.Connection:
    conn = _conexiones.get(module_id)
    if conn is not None:
        return conn
    ruta = datos.carpeta_estado(module_id) / NOMBRE_ARCHIVO
    conn = await aiosqlite.connect(ruta)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    await conn.commit()
    _conexiones[module_id] = conn
    logger.info("almacen propio abierto: modulo=%s ruta=%s", module_id, ruta)
    return conn


class AlmacenModulo:
    """Persistencia propia y privada de UN modulo -- un archivo SQLite por
    module_id, nunca compartido. Misma forma de API que mictlan.db
    (execute/fetch/fetchrow/fetchval, sintaxis $1/now()) para que un autor
    de modulo que ya conoce el codigo interno no tenga que aprender una
    API distinta, aunque el backend real (SQLite, no Postgres) sea otro.
    Async de verdad (aiosqlite): nunca bloquea el event loop."""

    def __init__(self, module_id: str):
        self.module_id = module_id

    async def execute(self, query: str, *args) -> None:
        conn = await _conexion_cruda(self.module_id)
        query, args = _traducir(query, args)
        await conn.execute(query, args)
        await conn.commit()

    async def executescript(self, script: str) -> None:
        """Para crear el esquema propio del modulo (CREATE TABLE IF NOT
        EXISTS ...) -- pensado para llamarse de forma idempotente (guardia
        propia del modulo) antes del primer uso real."""
        conn = await _conexion_cruda(self.module_id)
        await conn.executescript(script)
        await conn.commit()

    async def fetch(self, query: str, *args) -> list:
        conn = await _conexion_cruda(self.module_id)
        query, args = _traducir(query, args)
        cursor = await conn.execute(query, args)
        filas = await cursor.fetchall()
        await cursor.close()
        return filas

    async def fetchrow(self, query: str, *args):
        conn = await _conexion_cruda(self.module_id)
        query, args = _traducir(query, args)
        cursor = await conn.execute(query, args)
        fila = await cursor.fetchone()
        await cursor.close()
        return fila

    async def fetchval(self, query: str, *args):
        conn = await _conexion_cruda(self.module_id)
        query, args = _traducir(query, args)
        cursor = await conn.execute(query, args)
        fila = await cursor.fetchone()
        await cursor.close()
        await conn.commit()
        return fila[0] if fila else None

    @property
    def bloqueo(self) -> asyncio.Lock:
        """Candado propio de ESTE modulo (nunca compartido con otro) --
        para cualquier seccion critica leer-y-decidir. Uso:
        `async with contexto.datos.db.bloqueo:`."""
        return _lock_de(self.module_id)


async def cerrar_todas() -> None:
    """Cierra todas las conexiones de almacen abiertas -- se llama en el
    shutdown del proceso (ver _post_shutdown en main.py) para dejar los
    archivos -wal/-shm prolijos. WAL ya hace fsync en cada commit, asi que
    ningun write confirmado se pierde aunque esto no se llegue a correr."""
    for module_id, conn in list(_conexiones.items()):
        await conn.close()
        _conexiones.pop(module_id, None)
    logger.info("almacenes de modulos cerrados")


__all__ = ["AlmacenModulo", "cerrar_todas"]
