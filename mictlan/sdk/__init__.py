from __future__ import annotations

# Fachada del paquete: mantiene exactamente la misma API publica que tenia
# el antiguo mictlan/sdk.py (818 lineas en un solo archivo) -- todo caller
# existente (`from mictlan import sdk`, `sdk.activar_modulo(...)`, etc.)
# sigue funcionando sin cambios. El contenido real vive repartido en
# submodulos de una sola responsabilidad cada uno (ver CLAUDE.md,
# "Modularidad: nunca un core.py"):
#
#   excepciones.py     -- las 4 excepciones del SDK
#   scopes.py           -- SCOPES_PERMITIDOS/PREFIJOS_PELIGROSOS + validacion
#   rutas.py             -- EXTERNAL_DIR
#   facades_externos.py   -- ProxyFacade/CaptchaFacade/SmsFacade
#   facades_creditos.py    -- CreditosFacade (asimetria deliberada, sin otorgar())
#   facades_datos.py        -- DatosFacade + AlmacenPropioFacade (contexto.db)
#   facades_canal.py         -- CanalFacade
#   contexto.py                -- ContextoModulo (ensambla los facades)
#   manifiestos.py               -- leer/descubrir manifest.json
#   importador.py                 -- import dinamico del .py de un modulo
#   recorders.py                   -- wrappers de Application/job_queue
#   ciclo_vida.py                   -- activar/desactivar/eliminar/etc.

from .ciclo_vida import (
    _handlers,
    _instalar_fn,
    _jobs,
    _loaded,
    activar_modulo,
    alternar_origen,
    desactivar_modulo,
    descubrir_e_instalar,
    eliminar_modulo,
    listar_modulos,
    obtener_modulo,
    sincronizar_registro,
)
from .contexto import ContextoModulo
from .excepciones import (
    ModuloInvalido,
    PermisoNoConcedido,
    ProxyNoConfigurado,
    PublicacionNoConfigurada,
)
from .facades_datos import AlmacenPropioFacade
from .manifiestos import obtener_manifest
from .rutas import EXTERNAL_DIR
from .scopes import SCOPES_PERMITIDOS

__all__ = [
    "ContextoModulo",
    "AlmacenPropioFacade",
    "ModuloInvalido",
    "PermisoNoConcedido",
    "ProxyNoConfigurado",
    "PublicacionNoConfigurada",
    "descubrir_e_instalar",
    "sincronizar_registro",
    "listar_modulos",
    "obtener_modulo",
    "obtener_manifest",
    "activar_modulo",
    "desactivar_modulo",
    "eliminar_modulo",
    "alternar_origen",
    "SCOPES_PERMITIDOS",
    "EXTERNAL_DIR",
]
