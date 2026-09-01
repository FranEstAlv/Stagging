from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ... import paginacion, sdk
from ...mensajes import agregar_boton_cerrar

CB_MODULOS = "mando:mod"
CB_MENU = "mando:menu"

_EMOJI_ORIGEN = {"externo": "🧪", "interno": "🏠"}


def _cb(*partes) -> str:
    return ":".join((CB_MODULOS, *(str(p) for p in partes)))


def _int(valor: str | None) -> int:
    if valor is None or not valor.lstrip("-").isdigit():
        return 0
    return int(valor)


def _boton_modulo(m: dict, pagina: int) -> InlineKeyboardButton:
    estado = "✅" if m["activo"] else "⛔"
    origen = _EMOJI_ORIGEN.get(m["origen"], "")
    aviso = " ⚠️" if not m["en_disco"] else ""
    etiqueta = f"{estado} {origen} {m['nombre']}{aviso}"
    # Se embebe la pagina actual en el callback para que "⬅️ Volver" desde
    # el detalle regrese a la MISMA pagina, no siempre a la primera.
    return InlineKeyboardButton(etiqueta, callback_data=_cb("ver", m["module_id"], pagina))


async def _vista_lista(pagina: int = 0, nota: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    modulos = await sdk.listar_modulos()
    pagina = paginacion.pagina_valida(pagina, len(modulos))

    lineas = ["🧩 <b>Módulos</b>"]
    if nota:
        lineas.append("")
        lineas.append(nota)
    lineas.append("")
    if not modulos:
        lineas.append("(ninguno registrado todavía — probá '🔍 Detectar módulos')")
    else:
        total_pag = paginacion.total_paginas(len(modulos))
        pie_pagina = f" — página {pagina + 1}/{total_pag}" if total_pag > 1 else ""
        lineas.append(f"✅ activo / ⛔ inactivo — 🧪 externo / 🏠 interno — ⚠️ sin carpeta en disco{pie_pagina}")
    texto = "\n".join(lineas)

    botones = [_boton_modulo(m, pagina) for m in modulos]
    filas = paginacion.filas(botones, pagina)
    controles = paginacion.fila_controles(pagina, len(modulos), _cb("pagina"))
    if controles:
        filas.append(controles)
    filas.append([InlineKeyboardButton("🔍 Detectar módulos", callback_data=_cb("escanear"))])
    filas.append([InlineKeyboardButton("⬅️ Volver", callback_data=CB_MENU)])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def _vista_detalle(
    module_id: str, pagina_origen: int = 0, error: str | None = None
) -> tuple[str, InlineKeyboardMarkup]:
    m = await sdk.obtener_modulo(module_id)
    if m is None:
        return await _vista_lista(pagina_origen, f"⚠️ '{html.escape(module_id)}' ya no está registrado.")

    manifest = sdk.obtener_manifest(module_id) if m["en_disco"] else None

    lineas = [f"🧩 <b>{html.escape(m['nombre'])}</b>", f"<code>{html.escape(module_id)}</code>"]
    if error:
        lineas.append("")
        lineas.append(f"⚠️ {html.escape(error)}")
    lineas.append("")
    lineas.append(f"Estado: {'✅ activo' if m['activo'] else '⛔ inactivo'}")
    lineas.append(f"Origen: {'🏠 interno' if m['origen'] == 'interno' else '🧪 externo'}")
    lineas.append(f"Cargado en memoria: {'sí' if m['cargado'] else 'no'}")
    if m["en_disco"]:
        lineas.append("Carpeta en disco: sí")
    else:
        lineas.append(f"Carpeta en disco: ⚠️ no (external_modules/{html.escape(module_id)})")
    if manifest:
        lineas.append(f"Versión: {html.escape(str(manifest.get('version', '?')))}")
        permisos = manifest.get("permissions") or []
        lineas.append(f"Permisos: {', '.join(permisos) if permisos else '(ninguno)'}")
    texto = "\n".join(lineas)

    filas = []
    if m["activo"]:
        filas.append([InlineKeyboardButton("⛔ Desactivar", callback_data=_cb("desactivar", module_id, pagina_origen))])
    else:
        filas.append([InlineKeyboardButton("✅ Activar", callback_data=_cb("activar", module_id, pagina_origen))])
    etiqueta_origen = "Marcar externo" if m["origen"] == "interno" else "Marcar interno"
    filas.append([InlineKeyboardButton(f"🔁 {etiqueta_origen}", callback_data=_cb("origen", module_id, pagina_origen))])
    filas.append([InlineKeyboardButton("🗑 Eliminar", callback_data=_cb("borrar", module_id, pagina_origen))])
    filas.append([InlineKeyboardButton("⬅️ Volver", callback_data=_cb("pagina", pagina_origen))])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def _vista_confirmar_borrado(module_id: str, pagina_origen: int) -> tuple[str, InlineKeyboardMarkup]:
    m = await sdk.obtener_modulo(module_id)
    nombre = m["nombre"] if m else module_id
    texto = (
        f"🗑 <b>¿Eliminar {html.escape(nombre)}?</b>\n\n"
        f"<code>{html.escape(module_id)}</code>\n\n"
        "Se desregistra del SDK (se desactiva y se borra su fila de "
        "<code>sdk_modulos</code>). El archivo sigue en "
        "<code>external_modules/</code> — '🔍 Detectar módulos' lo vuelve a "
        "encontrar como nuevo (inactivo) más adelante."
    )
    filas = [
        [InlineKeyboardButton("✅ Sí, eliminar", callback_data=_cb("confirmar", module_id, pagina_origen))],
        [InlineKeyboardButton("⬅️ Cancelar", callback_data=_cb("ver", module_id, pagina_origen))],
    ]
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def manejar(app, partes: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    """Punto de entrada unico llamado por el dispatcher de mando/__init__.py
    para cualquier callback_data que empiece con 'mando:mod' -- 'partes' es
    todo lo que sigue a ese prefijo (ya separado por ':'), cada accion
    consume la cantidad de segmentos que necesita. Devuelve (texto,
    teclado) ya listos para editar el mensaje."""
    accion = partes[0] if partes else None
    if accion is None:
        return await _vista_lista()

    if accion == "pagina":
        return await _vista_lista(_int(partes[1] if len(partes) > 1 else None))

    if accion == "escanear":
        nuevos = await sdk.sincronizar_registro()
        if nuevos:
            nota = f"🔍 Se detectaron {len(nuevos)} módulo(s) nuevo(s), inactivos: {', '.join(nuevos)}."
        else:
            nota = "🔍 Nada nuevo — ya estaba todo registrado."
        return await _vista_lista(0, nota)

    module_id = partes[1] if len(partes) > 1 else None
    if module_id is None:
        return await _vista_lista()
    pagina_origen = _int(partes[2] if len(partes) > 2 else None)

    if accion == "ver":
        return await _vista_detalle(module_id, pagina_origen)

    if accion == "activar":
        try:
            await sdk.activar_modulo(app, module_id)
        except (sdk.ModuloInvalido, sdk.PermisoNoConcedido) as exc:
            return await _vista_detalle(module_id, pagina_origen, error=str(exc))
        return await _vista_detalle(module_id, pagina_origen)

    if accion == "desactivar":
        await sdk.desactivar_modulo(app, module_id)
        return await _vista_detalle(module_id, pagina_origen)

    if accion == "origen":
        try:
            await sdk.alternar_origen(module_id)
        except sdk.ModuloInvalido as exc:
            return await _vista_detalle(module_id, pagina_origen, error=str(exc))
        return await _vista_detalle(module_id, pagina_origen)

    if accion == "borrar":
        return await _vista_confirmar_borrado(module_id, pagina_origen)

    if accion == "confirmar":
        m = await sdk.obtener_modulo(module_id)
        nombre = m["nombre"] if m else module_id
        await sdk.eliminar_modulo(app, module_id)
        return await _vista_lista(
            pagina_origen, f"🗑 <code>{html.escape(module_id)}</code> ({html.escape(nombre)}) eliminado."
        )

    return await _vista_lista()


__all__ = ["CB_MODULOS", "manejar"]
