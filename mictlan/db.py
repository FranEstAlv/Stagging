from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager

import aiosqlite

# Adaptado a mano de mictlan/db.py (Postgres/asyncpg) para SQLite, exclusivo
# del bot de pruebas. No es el db.py real de Mictlan -- ver CLAUDE.md del
# repo principal: la decision de Postgres para produccion sigue firme.

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    rol TEXT NOT NULL DEFAULT 'miembro' CHECK (rol IN ('miembro', 'vendedor', 'administrador', 'root')),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS membresias (
    user_id INTEGER PRIMARY KEY REFERENCES usuarios(user_id),
    inicio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fin TEXT NOT NULL,
    activa INTEGER NOT NULL DEFAULT 1
);

-- Lista negra: usuario baneado (expulsado de todos los grupos/canales
-- gestionados) con evidencia -- motivo + foto -- para que un admin sepa
-- por que no debe volver a aceptarlo si intenta reingresar. Espejo del
-- concepto "blacklist" de ALFA-1 (samaritan/services/global_moderation.py),
-- reescrito de cero. Distinto de una expulsion por membresia vencida (esa
-- es solo por tiempo, sin motivo, y NO pasa por esta tabla -- ver
-- "expulsiones" abajo, confirmado explicitamente por Fernando: son
-- mecanismos diferentes aunque ambos terminen expulsando de todos los
-- grupos).
CREATE TABLE IF NOT EXISTS blacklist (
    user_id INTEGER PRIMARY KEY REFERENCES usuarios(user_id),
    motivo TEXT NOT NULL,
    foto_file_id TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activo INTEGER NOT NULL DEFAULT 1
);

-- Auditoria de expulsiones, insert-only (mismo patron que
-- creditos_ledger): una fila por cada grupo/canal en el que se intento
-- expulsar a alguien, con el resultado real de esa llamada puntual a la
-- API de Telegram. "tipo" distingue un baneo (motivo + entrada en
-- blacklist) de una futura expulsion automatica por membresia vencida
-- (sin motivo, sin blacklist -- todavia no construida, ver
-- "Modo de mantenimiento"/roadmap) -- se deja como TEXT libre, sin CHECK,
-- para no bloquear ese tipo nuevo el dia que se construya.
CREATE TABLE IF NOT EXISTS expulsiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    motivo TEXT,
    admin_id INTEGER,
    resultado TEXT NOT NULL,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Modo de mantenimiento: ventanas de mantenimiento consciente, para que
-- un futuro heartbeat/chequeo de salud (todavia no existe, ver
-- "Modo de mantenimiento (plan)" en CLAUDE.md) pueda distinguir una pausa
-- deliberada de una caida real. Espejo del concepto de ALFA-1
-- (samaritan/ops/maintenance.py: operational_maintenance_windows),
-- reescrito de cero. Solo la ULTIMA fila (mayor id) importa para saber el
-- estado actual -- las anteriores quedan como historial. Por diseno (igual
-- que ALFA-1) esto NO detiene el bot, NO cierra grupos, NO expulsa a
-- nadie: es solo el estado que una fase futura podria consultar.
CREATE TABLE IF NOT EXISTS mantenimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activo INTEGER NOT NULL DEFAULT 1,
    iniciado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hasta TEXT,
    finalizado_en TEXT,
    motivo TEXT,
    admin_id INTEGER,
    finalizado_por INTEGER
);

CREATE TABLE IF NOT EXISTS reportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES usuarios(user_id),
    texto TEXT NOT NULL,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atendido INTEGER NOT NULL DEFAULT 0,
    atendido_por INTEGER,
    atendido_en TEXT
);

CREATE TABLE IF NOT EXISTS sdk_modulos (
    module_id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    origen TEXT NOT NULL CHECK (origen IN ('interno', 'externo')),
    activo INTEGER NOT NULL DEFAULT 1,
    instalado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Grupos/canales dinamicos: se registran solos cuando el bot es agregado
-- (ver ChatMemberHandler sobre my_chat_member), pero quedan inactivos
-- hasta que un admin/root los active a proposito -- que cualquiera meta
-- al bot a un chat no le da poderes ahi automaticamente.
CREATE TABLE IF NOT EXISTS grupos (
    chat_id INTEGER PRIMARY KEY,
    nombre TEXT,
    tipo TEXT NOT NULL CHECK (tipo IN ('group', 'supergroup', 'channel', 'private')),
    activo INTEGER NOT NULL DEFAULT 0,
    agregado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Configuracion de publicacion por modulo -- a que grupo/canal publica,
-- boton fijo (editable sin tocar codigo), on/off, periodicidad si es
-- programado, y la plantilla de texto/formato. Un modulo externo nunca
-- escribe ni lee esta tabla directo -- pasa siempre por contexto.canal.
-- Un modulo puede tener VARIOS destinos a la vez (ej. canal + grupo
-- principal, igual que refe_command en core.py de ALFA-1 -- publica en
-- los dos, cada uno con su propio boton, y reporta por separado si cada
-- uno tuvo exito o fallo). "destino" es una etiqueta libre elegida por
-- quien configura el modulo (ej. 'canal', 'principal'), no un campo con
-- significado especial para el SDK.
CREATE TABLE IF NOT EXISTS publicaciones_modulo (
    module_id TEXT NOT NULL,
    destino TEXT NOT NULL DEFAULT 'principal',
    chat_id INTEGER REFERENCES grupos(chat_id),
    boton_texto TEXT,
    boton_url TEXT,
    activo INTEGER NOT NULL DEFAULT 0,
    periodicidad_minutos INTEGER,
    plantilla_texto TEXT,
    csv_archivo TEXT,
    csv_campo TEXT,
    actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (module_id, destino)
);

-- Ledger de creditos, insert-only -- el saldo de un usuario NUNCA se
-- guarda como columna aparte, se deriva siempre de SUM(delta) sobre esta
-- tabla (ver mictlan/creditos.py). saldo_resultante es una foto del saldo
-- justo despues de ESE movimiento, para auditar de un vistazo sin tener
-- que sumar todo el historial -- no es la fuente de verdad, es cache de
-- lectura. module_id es NULL cuando el movimiento lo hizo un admin desde
-- /otorgar (nunca un modulo externo: contexto.creditos no expone
-- "otorgar", ver PROGRESO.md, comparacion con el SDK de ALFA-1
-- 2026-09-01 -- ahi el unico camino real para un modulo externo era un
-- atajo sin permiso que si permitia acuñar creditos, leccion a NO
-- repetir). reembolso_de referencia el tx_id del cobro original cuando
-- esta fila es un reembolso.
CREATE TABLE IF NOT EXISTS creditos_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_id TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES usuarios(user_id),
    delta INTEGER NOT NULL,
    saldo_resultante INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    module_id TEXT,
    admin_id INTEGER,
    reembolso_de TEXT REFERENCES creditos_ledger(tx_id),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Links de invitacion de un solo uso (member_limit=1 en la API de
-- Telegram -- Telegram mismo invalida el link despues del primer
-- ingreso, no hace falta un mecanismo propio de deteccion/revocacion).
-- Insert-only, mismo patron que creditos_ledger/expulsiones: una fila
-- por cada link generado, nunca se actualiza -- el "actual" de un chat
-- es simplemente la fila mas reciente para ese chat_id. Dos flujos
-- distintos insertan aca (ver PROGRESO.md, sesion 2026-09-01): el panel
-- de /mando (solo genera para el grupo principal) y el comando /canales
-- (miembro validado, solo para grupos/canales secundarios).
CREATE TABLE IF NOT EXISTS invitaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES grupos(chat_id),
    invite_link TEXT NOT NULL,
    creado_por INTEGER NOT NULL,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Mictlantecuhtli: latidos del bot PRINCIPAL (ver mictlan/heartbeat.py,
-- install_heartbeat(app) en main.py) -- una fila por cada job periodico,
-- podada a las ultimas 500. Leida por el proceso SEPARADO de
-- Mictlantecuhtli (mictlantecuhtli.py) via la misma DB compartida, nunca
-- por HTTP -- ver "Grupo principal..." mas arriba para el precedente de
-- por que DB compartida es la opcion mas simple ya usada en este repo.
CREATE TABLE IF NOT EXISTS heartbeats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Mictlantecuhtli: estado actual (ver mictlan/tecuhtli/). Solo la ULTIMA
-- fila importa, mismo patron que mantenimiento -- las anteriores quedan
-- como historial. 'ventana_hasta' solo se usa en fase
-- 'recuperacion_pendiente'.
CREATE TABLE IF NOT EXISTS tecuhtli_estado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fase TEXT NOT NULL,
    entrado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ventana_hasta TEXT,
    motivo TEXT
);
"""

# Migracion sobre una tabla ya existente (grupos) -- CREATE TABLE IF NOT
# EXISTS no alcanza para sumar una columna nueva a una tabla que ya
# existia. "ALTER TABLE ... ADD COLUMN IF NOT EXISTS" NO es sintaxis
# valida en SQLite (confirmado, aunque la version instalada es 3.45),
# a diferencia de Postgres -- por eso el chequeo se hace a mano contra
# PRAGMA table_info en vez de confiar en el motor. Exclusivo de este
# adaptador de staging; el db.py real usa el patron
# "ALTER TABLE ... ADD COLUMN IF NOT EXISTS" documentado en
# "Migraciones de esquema (plan)" de CLAUDE.md, que ahi si es valido.
_MIGRACIONES_COLUMNAS = {
    "grupos": [("principal", "INTEGER NOT NULL DEFAULT 0")],
}

_PLACEHOLDER_RE = re.compile(r"\$(\d+)")


def _traducir(query: str, args: tuple):
    """Convierte sintaxis Postgres ($1, now()) a la de sqlite3 (?, CURRENT_TIMESTAMP),
    preservando la reutilizacion del mismo parametro en varias posiciones
    (asyncpg lo permite con $N repetido; sqlite3 con ? posicional no)."""
    query = query.replace("now()", "CURRENT_TIMESTAMP")
    orden: list[int] = []

    def _reemplazar(m: re.Match) -> str:
        orden.append(int(m.group(1)) - 1)
        return "?"

    query = _PLACEHOLDER_RE.sub(_reemplazar, query)
    return query, tuple(args[i] for i in orden)


class _Conexion:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def execute(self, query: str, *args):
        query, args = _traducir(query, args)
        await self._conn.execute(query, args)
        await self._conn.commit()

    async def fetch(self, query: str, *args):
        query, args = _traducir(query, args)
        cursor = await self._conn.execute(query, args)
        filas = await cursor.fetchall()
        await cursor.close()
        return filas

    async def fetchrow(self, query: str, *args):
        query, args = _traducir(query, args)
        cursor = await self._conn.execute(query, args)
        fila = await cursor.fetchone()
        await cursor.close()
        return fila

    async def fetchval(self, query: str, *args):
        query, args = _traducir(query, args)
        cursor = await self._conn.execute(query, args)
        fila = await cursor.fetchone()
        await cursor.close()
        await self._conn.commit()
        return fila[0] if fila else None


class _Pool:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield _Conexion(self._conn)

    async def close(self):
        await self._conn.close()


_pool: _Pool | None = None


async def _aplicar_migraciones_columnas(conn: aiosqlite.Connection) -> None:
    for tabla, columnas in _MIGRACIONES_COLUMNAS.items():
        cursor = await conn.execute(f"PRAGMA table_info({tabla})")
        existentes = {fila[1] for fila in await cursor.fetchall()}
        await cursor.close()
        for nombre, definicion in columnas:
            if nombre not in existentes:
                await conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}")


async def init_pool() -> None:
    global _pool
    ruta = os.environ["DATABASE_URL"].removeprefix("sqlite:///")
    conn = await aiosqlite.connect(ruta)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.executescript(_SCHEMA)
    await _aplicar_migraciones_columnas(conn)
    await conn.commit()
    _pool = _Pool(conn)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> _Pool:
    if _pool is None:
        raise RuntimeError("pool_no_inicializado")
    return _pool
