from __future__ import annotations

import csv
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Dos ambitos de datos de referencia para modulos (interno/externo):
#   - propios: carpeta exclusiva de CADA modulo, nadie mas la lee.
#   - compartidos: una sola carpeta general, legible por cualquier modulo
#     con el scope correspondiente -- para catalogos/listas que varios
#     modulos necesitan consultar (ej. un CSV de codigos, un .db de
#     referencia). Ambas viven fuera de git, igual que external_modules/.
EXTERNAL_DIR = Path(__file__).resolve().parent.parent / "external_modules"
COMPARTIDOS_DIR = Path(__file__).resolve().parent.parent / "datos_compartidos"


class ArchivoNoEncontrado(Exception):
    pass


def carpeta_propia(module_id: str) -> Path:
    carpeta = EXTERNAL_DIR / module_id / "datos"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def carpeta_estado(module_id: str) -> Path:
    """Carpeta de persistencia ESCRIBIBLE y privada de un modulo -- separada
    a proposito de carpeta_propia() (esa es de solo lectura, para
    catalogos/CSVs/.db de referencia que un admin coloca a mano en el
    disco). Nunca se comparte entre modulos ni se mezcla con los archivos
    de referencia -- evita que un modulo pise sin querer, por ejemplo, el
    'propio.db' de solo lectura que ya usan consulta1/2/3. Ver
    mictlan/almacen_modulos.py, expuesto como contexto.datos.db."""
    carpeta = EXTERNAL_DIR / module_id / "estado"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def carpeta_compartida() -> Path:
    COMPARTIDOS_DIR.mkdir(parents=True, exist_ok=True)
    return COMPARTIDOS_DIR


def listar(carpeta: Path) -> list[str]:
    return sorted(p.name for p in carpeta.iterdir() if p.is_file())


def leer_csv(ruta: Path) -> list[dict]:
    """Lee un CSV COMPLETO, sin ningun limite de filas -- lo carga entero
    en memoria de una vez (miles de filas no son un problema, son texto
    plano). csv.DictReader ya procesa el archivo entero por diseño; el bug
    documentado en ALFA-1 (extra.py, busqueda que no encontraba valores
    mas alla de ~3000 filas de un CSV de 83000+) nunca tuvo causa raiz
    confirmada -- no se repite ese patron aca: sin slicing, sin limit,
    sin early-break en ningun punto de esta funcion."""
    if not ruta.exists():
        raise ArchivoNoEncontrado(str(ruta))
    with ruta.open(newline="", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        return [dict(fila) for fila in lector]


@contextmanager
def abrir_sqlite_solo_lectura(ruta: Path):
    """Conexion de solo lectura -- cualquier intento de escritura falla.
    Nunca se abre en modo escritura desde este modulo: los datos
    propios/compartidos son de referencia, no un lugar para que un modulo
    guarde estado (para eso existe la futura contexto.db, todavia sin
    construir)."""
    if not ruta.exists():
        raise ArchivoNoEncontrado(str(ruta))
    conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


__all__ = [
    "ArchivoNoEncontrado",
    "carpeta_propia",
    "carpeta_estado",
    "carpeta_compartida",
    "listar",
    "leer_csv",
    "abrir_sqlite_solo_lectura",
]
