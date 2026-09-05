from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ... import invitaciones, paginacion
from ...mensajes import agregar_boton_cerrar
from ..grupos import activar, desactivar, establecer_modo_ingreso, establecer_principal, listar

# Seccion "Grupos" de /mando -- la deteccion automatica ya existe
# (modules/grupos.py, ChatMemberHandler sobre my_chat_member, decision ya
# confirmada por Fernando, ver CLAUDE.md "Grupos dinamicos (plan)"). Esto
# solo agrega la UI para listar/activar/desactivar lo que ya se detecto --
# nunca se borra un grupo de la tabla desde aca, no se pidio.

CB_GRUPOS = "mando:grp"
CB_MENU = "mando:menu"

_EMOJI_TIPO = {"group": "👥", "supergroup": "👥", "channel": "📢", "private": "👤"}
_ETIQUETA_MODO_INGRESO = {"ninguno": "🚫 Ninguno", "captcha": "🧮 Captcha", "aprobacion": "🛂 Aprobación admin"}


def _cb(*partes) -> str:
    return ":".join((CB_GRUPOS, *(str(p) for p in partes)))


def _int(valor: str | None) -> int:
    if valor is None or not valor.lstrip("-").isdigit():
        return 0
    return int(valor)


def _boton_grupo(g: dict, pagina: int) -> InlineKeyboardButton:
    estado = "✅" if g["activo"] else "⛔"
    icono = _EMOJI_TIPO.get(g["tipo"], "❔")
    etiqueta = f"{estado} {icono} {g['nombre'] or g['chat_id']}"
    # Misma tecnica que el panel de Modulos: la pagina viaja embebida en el
    # callback para que "Volver" desde el detalle regrese a la pagina de
    # origen, no siempre a la primera.
    return InlineKeyboardButton(etiqueta, callback_data=_cb("ver", g["chat_id"], pagina))


async def _vista_lista(pagina: int = 0, nota: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    grupos = await listar()
    pagina = paginacion.pagina_valida(pagina, len(grupos))

    lineas = ["🏘 <b>Grupos</b>"]
    if nota:
        lineas.append("")
        lineas.append(nota)
    lineas.append("")
    if not grupos:
        lineas.append("(ninguno todavía — se registran solos cuando agregan el bot a un chat, siempre inactivos)")
    else:
        total_pag = paginacion.total_paginas(len(grupos))
        pie_pagina = f" — página {pagina + 1}/{total_pag}" if total_pag > 1 else ""
        lineas.append(f"✅ activo / ⛔ inactivo{pie_pagina}")
    texto = "\n".join(lineas)

    botones = [_boton_grupo(g, pagina) for g in grupos]
    filas = paginacion.filas(botones, pagina)
    controles = paginacion.fila_controles(pagina, len(grupos), _cb("pagina"))
    if controles:
        filas.append(controles)
    filas.append([InlineKeyboardButton("⬅️ Volver", callback_data=CB_MENU)])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def _vista_detalle(chat_id: int, pagina_origen: int = 0, nota: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    grupos = await listar()
    g = next((x for x in grupos if x["chat_id"] == chat_id), None)
    if g is None:
        return await _vista_lista(pagina_origen, "⚠️ Ese grupo ya no está registrado.")

    lineas = [
        f"🏘 <b>{html.escape(g['nombre'] or str(chat_id))}</b>",
        f"<code>{chat_id}</code>",
        "",
        f"Tipo: {html.escape(g['tipo'])}",
        f"Estado: {'✅ activo' if g['activo'] else '⛔ inactivo'}",
        f"Agregado: {html.escape(str(g['agregado_en']))}",
        f"Principal: {'⭐ sí' if g['principal'] else 'no'}",
        f"Ingreso de nuevo miembro: {_ETIQUETA_MODO_INGRESO.get(g['modo_ingreso'], g['modo_ingreso'])}",
    ]
    if nota:
        lineas.append("")
        lineas.append(nota)

    filas = []
    if g["activo"]:
        filas.append([InlineKeyboardButton("⛔ Desactivar", callback_data=_cb("desactivar", chat_id, pagina_origen))])
    else:
        filas.append([InlineKeyboardButton("✅ Activar", callback_data=_cb("activar", chat_id, pagina_origen))])
    if not g["principal"]:
        filas.append([InlineKeyboardButton("⭐ Marcar como principal", callback_data=_cb("principal", chat_id, pagina_origen))])

    # Modo de ingreso: captcha de aritmetica vs aprobacion manual de un
    # admin/vendedor -- nunca ambos a la vez, ver mictlan/bienvenida.py /
    # mictlan/ingreso_admin.py. Solo se muestran los botones de los modos
    # que NO son el actual.
    modo_actual = g["modo_ingreso"]
    botones_modo = [
        InlineKeyboardButton(etiqueta, callback_data=_cb("modo", chat_id, pagina_origen, modo))
        for modo, etiqueta in _ETIQUETA_MODO_INGRESO.items()
        if modo != modo_actual
    ]
    filas.append(botones_modo)

    if g["principal"] or modo_actual == "aprobacion":
        # Link de invitacion: se genera para el grupo principal y para
        # cualquier grupo en modo 'aprobacion' (el propio diseño de ALFA-1
        # que se está espejando incluye ese link) -- los grupos/canales
        # secundarios sin ese modo usan /canales (mictlan/modules/canales.py),
        # no este panel.
        ultimo = await invitaciones.ultimo_link(chat_id)
        if ultimo:
            lineas.append("")
            lineas.append(f"🔗 Último link: {html.escape(ultimo['invite_link'])}")
        filas.append([InlineKeyboardButton("🔗 Generar nuevo link", callback_data=_cb("link", chat_id, pagina_origen))])
    texto = "\n".join(lineas)

    filas.append([InlineKeyboardButton("⬅️ Volver", callback_data=_cb("pagina", pagina_origen))])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def manejar(context: ContextTypes.DEFAULT_TYPE, admin_id: int, partes: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    """Punto de entrada unico llamado por el dispatcher de mando/__init__.py
    para cualquier callback_data que empiece con 'mando:grp' -- 'partes' es
    todo lo que sigue a ese prefijo, mismo patron que modulos.manejar().
    Recibe 'context' (no solo 'partes', como antes) porque generar un link
    de invitacion necesita context.bot, y 'admin_id' (el user_id de quien
    aprieta el boton, mismo patron que mantenimiento.manejar) porque
    invitaciones.generar_link registra quien genero cada link."""
    accion = partes[0] if partes else None
    if accion is None:
        return await _vista_lista()

    if accion == "pagina":
        return await _vista_lista(_int(partes[1] if len(partes) > 1 else None))

    chat_id_str = partes[1] if len(partes) > 1 else None
    if chat_id_str is None or not chat_id_str.lstrip("-").isdigit():
        return await _vista_lista()
    chat_id = int(chat_id_str)
    pagina_origen = _int(partes[2] if len(partes) > 2 else None)

    if accion == "ver":
        return await _vista_detalle(chat_id, pagina_origen)

    if accion == "activar":
        await activar(chat_id)
        return await _vista_detalle(chat_id, pagina_origen)

    if accion == "desactivar":
        await desactivar(chat_id)
        return await _vista_detalle(chat_id, pagina_origen)

    if accion == "principal":
        await establecer_principal(chat_id)
        return await _vista_detalle(chat_id, pagina_origen, "⭐ Marcado como grupo principal.")

    if accion == "modo":
        modo = partes[3] if len(partes) > 3 else None
        if modo not in _ETIQUETA_MODO_INGRESO:
            return await _vista_detalle(chat_id, pagina_origen)
        await establecer_modo_ingreso(chat_id, modo)
        return await _vista_detalle(chat_id, pagina_origen, f"✅ Ingreso configurado como {_ETIQUETA_MODO_INGRESO[modo]}.")

    if accion == "link":
        try:
            await invitaciones.generar_link(context, chat_id, admin_id)
        except TelegramError as exc:
            return await _vista_detalle(chat_id, pagina_origen, f"⚠️ No se pudo generar el link: {exc}")
        return await _vista_detalle(chat_id, pagina_origen, "✅ Link nuevo generado.")

    return await _vista_lista()


__all__ = ["CB_GRUPOS", "manejar"]
