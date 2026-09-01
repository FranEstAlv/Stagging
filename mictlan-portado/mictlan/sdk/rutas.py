from __future__ import annotations

from pathlib import Path

# external_modules/ vive fuera de git (ver .gitignore) -- cualquier modulo
# ahi adentro se instala bajo el entendimiento de que no paso revision de
# codigo. Ver CONTRATO_SDK_MODULOS.md. Constante compartida por
# manifiestos.py y ciclo_vida.py -- vive en su propio archivo para que
# ninguno de los dos "sea dueño" del otro.
EXTERNAL_DIR = Path(__file__).resolve().parent.parent.parent / "external_modules"

__all__ = ["EXTERNAL_DIR"]
