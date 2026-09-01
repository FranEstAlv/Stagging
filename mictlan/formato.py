from __future__ import annotations

import html

# Helpers de formato HTML de Telegram, para armar un mensaje "punto por
# punto" sin que un modulo tenga que memorizar las etiquetas. Cada helper
# escapa el texto que recibe -- si alguien quiere formato anidado
# (ej. negrita + link), compone las funciones: enlace(negrita("texto"), url)
# NO escapa two veces porque cada funcion solo escapa lo que a ELLA le
# llega, no lo que ya viene con tags de otra funcion -- ver _crudo() para
# el caso "ya viene formateado, no lo toques".
#
# El modulo tambien puede ignorar todo esto y mandar su propio string HTML
# armado a mano a contexto.canal.publicar(texto=...) -- no hay obligacion
# de pasar por estos helpers.


def negrita(texto: str) -> str:
    return f"<b>{html.escape(texto)}</b>"


def cursiva(texto: str) -> str:
    return f"<i>{html.escape(texto)}</i>"


def subrayado(texto: str) -> str:
    return f"<u>{html.escape(texto)}</u>"


def tachado(texto: str) -> str:
    return f"<s>{html.escape(texto)}</s>"


def monospace(texto: str) -> str:
    return f"<code>{html.escape(texto)}</code>"


def bloque_codigo(texto: str, lenguaje: str | None = None) -> str:
    clase = f' class="language-{html.escape(lenguaje)}"' if lenguaje else ""
    return f"<pre{clase}>{html.escape(texto)}</pre>"


def cita(texto: str, expandible: bool = False) -> str:
    apertura = "<blockquote expandable>" if expandible else "<blockquote>"
    return f"{apertura}{html.escape(texto)}</blockquote>"


def spoiler(texto: str) -> str:
    return f"<tg-spoiler>{html.escape(texto)}</tg-spoiler>"


def enlace(texto: str, url: str) -> str:
    return f'<a href="{html.escape(url)}">{html.escape(texto)}</a>'


def crudo(texto_html: str) -> str:
    """Passthrough explicito: 'este texto ya viene formateado como HTML de
    Telegram, no lo toques'. Existe para que la intencion quede clara en
    el codigo del modulo en vez de simplemente concatenar strings sueltas."""
    return texto_html


__all__ = [
    "negrita",
    "cursiva",
    "subrayado",
    "tachado",
    "monospace",
    "bloque_codigo",
    "cita",
    "spoiler",
    "enlace",
    "crudo",
]
