from __future__ import annotations

import os

from telegram.ext import CommandHandler

from .evaluador import evaluar_periodico
from .recuperacion import reactivar_command, simular_command

# Mictlantecuhtli: segundo bot de respaldo/failover, proceso separado
# (mictlantecuhtli.py). Espejo del concepto de ALFA-1 ("SOMBRA",
# OLIMPO/alfa1/future/SOMBRA_ARQUITECTURA_Y_BASE.md), pero ALFA-1 nunca
# construyo de verdad el bot de respaldo independiente -- solo el
# monitoreo pasivo (heartbeat + calculo de estado). Fernando pidio cubrir
# TODO lo que ese documento planteaba por escrito, con tono
# neutral/tecnico (nunca "Comando Conjunto"/"Protocolo Emboscada"/
# "Estado de Sitio") y nombre propio: Mictlantecuhtli. Ver estado.py
# para la maquina de estados (consolidada de las 7 fases del documento
# original a 5, documentado ahi el motivo).

EVALUAR_INTERVALO_SEGUNDOS_DEFECTO = 30


def install_tecuhtli(app) -> None:
    app.add_handler(CommandHandler("reactivar", reactivar_command))
    app.add_handler(CommandHandler("tecuhtli_simular", simular_command))
    intervalo = int(os.environ.get("TECUHTLI_EVALUAR_INTERVALO_SEGUNDOS", EVALUAR_INTERVALO_SEGUNDOS_DEFECTO))
    app.job_queue.run_repeating(evaluar_periodico, interval=intervalo, first=5)


__all__ = ["install_tecuhtli"]
