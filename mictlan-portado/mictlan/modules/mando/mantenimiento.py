from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ... import mantenimiento
from ...mensajes import agregar_boton_cerrar

CB_MANTENIMIENTO = "mando:mnt"
CB_MENU = "mando:menu"


def _cb(*partes) -> str:
    return ":".join((CB_MANTENIMIENTO, *(str(p) for p in partes)))


async def _vista(nota: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    estado = await mantenimiento.estado_actual()
    activo = bool(estado.get("activo"))

    lineas = ["🛠 <b>Mantenimiento</b>"]
    if nota:
        lineas.append("")
        lineas.append(nota)
    lineas.append("")
    lineas.append(f"Estado: {'🟡 activo' if activo else '✅ inactivo'}")
    if activo:
        lineas.append(f"Desde: {estado['iniciado_en'].strftime('%Y-%m-%d %H:%M')}")
        lineas.append(f"Restante: {mantenimiento.tiempo_restante(estado.get('hasta'))}")
        if estado.get("motivo"):
            lineas.append(f"Motivo: {html.escape(str(estado['motivo']))}")
    texto = "\n".join(lineas)

    filas = [
        [
            InlineKeyboardButton("🟡 30 min", callback_data=_cb("start", 30)),
            InlineKeyboardButton("🟠 2 h", callback_data=_cb("start", 120)),
        ],
        [InlineKeyboardButton("🔵 Indefinido", callback_data=_cb("start", "indefinido"))],
    ]
    if activo:
        filas.append([InlineKeyboardButton("✅ Finalizar mantenimiento", callback_data=_cb("stop"))])
    filas.append([InlineKeyboardButton("⬅️ Volver", callback_data=CB_MENU)])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def manejar(admin_id: int, partes: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    """Punto de entrada unico llamado por el dispatcher de mando/__init__.py
    para cualquier callback_data que empiece con 'mando:mnt'. Sin
    ConversationHandler ni texto libre a proposito -- solo botones con
    duraciones fijas, consistente con la regla de centralizar en /mando
    por botones en vez de comandos de texto sueltos."""
    accion = partes[0] if partes else None
    if accion is None:
        return await _vista()

    if accion == "start":
        valor = partes[1] if len(partes) > 1 else None
        if valor == "indefinido":
            await mantenimiento.activar(None, admin_id)
            return await _vista("✅ Mantenimiento activado (indefinido).")
        if valor is not None and valor.isdigit():
            await mantenimiento.activar(int(valor), admin_id)
            return await _vista(f"✅ Mantenimiento activado ({valor} min).")
        return await _vista()

    if accion == "stop":
        await mantenimiento.desactivar(admin_id)
        return await _vista("✅ Mantenimiento finalizado.")

    return await _vista()


__all__ = ["CB_MANTENIMIENTO", "manejar"]
