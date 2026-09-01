from __future__ import annotations

from telegram.ext import ContextTypes

from .. import mantenimiento
from . import acciones, estado

# Job periodico que decide si hace falta cambiar de fase. Reglas, en
# orden:
# 1. En 'recuperacion_pendiente': si la ventana vencio sin /reactivar
#    exitoso, vuelve a respaldo_activo (sigue restringido) -- nunca se
#    resuelve sola. Mientras la ventana corre, no se re-evalua nada mas.
# 2. En 'respaldo_activo': fase "pegajosa" -- solo /reactivar con el
#    secreto correcto puede sacarla de ahi, ni siquiera que el heartbeat
#    del bot principal vuelva por su cuenta alcanza. Esto es lo que
#    reemplaza el "contra-interrogatorio" que ALFA-1 dejo sin terminar
#    (ver estado.py).
# 3. Si Mictlan esta en mantenimiento deliberado (mantenimiento.py, ya
#    consultado por esta pieza tal como quedo pendiente ahi), nunca
#    escala -- si ya estaba en alerta/critico por una caida previa a que
#    se activara el mantenimiento, se despeja a normal.
# 4. Si no, la fase sigue el heartbeat: 'alerta'/'critico' son solo
#    informativas (avisan y nada mas, se autoajustan libremente en
#    cualquier direccion); solo la transicion A 'respaldo_activo' dispara
#    una accion real (restringir todos los grupos).


async def evaluar_periodico(context: ContextTypes.DEFAULT_TYPE) -> None:
    estado_actual = await estado.obtener_estado()
    fase_actual = estado_actual["fase"]

    if fase_actual == estado.FASE_RECUPERACION_PENDIENTE:
        if estado.ventana_vencida(estado_actual):
            await estado.fijar_fase(estado.FASE_RESPALDO_ACTIVO, motivo="ventana_recuperacion_vencida")
        return

    if fase_actual == estado.FASE_RESPALDO_ACTIVO:
        return

    if await mantenimiento.esta_en_mantenimiento():
        if fase_actual != estado.FASE_NORMAL:
            await estado.fijar_fase(estado.FASE_NORMAL, motivo="mantenimiento_activo")
        return

    nueva_severidad = await estado.severidad_por_heartbeat()
    if nueva_severidad == fase_actual:
        return

    await estado.fijar_fase(nueva_severidad, motivo="heartbeat")

    if nueva_severidad == estado.FASE_RESPALDO_ACTIVO:
        resultado = await acciones.restringir_todos_los_grupos(context)
        await acciones.avisar(
            context,
            f"🔒 Respaldo activo: grupos restringidos ({resultado['ok']}/{resultado['total']}), "
            "sin señal del bot principal. Usá /reactivar cuando vuelva a estar sano.",
        )
    elif nueva_severidad in (estado.FASE_ALERTA, estado.FASE_CRITICO):
        await acciones.avisar(context, f"⚠️ Fase {nueva_severidad}: sin señal del bot principal.")


__all__ = ["evaluar_periodico"]
