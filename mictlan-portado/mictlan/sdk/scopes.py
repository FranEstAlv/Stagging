from __future__ import annotations

from .excepciones import PermisoNoConcedido

# Los permisos son scopes de acceso, nunca comandos ni roles -- leccion
# directa de los parches de ALFA-1 (R2.31.8.28.1 / .28.2): un manifest que
# mete "/comando" o un rol dentro de "permissions" se rechaza como
# desconocido, no se interpreta como scope valido.
#
# NOTA: "captcha.resolver" y "sms.usar" existieron como groundwork en
# mictlan-staging (contexto.captcha/contexto.sms) pero NO se portaron aca
# a proposito -- son decision abierta pendiente de Fernando (con que
# proveedor probar primero, un proveedor activo o varios a la vez, ver
# CONTRATO_SDK_MODULOS.md). Agregarlos cuando esa decision este tomada,
# no antes.
SCOPES_PERMITIDOS = {
    "usuarios.leer_rol",
    "usuarios.registrar",
    "mensajes.enviar",
    "proxy.usar",
    "datos.leer_propio",
    "datos.leer_compartido",
    "datos.escribir_propio",
    "canal.publicar",
    "creditos.leer_saldo",
    "creditos.cobrar",
}

# Prefijos bloqueados explicitamente, ademas de no estar en el allowlist de
# arriba -- doble barrera, mensaje de error mas claro para el caso comun.
SCOPES_PREFIJOS_PELIGROSOS = ("db.", "database.", "secrets.", "env.", "core.", "shell.", "system.")


def validar_permisos(module_id: str, declarados: list) -> set[str]:
    permisos: set[str] = set()
    for crudo in declarados:
        permiso = str(crudo or "").strip()
        if not permiso:
            continue
        if any(permiso.startswith(prefijo) for prefijo in SCOPES_PREFIJOS_PELIGROSOS):
            raise PermisoNoConcedido(
                f"Modulo '{module_id}' pide un scope peligroso, rechazado: {permiso}"
            )
        if permiso not in SCOPES_PERMITIDOS:
            raise PermisoNoConcedido(
                f"Modulo '{module_id}' pide un scope desconocido/no soportado: {permiso}"
            )
        permisos.add(permiso)
    return permisos


__all__ = ["SCOPES_PERMITIDOS", "SCOPES_PREFIJOS_PELIGROSOS", "validar_permisos"]
