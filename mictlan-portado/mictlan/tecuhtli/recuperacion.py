from __future__ import annotations

import os

from telegram import Chat, Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from .. import roles
from . import acciones, estado

# /reactivar: unico camino para sacar a Mictlantecuhtli de
# 'respaldo_activo' -- secreto compartido + ventana de tiempo, mismo
# mecanismo tanto para una recuperacion manual como para "confirmar que
# el bot principal volvio de verdad" (ver evaluador.py, por que no hace
# falta un segundo secreto separado).
#
# /tecuhtli_simular: espejo simplificado del "simulador SOMBRA" de
# ALFA-1 -- fuerza una fase a mano para poder probar/demostrar el flujo
# sin esperar los umbrales reales.


def _chat_permitido(chat: Chat | None) -> bool:
    if chat is None:
        return False
    if chat.type == ChatType.PRIVATE:
        return True
    return chat.id == int(os.environ["ADMIN_GROUP_ID"])


async def _autorizado(update: Update) -> bool:
    user = update.effective_user
    if not user or not _chat_permitido(update.effective_chat):
        return False
    rol = await roles.obtener_rol(user.id)
    return roles.alcanza_rol(rol, roles.ROLE_ROOT)


async def reactivar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not await _autorizado(update):
        return  # silencio total, mismo patron que /mando

    estado_actual = await estado.obtener_estado()
    fase_actual = estado_actual["fase"]
    args = context.args or []

    if fase_actual not in (estado.FASE_CRITICO, estado.FASE_RESPALDO_ACTIVO, estado.FASE_RECUPERACION_PENDIENTE):
        await message.reply_text("✅ Todo en orden, no hace falta reactivar nada.")
        return

    if not args:
        await estado.iniciar_ventana_recuperacion()
        segundos = os.environ.get("TECUHTLI_VENTANA_RECUPERACION_SEGUNDOS", "30")
        await message.reply_text(f"🔑 Enviá /reactivar <secreto> dentro de los próximos {segundos}s.")
        return

    estado_actual = await estado.obtener_estado()  # re-leer, pudo cambiar entre el chequeo de arriba y ahora
    if estado_actual["fase"] != estado.FASE_RECUPERACION_PENDIENTE or estado.ventana_vencida(estado_actual):
        if estado_actual["fase"] == estado.FASE_RECUPERACION_PENDIENTE:
            await estado.fijar_fase(estado.FASE_RESPALDO_ACTIVO, motivo="ventana_vencida_en_intento")
        await message.reply_text("⏱ No hay una ventana de recuperación abierta (o venció). Corré /reactivar de nuevo.")
        return

    secreto_correcto = os.environ.get("TECUHTLI_SECRETO_RECUPERACION", "")
    if not secreto_correcto or args[0] != secreto_correcto:
        await message.reply_text("❌ Secreto incorrecto.")
        return

    resultado = await acciones.liberar_todos_los_grupos(context)
    await estado.fijar_fase(estado.FASE_NORMAL, motivo="reactivado_manual")
    await message.reply_text(f"✅ Reactivado. Grupos liberados ({resultado['ok']}/{resultado['total']}).")


async def simular_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not await _autorizado(update):
        return

    args = context.args or []
    if not args or args[0] not in estado.FASES_SEVERIDAD:
        opciones = "|".join(estado.FASES_SEVERIDAD)
        await message.reply_text(f"Uso: /tecuhtli_simular <{opciones}>")
        return

    fase_pedida = args[0]
    await estado.fijar_fase(fase_pedida, motivo="simulacion_manual")
    if fase_pedida == estado.FASE_RESPALDO_ACTIVO:
        await acciones.restringir_todos_los_grupos(context)
    elif fase_pedida == estado.FASE_NORMAL:
        await acciones.liberar_todos_los_grupos(context)
    await message.reply_text(f"🧪 Fase simulada: {fase_pedida}")


__all__ = ["reactivar_command", "simular_command"]
