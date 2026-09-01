from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ... import db, membresias, moderacion, paginacion, roles
from ...mensajes import agregar_boton_cerrar

CB_USUARIOS = "mando:usuarios"
CB_MENU = "mando:menu"
CB_BANEAR_PREFIJO = "mando:usuarios:banear"
CB_REPORTE_PREFIJO = "mando:usuarios:reporte"

_ROLES_EN_ORDEN = [roles.ROLE_MEMBER, roles.ROLE_SELLER, roles.ROLE_ADMIN, roles.ROLE_ROOT]


def _cb(*partes) -> str:
    return ":".join((CB_USUARIOS, *(str(p) for p in partes)))


def _int(valor: str | None) -> int:
    if valor is None or not valor.lstrip("-").isdigit():
        return 0
    return int(valor)


def _formatear_fecha(valor: str) -> str:
    # 'fin'/'creado_en' llegan como TEXT plano de SQLite (ver db.py de
    # staging) -- nunca datetime, nunca .strftime() directo sobre la fila.
    return valor[:10] if valor else "?"


async def _listar_usuarios() -> list[dict]:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        filas = await conn.fetch(
            """
            SELECT u.user_id, u.username, u.rol,
                   CASE WHEN b.user_id IS NOT NULL THEN 1 ELSE 0 END AS baneado
            FROM usuarios u
            LEFT JOIN blacklist b ON b.user_id = u.user_id AND b.activo = 1
            ORDER BY u.actualizado_en DESC
            """
        )
    return [dict(f) for f in filas]


def _boton_usuario(u: dict, pagina: int) -> InlineKeyboardButton:
    emoji_rol = roles.emoji_rol(u["rol"])
    aviso = " ⛔" if u["baneado"] else ""
    etiqueta = f"{emoji_rol} {u['username'] or u['user_id']}{aviso}"
    return InlineKeyboardButton(etiqueta, callback_data=_cb("ver", u["user_id"], pagina))


async def _vista_lista(pagina: int = 0, nota: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    usuarios = await _listar_usuarios()
    pagina = paginacion.pagina_valida(pagina, len(usuarios))

    lineas = ["🛠 <b>Usuarios</b>"]
    if nota:
        lineas.append("")
        lineas.append(nota)
    lineas.append("")
    if not usuarios:
        lineas.append("(ninguno todavía)")
    else:
        total_pag = paginacion.total_paginas(len(usuarios))
        pie_pagina = f" — página {pagina + 1}/{total_pag}" if total_pag > 1 else ""
        lineas.append(f"👤 / 💼 / 🛠 / 👑 — ⛔ baneado{pie_pagina}")
    texto = "\n".join(lineas)

    botones = [_boton_usuario(u, pagina) for u in usuarios]
    filas = paginacion.filas(botones, pagina)
    controles = paginacion.fila_controles(pagina, len(usuarios), _cb("pagina"))
    if controles:
        filas.append(controles)
    filas.append([InlineKeyboardButton("⬅️ Volver", callback_data=CB_MENU)])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def _vista_detalle(user_id: int, pagina_origen: int = 0, nota: str | None = None) -> tuple[str, InlineKeyboardMarkup]:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        u = await conn.fetchrow("SELECT user_id, username, rol FROM usuarios WHERE user_id = $1", user_id)
    if u is None:
        return await _vista_lista(pagina_origen, "⚠️ Ese usuario ya no está registrado.")
    u = dict(u)

    membresia = await membresias.obtener(user_id)
    baneo = await moderacion.esta_en_blacklist(user_id)

    lineas = [f"🛠 <b>{html.escape(u['username'] or str(user_id))}</b>", f"<code>{user_id}</code>"]
    if nota:
        lineas.append("")
        lineas.append(nota)
    lineas.append("")
    lineas.append(f"Rol: {roles.emoji_rol(u['rol'])}")
    if membresia and membresia["activa"] and membresia["fin"]:
        lineas.append(f"Membresía: activa hasta {_formatear_fecha(membresia['fin'])}")
    elif membresia and membresia["fin"]:
        lineas.append(f"Membresía: vencida ({_formatear_fecha(membresia['fin'])})")
    else:
        lineas.append("Membresía: sin membresía")
    if baneo:
        lineas.append(f"Estado: ⛔ baneado ({_formatear_fecha(baneo['creado_en'])})")
    else:
        lineas.append("Estado: ✅ sin baneo")
    texto = "\n".join(lineas)

    filas = [
        [
            InlineKeyboardButton("📅 +7", callback_data=_cb("dias", user_id, 7, pagina_origen)),
            InlineKeyboardButton("📅 +30", callback_data=_cb("dias", user_id, 30, pagina_origen)),
        ],
        [
            InlineKeyboardButton("📅 -7", callback_data=_cb("dias", user_id, -7, pagina_origen)),
            InlineKeyboardButton("📅 -30", callback_data=_cb("dias", user_id, -30, pagina_origen)),
        ],
        [InlineKeyboardButton("🎭 Cambiar rol", callback_data=_cb("rol", user_id, pagina_origen))],
    ]
    if baneo:
        filas.append([InlineKeyboardButton("✅ Desbanear", callback_data=_cb("desbanear", user_id, pagina_origen))])
        filas.append([InlineKeyboardButton("📋 Ver reporte", callback_data=_cb("reporte", user_id, pagina_origen))])
    else:
        filas.append([InlineKeyboardButton("🚫 Banear", callback_data=f"{CB_BANEAR_PREFIJO}:{user_id}:{pagina_origen}")])
    filas.append([InlineKeyboardButton("⬅️ Volver", callback_data=_cb("pagina", pagina_origen))])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def _vista_rol(user_id: int, pagina_origen: int) -> tuple[str, InlineKeyboardMarkup]:
    pool = db.get_pool()
    async with pool.acquire() as conn:
        u = await conn.fetchrow("SELECT rol FROM usuarios WHERE user_id = $1", user_id)
    if u is None:
        return await _vista_lista(pagina_origen, "⚠️ Ese usuario ya no está registrado.")

    texto = f"🎭 <b>Cambiar rol</b>\n<code>{user_id}</code>\n\nRol actual: {roles.emoji_rol(u['rol'])}"
    filas = []
    for rol in _ROLES_EN_ORDEN:
        marca = "✅ " if rol == u["rol"] else ""
        filas.append(
            [InlineKeyboardButton(f"{marca}{roles.emoji_rol(rol)}", callback_data=_cb("rolset", user_id, rol, pagina_origen))]
        )
    filas.append([InlineKeyboardButton("⬅️ Cancelar", callback_data=_cb("ver", user_id, pagina_origen))])
    teclado = agregar_boton_cerrar(InlineKeyboardMarkup(filas))
    return texto, teclado


async def manejar(context: ContextTypes.DEFAULT_TYPE, partes: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    """Punto de entrada unico llamado por el dispatcher de mando/__init__.py
    para cualquier callback_data que empiece con 'mando:usuarios' (salvo
    'banear'/'reporte', interceptados antes por modules/mando/baneo.py --
    ver ese archivo para el motivo). 'partes' es todo lo que sigue al
    prefijo. Recibe 'context' (no solo 'app', como modulos.manejar) porque
    'desbanear' necesita context.bot para levantar el ban en cada grupo."""
    accion = partes[0] if partes else None
    if accion is None:
        return await _vista_lista()

    if accion == "pagina":
        return await _vista_lista(_int(partes[1] if len(partes) > 1 else None))

    user_id_str = partes[1] if len(partes) > 1 else None
    if user_id_str is None or not user_id_str.isdigit():
        return await _vista_lista()
    user_id = int(user_id_str)

    if accion == "ver":
        pagina_origen = _int(partes[2] if len(partes) > 2 else None)
        return await _vista_detalle(user_id, pagina_origen)

    if accion == "dias":
        delta = _int(partes[2] if len(partes) > 2 else None)
        pagina_origen = _int(partes[3] if len(partes) > 3 else None)
        resultado = await membresias.ajustar_dias(user_id, delta)
        if resultado is None:
            return await _vista_detalle(user_id, pagina_origen, "⚠️ No tiene membresía — no hay días que restar.")
        return await _vista_detalle(user_id, pagina_origen)

    if accion == "rol":
        pagina_origen = _int(partes[2] if len(partes) > 2 else None)
        return await _vista_rol(user_id, pagina_origen)

    if accion == "rolset":
        rol = partes[2] if len(partes) > 2 else None
        pagina_origen = _int(partes[3] if len(partes) > 3 else None)
        if rol not in _ROLES_EN_ORDEN:
            return await _vista_detalle(user_id, pagina_origen)
        await roles.establecer_rol(user_id, rol)
        return await _vista_detalle(user_id, pagina_origen, f"✅ Rol actualizado a {roles.emoji_rol(rol)}.")

    if accion == "desbanear":
        pagina_origen = _int(partes[2] if len(partes) > 2 else None)
        await moderacion.quitar_de_blacklist(user_id)
        sync = await moderacion.reingresar_a_todos_los_grupos(context, user_id)
        return await _vista_detalle(
            user_id, pagina_origen, f"✅ Desbaneado. Liberado en {sync['ok']}/{sync['total']} grupos."
        )

    return await _vista_lista()


__all__ = ["CB_USUARIOS", "CB_BANEAR_PREFIJO", "CB_REPORTE_PREFIJO", "manejar"]
