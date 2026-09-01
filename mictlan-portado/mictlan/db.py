from __future__ import annotations

import os

import asyncpg

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    rol TEXT NOT NULL DEFAULT 'miembro' CHECK (rol IN ('miembro', 'vendedor', 'administrador', 'root')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS membresias (
    user_id BIGINT PRIMARY KEY REFERENCES usuarios(user_id),
    inicio TIMESTAMPTZ NOT NULL DEFAULT now(),
    fin TIMESTAMPTZ NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT true
);

-- Lista negra: usuario baneado (expulsado de todos los grupos/canales
-- gestionados) con evidencia -- motivo + foto -- para que un admin sepa
-- por que no debe volver a aceptarlo si intenta reingresar. Distinto de
-- una expulsion por membresia vencida (esa es solo por tiempo, sin
-- motivo, y NO pasa por esta tabla -- ver "expulsiones" abajo).
CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT PRIMARY KEY REFERENCES usuarios(user_id),
    motivo TEXT NOT NULL,
    foto_file_id TEXT NOT NULL,
    admin_id BIGINT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    activo BOOLEAN NOT NULL DEFAULT true
);

-- Auditoria de expulsiones, insert-only (mismo patron que
-- creditos_ledger): una fila por cada grupo/canal en el que se intento
-- expulsar a alguien, con el resultado real de esa llamada puntual a la
-- API de Telegram. "tipo" distingue un baneo (motivo + entrada en
-- blacklist) de una futura expulsion automatica por membresia vencida
-- (sin motivo, sin blacklist -- todavia no construida, ver "Modo de
-- mantenimiento" mas abajo) -- se deja como TEXT libre, sin CHECK, para
-- no bloquear ese tipo nuevo el dia que se construya.
CREATE TABLE IF NOT EXISTS expulsiones (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    tipo TEXT NOT NULL,
    motivo TEXT,
    admin_id BIGINT,
    resultado TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Modo de mantenimiento: ventanas de mantenimiento consciente, para que
-- un futuro heartbeat/chequeo de salud (todavia no existe) pueda
-- distinguir una pausa deliberada de una caida real. Solo la ULTIMA fila
-- (mayor id) importa para el estado actual -- las anteriores quedan como
-- historial. Por diseno esto NO detiene el bot, NO cierra grupos, NO
-- expulsa a nadie: es solo el estado que una fase futura podria
-- consultar.
CREATE TABLE IF NOT EXISTS mantenimiento (
    id SERIAL PRIMARY KEY,
    activo BOOLEAN NOT NULL DEFAULT true,
    iniciado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    hasta TIMESTAMPTZ,
    finalizado_en TIMESTAMPTZ,
    motivo TEXT,
    admin_id BIGINT,
    finalizado_por BIGINT
);

CREATE TABLE IF NOT EXISTS reportes (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES usuarios(user_id),
    texto TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    atendido BOOLEAN NOT NULL DEFAULT false,
    atendido_por BIGINT,
    atendido_en TIMESTAMPTZ
);

-- SDK de modulos externos -- ver mictlan/sdk/ y CONTRATO_SDK_MODULOS.md.
-- Nunca activo=true por defecto: sincronizar_registro() siempre inserta
-- activo=false explicito, este DEFAULT solo documenta el invariante real.
CREATE TABLE IF NOT EXISTS sdk_modulos (
    module_id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    origen TEXT NOT NULL CHECK (origen IN ('interno', 'externo')),
    activo BOOLEAN NOT NULL DEFAULT false,
    instalado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Grupos/canales dinamicos: se registran solos cuando el bot es agregado
-- (ChatMemberHandler sobre my_chat_member, ver modules/grupos.py), pero
-- quedan inactivos hasta que un admin/root los active a proposito desde
-- /mando -> Grupos -- que cualquiera meta al bot a un chat no le da
-- poderes ahi automaticamente. chat_id es BIGINT (no INTEGER): los IDs de
-- supergrupo/canal de Telegram (formato -100xxxxxxxxxx) exceden el rango
-- de un INTEGER de 32 bits de Postgres.
CREATE TABLE IF NOT EXISTS grupos (
    chat_id BIGINT PRIMARY KEY,
    nombre TEXT,
    tipo TEXT NOT NULL CHECK (tipo IN ('group', 'supergroup', 'channel', 'private')),
    activo BOOLEAN NOT NULL DEFAULT false,
    agregado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Configuracion de publicacion por modulo -- a que grupo/canal publica,
-- boton fijo (editable sin tocar codigo), on/off, periodicidad si es
-- programado, y la plantilla de texto/formato. Un modulo externo nunca
-- escribe ni lee esta tabla directo -- pasa siempre por contexto.canal
-- (mictlan/sdk/facades_canal.py). Un modulo puede tener VARIOS destinos a
-- la vez (ej. canal + grupo principal) -- "destino" es una etiqueta libre
-- elegida por quien configura el modulo, no un campo con significado
-- especial para el SDK.
CREATE TABLE IF NOT EXISTS publicaciones_modulo (
    module_id TEXT NOT NULL,
    destino TEXT NOT NULL DEFAULT 'principal',
    chat_id BIGINT REFERENCES grupos(chat_id),
    boton_texto TEXT,
    boton_url TEXT,
    activo BOOLEAN NOT NULL DEFAULT false,
    periodicidad_minutos INTEGER,
    plantilla_texto TEXT,
    csv_archivo TEXT,
    csv_campo TEXT,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (module_id, destino)
);

-- Ledger de creditos, insert-only -- el saldo de un usuario NUNCA se
-- guarda como columna aparte, se deriva siempre de SUM(delta) sobre esta
-- tabla (ver mictlan/creditos.py). saldo_resultante es una foto del saldo
-- justo despues de ESE movimiento, para auditar de un vistazo sin tener
-- que sumar todo el historial -- no es la fuente de verdad, es cache de
-- lectura. module_id es NULL cuando el movimiento lo hizo un admin desde
-- /otorgar (nunca un modulo externo: contexto.creditos no expone
-- "otorgar", ver CONTRATO_SDK_MODULOS.md). reembolso_de referencia el
-- tx_id del cobro original cuando esta fila es un reembolso.
CREATE TABLE IF NOT EXISTS creditos_ledger (
    id SERIAL PRIMARY KEY,
    tx_id TEXT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL REFERENCES usuarios(user_id),
    delta INTEGER NOT NULL,
    saldo_resultante INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    module_id TEXT,
    admin_id BIGINT,
    reembolso_de TEXT REFERENCES creditos_ledger(tx_id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Links de invitacion de un solo uso (member_limit=1 en la API de
-- Telegram -- Telegram mismo invalida el link despues del primer
-- ingreso). Insert-only, mismo patron que creditos_ledger/expulsiones:
-- una fila por cada link generado, el "actual" de un chat es la fila mas
-- reciente para ese chat_id. Dos flujos generan aca: el panel de /mando
-- (solo para el grupo principal, ver modules/mando/grupos.py) y el
-- comando /canales (miembro con membresia activa, solo para
-- grupos/canales secundarios, ver modules/canales.py).
CREATE TABLE IF NOT EXISTS invitaciones (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES grupos(chat_id),
    invite_link TEXT NOT NULL,
    creado_por BIGINT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Mictlantecuhtli: latidos del bot PRINCIPAL (ver mictlan/heartbeat.py,
-- install_heartbeat(app) en main.py) -- una fila por cada job periodico,
-- podada a las ultimas 500. Leida por el proceso SEPARADO de
-- Mictlantecuhtli (mictlantecuhtli.py, su propio token/Application) via
-- la misma DB compartida, nunca por HTTP.
CREATE TABLE IF NOT EXISTS heartbeats (
    id SERIAL PRIMARY KEY,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Mictlantecuhtli: estado actual (ver mictlan/tecuhtli/). Solo la ULTIMA
-- fila importa, mismo patron que mantenimiento -- las anteriores quedan
-- como historial. 'ventana_hasta' solo se usa en fase
-- 'recuperacion_pendiente'.
CREATE TABLE IF NOT EXISTS tecuhtli_estado (
    id SERIAL PRIMARY KEY,
    fase TEXT NOT NULL,
    entrado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    ventana_hasta TIMESTAMPTZ,
    motivo TEXT
);

-- Migracion sobre una tabla ya existente (grupos) -- CREATE TABLE IF NOT
-- EXISTS no alcanza para sumar una columna nueva a una tabla que ya
-- existia en produccion. Ver "Migraciones de esquema (plan)" en
-- CLAUDE.md: ADD COLUMN IF NOT EXISTS es idempotente en Postgres, correr
-- esto en cada arranque es seguro.
ALTER TABLE grupos ADD COLUMN IF NOT EXISTS principal BOOLEAN NOT NULL DEFAULT false;
"""

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(dsn=os.environ["DATABASE_URL"])
    async with _pool.acquire() as conn:
        await conn.execute(_SCHEMA)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("pool_no_inicializado")
    return _pool
