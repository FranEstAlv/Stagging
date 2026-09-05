from __future__ import annotations

import importlib.util
import inspect
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
    instalar_fn = getattr(mod, funcion)
    if inspect.iscoroutinefunction(instalar_fn):
        # ciclo_vida.py llama a instalar_fn(recorder, contexto) SIN await
        # (contrato: el entrypoint es siempre sincrono) -- un "async def"
        # devolveria una corrutina sin ejecutar y el modulo quedaria
        # "activo" en sdk_modulos sin haber registrado un solo handler,
        # sin ningun error visible. Se rechaza antes de instalar nada.
        raise ModuloInvalido(
            f"El entrypoint '{funcion}' de '{module_id}' es 'async def' -- tiene que ser sincrono"
        )
    return mod, instalar_fn


def desregistrar_ruta(carpeta: Path) -> None:
    """Inverso de agregar la carpeta a sys.path arriba -- se llama al
    eliminar un modulo para que sys.path no crezca sin limite para
    siempre con carpetas de modulos ya borrados del registro. Nunca
    levanta si la ruta ya no esta (idempotente)."""
    try:
        sys.path.remove(str(carpeta))
    except ValueError:
        pass


__all__ = ["importar_modulo", "desregistrar_ruta"]
