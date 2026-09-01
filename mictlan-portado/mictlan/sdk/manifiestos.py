from __future__ import annotations

import json
import logging
from pathlib import Path

from .excepciones import ModuloInvalido
from .rutas import EXTERNAL_DIR

logger = logging.getLogger("mictlan.sdk")

CAMPOS_MANIFEST_OBLIGATORIOS = ("module_id", "nombre", "version", "entrypoint")


def leer_manifest(carpeta: Path) -> dict:
    ruta = carpeta / "manifest.json"
    if not ruta.exists():
        raise ModuloInvalido(f"Falta manifest.json en {carpeta.name}")
    try:
        manifest = json.loads(ruta.read_text())
    except json.JSONDecodeError as exc:
        raise ModuloInvalido(f"manifest.json invalido en {carpeta.name}: {exc}") from exc
    faltan = [c for c in CAMPOS_MANIFEST_OBLIGATORIOS if not manifest.get(c)]
    if faltan:
        raise ModuloInvalido(f"manifest.json de {carpeta.name} sin campos: {', '.join(faltan)}")
    return manifest


def descubrir_manifiestos() -> list[dict]:
    """Escaneo de solo lectura de external_modules/*/manifest.json -- ningun
    import, ningun toque a la DB. Cada dict trae ademas '_carpeta' (Path)."""
    if not EXTERNAL_DIR.exists():
        return []
    encontrados = []
    for carpeta in sorted(p for p in EXTERNAL_DIR.iterdir() if p.is_dir()):
        try:
            manifest = leer_manifest(carpeta)
        except ModuloInvalido:
            logger.exception("manifest invalido en %s, omitido del escaneo", carpeta.name)
            continue
        manifest["_carpeta"] = carpeta
        encontrados.append(manifest)
    return encontrados


def obtener_manifest(module_id: str) -> dict | None:
    """Lee manifest.json del disco para mostrarlo en un panel (version,
    entrypoint, permissions) -- None si la carpeta no existe o el manifest
    es invalido. No importa el modulo ni toca la DB."""
    carpeta = EXTERNAL_DIR / module_id
    if not carpeta.is_dir():
        return None
    try:
        return leer_manifest(carpeta)
    except ModuloInvalido:
        return None


__all__ = ["CAMPOS_MANIFEST_OBLIGATORIOS", "leer_manifest", "descubrir_manifiestos", "obtener_manifest"]
