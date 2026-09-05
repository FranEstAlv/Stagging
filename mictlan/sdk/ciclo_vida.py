from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .. import db
from .contexto import ContextoModulo
from .excepciones import ModuloInvalido
from .importador import desregistrar_ruta, importar_modulo
from .manifiestos import descubrir_manifiestos, leer_manifest
from .recorders import AppRecorder
from .rutas import EXTERNAL_DIR
from .scopes import validar_permisos

logger = logging.getLogger("mictlan.sdk")

# Guardia contra reimportacion repetida -- mismo patron que sdk.py de
# OLIMPO. Acotado por la cantidad de modulos instalados (finito, controlado
# por un admin), no por input de usuario -- no es el anti-patron de cache
# sin limite que advierte CLAUDE.md.
# module_id -> modulo Python ya importado (se reusa entre activar/desactivar
# repetidos, nunca se reimporta el .py del disco dos veces en el mismo
# proceso).
_loaded: dict[str, Any] = {}
# module_id -> la funcion install_modulo(app, contexto) ya resuelta, para
# poder volver a llamarla en un reactivar sin reimportar.
_instalar_fn: dict[str, Any] = {}
# module_id -> [(handler, group), ...] agregados por ESE modulo en la
# instalacion mas reciente -- lo que activar/desactivar_modulo agrega y
# quita del Application. Se reemplaza entero en cada (re)instalacion, nunca
# crece sin limite.
_handlers: dict[str, list[tuple[Any, int]]] = {}
# module_id -> [Job, ...] programados por ESE modulo via contexto/app.job_queue
# en la instalacion mas reciente -- para poder cancelarlos (schedule_removal)
# al desactivar. Un modulo sin jobs simplemente no aparece acá.
_jobs: dict[str, list[Any]] = {}


async def sincronizar_registro() -> list[str]:
    """Registra en sdk_modulos cualquier modulo nuevo encontrado en disco
    que todavia no tenga fila -- SIEMPRE inactivo por defecto (activo=0),
    para que la sola presencia del .py en external_modules/ nunca alcance
    para que corra: alguien lo tiene que activar a proposito desde la
    seccion Modulos de /mando. Nunca toca una fila que ya existe (no pisa
    activo/origen de un modulo ya conocido). Devuelve los module_id nuevos,
    para feedback en la UI."""
    manifiestos = descubrir_manifiestos()
    if not manifiestos:
        return []
    pool = db.get_pool()
    nuevos: list[str] = []
    async with pool.acquire() as conn:
        for manifest in manifiestos:
            module_id = str(manifest["module_id"])
            existente = await conn.fetchrow(
                "SELECT module_id FROM sdk_modulos WHERE module_id = $1", module_id
            )
            if existente is not None:
                continue
            await conn.execute(
                "INSERT INTO sdk_modulos (module_id, nombre, origen, activo) VALUES ($1, $2, $3, $4)",
                module_id,
                str(manifest.get("nombre", module_id)),
                "externo",
                False,
            )
            nuevos.append(module_id)
    return nuevos


async def listar_modulos() -> list[dict]:
    """Metadata de todos los modulos registrados, activos e inactivos --
    para la seccion Modulos dentro de /mando. Suma 'en_disco' (si la
    carpeta sigue en external_modules/) y 'cargado' (si esta importado en
    este proceso ahora mismo) -- ninguno de los dos viene de sdk_modulos,
    se calculan al vuelo."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        filas = await conn.fetch("SELECT * FROM sdk_modulos ORDER BY nombre")
    resultado = []
    for fila in filas:
        d = dict(fila)
        d["en_disco"] = (EXTERNAL_DIR / d["module_id"]).is_dir()
        d["cargado"] = d["module_id"] in _loaded
        resultado.append(d)
    return resultado


async def obtener_modulo(module_id: str) -> dict | None:
    """Igual que listar_modulos() pero para uno solo -- vista de detalle."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow("SELECT * FROM sdk_modulos WHERE module_id = $1", module_id)
    if fila is None:
        return None
    d = dict(fila)
    d["en_disco"] = (EXTERNAL_DIR / module_id).is_dir()
    d["cargado"] = module_id in _loaded
    return d


def _quitar_handlers_jobs(app, module_id: str) -> None:
    """Saca del Application cualquier handler/job que este modulo tuviera
    agregado de una instalacion anterior. Factoreado aparte de
    desactivar_modulo() para que _instalar_o_reinstalar() lo pueda llamar
    tambien ANTES de instalar -- asi activar_modulo() queda idempotente:
    si se lo llama dos veces seguidas sin pasar por desactivar en el medio
    (ej. dos admins clickeando "Activar" casi al mismo tiempo), la segunda
    llamada limpia la primera tanda de handlers en vez de dejarla huerfana
    y sin referencia en _handlers (bug real, encontrado 2026-09-05: antes
    _handlers[module_id] se pisaba entero con la tanda nueva, perdiendo la
    unica referencia que permitia sacar la tanda vieja del Application)."""
    for handler, group in _handlers.pop(module_id, []):
        try:
            app.remove_handler(handler, group)
        except (KeyError, ValueError):
            pass  # ya no estaba agregado -- no es un error real
    for job in _jobs.pop(module_id, []):
        job.schedule_removal()


async def _instalar_o_reinstalar(app, module_id: str, carpeta: Path, permisos: set[str]) -> None:
    """Corre install_modulo(app, contexto) grabando los handlers/jobs
    nuevos en _handlers/_jobs. Reusa el modulo ya importado si existe --
    activar/desactivar/activar de vuelta NUNCA reimporta el .py del disco,
    solo la primera vez que se activa en este proceso."""
    if module_id not in _loaded:
        manifest = leer_manifest(carpeta)
        mod, instalar_fn = importar_modulo(module_id, manifest["entrypoint"], carpeta)
        _loaded[module_id] = mod
        _instalar_fn[module_id] = instalar_fn
    instalar_fn = _instalar_fn[module_id]
    _quitar_handlers_jobs(app, module_id)  # idempotencia -- ver docstring de arriba
    contexto = ContextoModulo(module_id, permisos)
    handlers: list = []
    jobs: list = []
    recorder = AppRecorder(app, handlers, jobs)
    instalar_fn(recorder, contexto)
    _handlers[module_id] = handlers
    _jobs[module_id] = jobs


async def activar_modulo(app, module_id: str) -> None:
    """Instala (o reinstala) los handlers/jobs del modulo y lo marca activo
    en sdk_modulos. No hace falta reiniciar el proceso -- toma efecto de
    inmediato en el Application que ya esta corriendo."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow("SELECT module_id FROM sdk_modulos WHERE module_id = $1", module_id)
    if fila is None:
        raise ModuloInvalido(f"'{module_id}' no esta registrado -- corré '🔍 Detectar módulos' primero")
    carpeta = EXTERNAL_DIR / module_id
    if not carpeta.is_dir():
        raise ModuloInvalido(f"'{module_id}' ya no tiene carpeta en external_modules/, no se puede activar")
    manifest = leer_manifest(carpeta)
    permisos = validar_permisos(module_id, manifest.get("permissions", []))
    await _instalar_o_reinstalar(app, module_id, carpeta, permisos)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE sdk_modulos SET activo = $1 WHERE module_id = $2", True, module_id)
    logger.info("modulo activado: %s (permisos=%s)", module_id, sorted(permisos))


async def desactivar_modulo(app, module_id: str) -> None:
    """Quita del Application los handlers/jobs que ese modulo tenia
    agregados y lo marca inactivo. El modulo sigue importado en memoria
    (para poder reactivarlo rapido sin releer el .py), simplemente deja de
    responder a nada hasta que se reactive."""
    _quitar_handlers_jobs(app, module_id)
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE sdk_modulos SET activo = $1 WHERE module_id = $2", False, module_id)
    logger.info("modulo desactivado: %s", module_id)


async def eliminar_modulo(app, module_id: str) -> None:
    """Desregistra el modulo por completo: le quita handlers/jobs si
    estaba activo, lo borra de sdk_modulos y de la memoria del proceso.
    NUNCA borra la carpeta de external_modules/ -- si el .py sigue en
    disco, '🔍 Detectar módulos' lo va a volver a encontrar como nuevo
    (inactivo por defecto) la proxima vez que se corra ese escaneo."""
    await desactivar_modulo(app, module_id)
    _loaded.pop(module_id, None)
    _instalar_fn.pop(module_id, None)
    desregistrar_ruta(EXTERNAL_DIR / module_id)  # sys.path no debe crecer para siempre con modulos ya eliminados
    pool = db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM sdk_modulos WHERE module_id = $1", module_id)
    logger.info("modulo eliminado del registro: %s", module_id)


async def alternar_origen(module_id: str) -> str:
    """Cambia solo la etiqueta origen interno/externo en sdk_modulos --
    NO mueve archivos ni cambia como el SDK descubre/instala el modulo
    (sigue viviendo en external_modules/ de todas formas, sigue
    cargandose por el mismo loader). Sirve para marcar en el panel cuales
    modulos de prueba ya se consideran 'graduados' y candidatos a
    portarse a mano a mictlan/modules/ del repo real. Devuelve el origen
    nuevo."""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        fila = await conn.fetchrow("SELECT origen FROM sdk_modulos WHERE module_id = $1", module_id)
        if fila is None:
            raise ModuloInvalido(f"'{module_id}' no esta registrado")
        nuevo = "interno" if fila["origen"] == "externo" else "externo"
        await conn.execute("UPDATE sdk_modulos SET origen = $1 WHERE module_id = $2", nuevo, module_id)
    return nuevo


async def descubrir_e_instalar(app) -> None:
    """Se llama una vez al arrancar la app (post_init, despues de
    db.init_pool()). Primero registra en sdk_modulos cualquier modulo
    nuevo encontrado en disco (inactivo por defecto, ver
    sincronizar_registro), despues instala los que ya estan marcados
    activos. Un modulo roto no debe tumbar el arranque del bot -- se omite
    y queda logueado. Activar/desactivar/eliminar en caliente se hace
    despues desde la seccion Modulos de /mando, sin reiniciar el proceso."""
    nuevos = await sincronizar_registro()
    if nuevos:
        logger.info("modulos nuevos detectados (inactivos por defecto): %s", ", ".join(nuevos))
    pool = db.get_pool()
    async with pool.acquire() as conn:
        activos = await conn.fetch("SELECT module_id FROM sdk_modulos WHERE activo = $1", True)
    for fila in activos:
        module_id = fila["module_id"]
        carpeta = EXTERNAL_DIR / module_id
        if not carpeta.is_dir():
            logger.warning("modulo '%s' activo en DB pero sin carpeta en disco, omitido", module_id)
            continue
        try:
            manifest = leer_manifest(carpeta)
            permisos = validar_permisos(module_id, manifest.get("permissions", []))
            await _instalar_o_reinstalar(app, module_id, carpeta, permisos)
            logger.info("modulo externo instalado: %s (permisos=%s)", module_id, sorted(permisos))
        except Exception:
            logger.exception("No se pudo instalar el modulo '%s'", module_id)


__all__ = [
    "sincronizar_registro",
    "listar_modulos",
    "obtener_modulo",
    "activar_modulo",
    "desactivar_modulo",
    "eliminar_modulo",
    "alternar_origen",
    "descubrir_e_instalar",
]
