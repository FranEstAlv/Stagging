from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .excepciones import ModuloInvalido


def importar_modulo(module_id: str, entrypoint: str, carpeta: Path):
    if ":" not in entrypoint:
        raise ModuloInvalido(f"entrypoint invalido para '{module_id}': {entrypoint!r}")
    nombre_archivo, funcion = entrypoint.split(":", 1)
    ruta = carpeta / f"{nombre_archivo}.py"
    if not ruta.exists():
        raise ModuloInvalido(f"No se encontro {ruta}")

    # Un modulo puede tener varios archivos propios en su misma carpeta
    # (ej. trivia.py + preguntas.py) e importarlos entre si con
    # "import preguntas". Sin esto, solo se podrian escribir modulos de un
    # unico archivo. Se agrega al final de sys.path (no al principio) para
    # que nunca tape un paquete real ya instalado si un modulo externo
    # nombra un archivo igual (ej. "json.py").
    carpeta_str = str(carpeta)
    if carpeta_str not in sys.path:
        sys.path.append(carpeta_str)

    spec = importlib.util.spec_from_file_location(f"mictlan_ext_{module_id}", ruta)
    if spec is None or spec.loader is None:
        raise ModuloInvalido(f"No se pudo cargar el spec de {ruta}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, funcion):
        raise ModuloInvalido(f"El modulo '{module_id}' no define '{funcion}'")
    return mod, getattr(mod, funcion)


__all__ = ["importar_modulo"]
