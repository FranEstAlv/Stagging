from __future__ import annotations

import asyncio
import logging

import aiosqlite

from . import datos
from .db import _traducir

logger = logging.getLogger("mictlan.almacen_modulos")

# Resuelve el hueco de "contexto.db" documentado en PROGRESO.md/
# GUIA_SDK_MODULOS_EXTERNOS.md: hoy trivia y compartir pierden todo su
# estado en cada restart porque no tienen donde persistir. Diseño:
#
# - UN archivo SQLite por modulo (datos.carpeta_estado(module_id)), nunca
#   compartido con otro modulo ni con las tablas core de db.py -- aislamiento
#   fisico real, no solo un scope de permiso.
# - UNA conexion aiosqlite persistente por modulo, abierta una sola vez y
#   reusada durante toda la vida del proceso (mismo espiritu que _pool en
#   db.py). aiosqlite corre en su propio hilo con una cola interna, asi que
#   muchas peticiones concurrentes de USUARIOS distintos contra el MISMO
#   modulo nunca corrompen el archivo -- se encolan solas, sin que el modulo
#   tenga que pensar en eso.
# - Conexiones (y candados) separadas POR modulo, no una global compartida:
#   un modulo con mucho trafico (ej. publicadorprod corriendo cada 60s)
#   nunca hace esperar a otro modulo sin relacion -- tareas de verdad
#   independientes.
# - WAL + synchronous=NORMAL: cada commit sobrevive un crash del proceso sin
#   dejar el archivo a medias -- la garantia concreta de "no perder nada de
#   los usuarios" que se pidio.
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
    module_id, nunca compartido. Misma forma de API que db.py
    (execute/fetch/fetchrow/fetchval, sintaxis $1/now()) para que un autor
    de modulo que ya conoce el codigo interno no tenga que aprender una API
    distinta. Async de verdad (aiosqlite): nunca bloquea el event loop, asi
    que muchas peticiones de usuarios distintos contra distintos modulos (o
    contra el mismo) siguen atendiendose todas mientras una escritura esta
    en curso."""

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
        mismo patron que _LEDGER_LOCK en creditos.py, para cualquier
        seccion critica leer-y-decidir (ej. 'solo si no existe ya una fila
        para este file_unique_id', 'sumar 1 al contador sin perder un
        incremento concurrente'). Uso: `async with contexto.datos.db.bloqueo:`."""
        return _lock_de(self.module_id)


async def cerrar_todas() -> None:
    """Cierra todas las conexiones de almacen abiertas -- se llama en el
    shutdown del proceso (ver _post_shutdown en main.py) para dejar los
    archivos -wal/-shm prolijos. WAL ya hace fsync en cada commit, asi que
    ningun write confirmado se pierde aunque esto no se llegue a correr
    (ej. un kill -9)."""
    for module_id, conn in list(_conexiones.items()):
        await conn.close()
        _conexiones.pop(module_id, None)
    logger.info("almacenes de modulos cerrados")


__all__ = ["AlmacenModulo", "cerrar_todas"]
