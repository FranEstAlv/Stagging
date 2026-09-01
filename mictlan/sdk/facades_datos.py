from __future__ import annotations

from .. import almacen_modulos, datos

# DatosFacade (lectura de referencia) y AlmacenPropioFacade (persistencia
# escribible propia) viven juntas a proposito -- DatosFacade.db devuelve
# un AlmacenPropioFacade, y ambas giran alrededor del mismo tema ("de
# donde saca/guarda datos un modulo"), solo que con privilegios distintos
# (datos.leer_propio/datos.leer_compartido de solo lectura vs.
# datos.escribir_propio de lectoescritura).


class AlmacenPropioFacade:
    """Expuesto como contexto.datos.db -- resuelve el hueco de
    'contexto.db' (ver PROGRESO.md, GUIA_SDK_MODULOS_EXTERNOS.md): un
    archivo SQLite propio y privado por modulo (mictlan/almacen_modulos.py),
    async de verdad (aiosqlite, nunca bloquea el event loop), para que un
    modulo pueda recordar datos de sus usuarios entre restarts. Requiere el
    scope 'datos.escribir_propio' -- deliberadamente distinto de
    'datos.leer_propio' (ese es solo para los archivos de referencia que un
    admin coloca a mano, ver DatosFacade) porque son dos niveles de
    privilegio distintos: leer un CSV de catalogo no es lo mismo que poder
    crear/escribir tablas propias.

    Nota de nombres: el diseño original en GUIA_SDK_MODULOS_EXTERNOS.md
    proponia el scope 'db.propio', pero 'db.' esta en
    SCOPES_PREFIJOS_PELIGROSOS (bloqueado a proposito) -- de ahi el nombre
    real 'datos.escribir_propio', dentro del mismo namespace que los otros
    scopes de datos."""

    def __init__(self, contexto: "ContextoModulo"):
        self._contexto = contexto
        self._almacen = almacen_modulos.AlmacenModulo(contexto.module_id)

    def _check(self) -> None:
        self._contexto._requiere("datos.escribir_propio")

    async def execute(self, query: str, *args) -> None:
        self._check()
        await self._almacen.execute(query, *args)

    async def executescript(self, script: str) -> None:
        self._check()
        await self._almacen.executescript(script)

    async def fetch(self, query: str, *args):
        self._check()
        return await self._almacen.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        self._check()
        return await self._almacen.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        self._check()
        return await self._almacen.fetchval(query, *args)

    @property
    def bloqueo(self):
        self._check()
        return self._almacen.bloqueo


class DatosFacade:
    """Expuesto como contexto.datos -- lectura completa de archivos CSV o
    SQLite de referencia, sin importar el tamano (miles de filas no se
    truncan, ver mictlan/datos.py). Dos scopes separados porque son dos
    niveles de privilegio distintos:
      - datos.leer_propio: solo la carpeta del propio modulo, nadie mas
        la ve.
      - datos.leer_compartido: una carpeta general que cualquier modulo
        con este scope puede leer -- para catalogos que varios modulos
        necesitan consultar. Siempre solo lectura, nunca escritura.
    Para persistencia ESCRIBIBLE propia del modulo (sobrevive restarts),
    ver contexto.datos.db -- AlmacenPropioFacade, arriba, scope separado
    'datos.escribir_propio'."""

    def __init__(self, contexto: "ContextoModulo"):
        self._contexto = contexto

    def listar_propios(self) -> list[str]:
        self._contexto._requiere("datos.leer_propio")
        return datos.listar(datos.carpeta_propia(self._contexto.module_id))

    def leer_csv_propio(self, nombre_archivo: str) -> list[dict]:
        self._contexto._requiere("datos.leer_propio")
        ruta = datos.carpeta_propia(self._contexto.module_id) / nombre_archivo
        return datos.leer_csv(ruta)

    def abrir_sqlite_propio(self, nombre_archivo: str):
        self._contexto._requiere("datos.leer_propio")
        ruta = datos.carpeta_propia(self._contexto.module_id) / nombre_archivo
        return datos.abrir_sqlite_solo_lectura(ruta)

    def listar_compartidos(self) -> list[str]:
        self._contexto._requiere("datos.leer_compartido")
        return datos.listar(datos.carpeta_compartida())

    def leer_csv_compartido(self, nombre_archivo: str) -> list[dict]:
        self._contexto._requiere("datos.leer_compartido")
        ruta = datos.carpeta_compartida() / nombre_archivo
        return datos.leer_csv(ruta)

    def abrir_sqlite_compartido(self, nombre_archivo: str):
        self._contexto._requiere("datos.leer_compartido")
        ruta = datos.carpeta_compartida() / nombre_archivo
        return datos.abrir_sqlite_solo_lectura(ruta)

    @property
    def db(self) -> AlmacenPropioFacade:
        return AlmacenPropioFacade(self._contexto)


__all__ = ["DatosFacade", "AlmacenPropioFacade"]
