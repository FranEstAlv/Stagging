from __future__ import annotations

import os
from datetime import datetime, timedelta

from .. import db

# Maquina de estados de Mictlantecuhtli. Consolida las 7 fases del
# documento original de ALFA-1 (que el propio documento aplica de forma
# inconsistente entre su texto narrativo y su pseudocodigo -- confirmado
# leyendo el codigo real) en 5, sin perder funcionalidad:
# "aviso"+"alerta critica" -> alerta/critico (solo avisan, ninguna
# accion); "cierre de perimetro"+"control total" -> respaldo_activo
# (unica fase que restringe grupos de verdad, ver acciones.py);
# "comando de recuperacion"+"entrega de mando" -> recuperacion_pendiente
# + vuelta a normal; "contra-interrogatorio" -> exigir SIEMPRE el mismo
# secreto para bajar de respaldo_activo, incluso si el heartbeat volvio
# solo (ver evaluador.py) -- reemplaza el mecanismo separado que ALFA-1
# dejo sin terminar (su propio codigo real dice literalmente
# "se implementara aqui").

FASE_NORMAL = "normal"
FASE_ALERTA = "alerta"
FASE_CRITICO = "critico"
FASE_RESPALDO_ACTIVO = "respaldo_activo"
FASE_RECUPERACION_PENDIENTE = "recuperacion_pendiente"

FASES_SEVERIDAD = (FASE_NORMAL, FASE_ALERTA, FASE_CRITICO, FASE_RESPALDO_ACTIVO)

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def _parsear(valor: str) -> datetime:
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return datetime.strptime(valor, FORMATO_FECHA)


def _umbral(nombre: str, defecto: int) -> int:
    return int(os.environ.get(nombre, defecto))


async def obtener_estado() -> dict:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow(
            "SELECT fase, entrado_en, ventana_hasta, motivo FROM tecuhtli_estado ORDER BY id DESC LIMIT 1"
        )
    if fila is None:
        return {"fase": FASE_NORMAL, "entrado_en": None, "ventana_hasta": None, "motivo": None}
    return dict(fila)


async def fijar_fase(fase: str, *, motivo: str, ventana_hasta: str | None = None) -> None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tecuhtli_estado (fase, ventana_hasta, motivo) VALUES ($1, $2, $3)",
            fase,
            ventana_hasta,
            motivo,
        )


async def iniciar_ventana_recuperacion() -> None:
    segundos = _umbral("TECUHTLI_VENTANA_RECUPERACION_SEGUNDOS", 30)
    hasta = (datetime.utcnow() + timedelta(seconds=segundos)).strftime(FORMATO_FECHA)
    await fijar_fase(FASE_RECUPERACION_PENDIENTE, motivo="recuperacion_iniciada", ventana_hasta=hasta)


def ventana_vencida(estado: dict) -> bool:
    if not estado.get("ventana_hasta"):
        return True
    return datetime.utcnow() > _parsear(estado["ventana_hasta"])


async def _ultimo_heartbeat() -> str | None:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        valor = await conn.fetchval("SELECT creado_en FROM heartbeats ORDER BY id DESC LIMIT 1")
    return valor


async def severidad_por_heartbeat() -> str:
    """Nunca devuelve recuperacion_pendiente -- esa fase solo se entra a
    mano via /reactivar (ver recuperacion.py), nunca por calculo de
    heartbeat."""
    ultimo = await _ultimo_heartbeat()
    if ultimo is None:
        return FASE_RESPALDO_ACTIVO  # nunca hubo un latido -- se trata como caida real
    antiguedad = (datetime.utcnow() - _parsear(ultimo)).total_seconds()
    if antiguedad > _umbral("TECUHTLI_RESPALDO_SEGUNDOS", 900):
        return FASE_RESPALDO_ACTIVO
    if antiguedad > _umbral("TECUHTLI_CRITICO_SEGUNDOS", 480):
        return FASE_CRITICO
    if antiguedad > _umbral("TECUHTLI_ALERTA_SEGUNDOS", 180):
        return FASE_ALERTA
    return FASE_NORMAL


__all__ = [
    "FASE_NORMAL",
    "FASE_ALERTA",
    "FASE_CRITICO",
    "FASE_RESPALDO_ACTIVO",
    "FASE_RECUPERACION_PENDIENTE",
    "FASES_SEVERIDAD",
    "obtener_estado",
    "fijar_fase",
    "iniciar_ventana_recuperacion",
    "ventana_vencida",
    "severidad_por_heartbeat",
]
