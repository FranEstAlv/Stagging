from __future__ import annotations

import os
from datetime import datetime

from telegram.ext import ContextTypes

from . import db

# Latidos del bot PRINCIPAL -- para que Mictlantecuhtli (proceso
# separado, mictlantecuhtli.py) sepa si el principal sigue vivo sin que
# este le avise nada directo: ambos leen/escriben la misma DB
# compartida, ninguna API HTTP nueva (ver mictlan/tecuhtli/). Podado a
# las ultimas RETENCION_FILAS -- nunca crece sin limite.

INTERVALO_SEGUNDOS_DEFECTO = 60
RETENCION_FILAS = 500
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


async def _latido(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inserta 'creado_en' calculado en Python (nunca DEFAULT VALUES) --
    mismo criterio que membresias.py/mantenimiento.py."""
    pool = db.get_pool()
    ahora = datetime.utcnow().strftime(FORMATO_FECHA)
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO heartbeats (creado_en) VALUES ($1)", ahora)
        await conn.execute(
            "DELETE FROM heartbeats WHERE id NOT IN (SELECT id FROM heartbeats ORDER BY id DESC LIMIT $1)",
            RETENCION_FILAS,
        )


def install_heartbeat(app) -> None:
    intervalo = int(os.environ.get("TECUHTLI_HEARTBEAT_INTERVAL_SEGUNDOS", INTERVALO_SEGUNDOS_DEFECTO))
    app.job_queue.run_repeating(_latido, interval=intervalo, first=5)


__all__ = ["install_heartbeat"]
