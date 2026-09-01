from __future__ import annotations

import os

# Ver "Proxies salientes via DataImpulse (plan)" en CLAUDE.md -- un solo
# lugar que sabe como salir a internet via DataImpulse, para que ningun
# modulo (interno o externo) tenga que leer credenciales de proxy por su
# cuenta ni hardcodearlas.
#
# Lectura perezosa (dentro de la funcion, no a nivel de modulo) -- misma
# razon que ROOT_ID/ADMIN_GROUP_ID: load_dotenv() corre despues de los
# imports de nivel superior de main.py.


def obtener_proxy_url() -> str:
    return os.environ["DATAIMPULSE_PROXY_URL"]


def proxies_httpx() -> dict:
    url = obtener_proxy_url()
    return {"http://": url, "https://": url}
