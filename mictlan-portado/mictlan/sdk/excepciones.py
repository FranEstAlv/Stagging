from __future__ import annotations

# Excepciones propias del SDK de modulos externos -- archivo aparte para
# que cualquier otro submodulo de sdk/ las importe sin arrastrar el resto
# (loader, facades, etc.), evitando ciclos de import entre submodulos.


class ModuloInvalido(Exception):
    pass


class PermisoNoConcedido(Exception):
    pass


class ProxyNoConfigurado(Exception):
    pass


class PublicacionNoConfigurada(Exception):
    pass


__all__ = [
    "ModuloInvalido",
    "PermisoNoConcedido",
    "ProxyNoConfigurado",
    "PublicacionNoConfigurada",
]
