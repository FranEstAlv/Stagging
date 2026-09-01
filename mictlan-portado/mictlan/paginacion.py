from __future__ import annotations

from telegram import InlineKeyboardButton

# Regla para CUALQUIER panel de botones que liste items del mismo tipo
# (modulos, grupos, archivos, opciones...): grilla de 2 columnas x 3 filas
# por pagina (6 items), en vez de un boton por fila sin limite -- evita
# paneles kilometricos. Es un helper de UI puro, sin relacion con la base
# de datos -- importable directo tanto desde codigo interno (mictlan/)
# como desde un modulo externo.
COLUMNAS = 2
FILAS_POR_PAGINA = 3
POR_PAGINA = COLUMNAS * FILAS_POR_PAGINA  # 6


def total_paginas(total_items: int) -> int:
    return max(1, -(-total_items // POR_PAGINA))  # division entera hacia arriba


def pagina_valida(pagina: int, total_items: int) -> int:
    """Acota la pagina pedida al rango real -- por si la lista encogio
    (ej. se elimino un item) y la pagina que se pedia ya no existe, o si
    llega un numero invalido desde un callback_data viejo."""
    return max(0, min(pagina, total_paginas(total_items) - 1))


def filas(botones: list[InlineKeyboardButton], pagina: int) -> list[list[InlineKeyboardButton]]:
    """Recorta los botones de UNA pagina (pagina ya validada con
    pagina_valida) y los acomoda en la grilla de 2 columnas x 3 filas."""
    inicio = pagina * POR_PAGINA
    lote = botones[inicio : inicio + POR_PAGINA]
    return [lote[i : i + COLUMNAS] for i in range(0, len(lote), COLUMNAS)]


def fila_controles(pagina: int, total_items: int, prefijo_callback: str) -> list[InlineKeyboardButton] | None:
    """Fila de navegacion Anterior/Siguiente -- None si todo entra en una
    sola pagina. El boton del medio (numero de pagina) apunta a la misma
    pagina actual -- tocarlo solo la vuelve a mostrar (idempotente), asi
    no hace falta un callback_data 'noop' aparte que un router tendria
    que interceptar."""
    total = total_paginas(total_items)
    if total <= 1:
        return None
    controles = []
    if pagina > 0:
        controles.append(InlineKeyboardButton("⬅️", callback_data=f"{prefijo_callback}:{pagina - 1}"))
    controles.append(InlineKeyboardButton(f"📄 {pagina + 1}/{total}", callback_data=f"{prefijo_callback}:{pagina}"))
    if pagina < total - 1:
        controles.append(InlineKeyboardButton("➡️", callback_data=f"{prefijo_callback}:{pagina + 1}"))
    return controles


__all__ = ["COLUMNAS", "FILAS_POR_PAGINA", "POR_PAGINA", "total_paginas", "pagina_valida", "filas", "fila_controles"]
