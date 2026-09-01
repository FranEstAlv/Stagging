from __future__ import annotations

# Fachada del paquete -- todo caller (`from mictlan import sdk`,
# `sdk.activar_modulo(...)`, etc.) usa esta API sin conocer los
# submodulos internos, cada uno de una sola responsabilidad (ver
# CLAUDE.md, "Modularidad: nunca un core.py"):
#
#   excepciones.py     -- las 4 excepciones del SDK
#   scopes.py           -- SCOPES_PERMITIDOS/PREFIJOS_PELIGROSOS + validacion
#   rutas.py             -- EXTERNAL_DIR
#   facades_proxy.py      -- ProxyFacade
#   facades_creditos.py    -- CreditosFacade (asimetria deliberada, sin otorgar())
#   facades_datos.py        -- DatosFacade + AlmacenPropioFacade (contexto.datos.db)
#   facades_canal.py         -- CanalFacade
#   contexto.py                -- ContextoModulo (ensambla los facades)
#   manifiestos.py               -- leer/descubrir manifest.json
#   importador.py                 -- import dinamico del .py de un modulo
#   recorders.py                   -- wrappers de Application/job_queue
#   ciclo_vida.py                   -- activar/desactivar/eliminar/etc.
#
# contexto.captcha y contexto.sms NO existen todavia -- ver la nota en
# contexto.py y CONTRATO_SDK_MODULOS.md.

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
