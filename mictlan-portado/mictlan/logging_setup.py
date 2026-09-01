from __future__ import annotations

import logging
import logging.handlers
import os

# Logging propio de Mictlan -- hoy el bot solo manda a stdout, capturado
# por journalctl via systemd, que rota/descarta segun la config del
# sistema, no de Mictlan. Este modulo agrega un RotatingFileHandler
# independiente para no perder historial si el journal rota o se llena,
# sin dejar de mandar tambien a consola (journalctl sigue viendo lo
# mismo que antes).
#
# Guarda contra duplicar handlers si configurar_logging() se llama mas de
# una vez en el mismo proceso -- mismo patron que OLIMPO/logging_setup.py
# (root.handlers: return), con la misma leccion aprendida ahi: sin esa
# guarda, un logger termina duplicando cada linea y abriendo un file
# descriptor nuevo sin limite.
#
# Ruta y nivel configurables por variable de entorno
# (MICTLAN_LOG_PATH/MICTLAN_LOG_LEVEL), leidas de forma perezosa (dentro
# de la funcion, no a nivel de modulo) -- mismo criterio que
# ROOT_ID/ADMIN_GROUP_ID en main.py.


class _RedactorToken(logging.Filter):
    """El logger de httpx/telegram puede loguear la URL completa de cada
    request a la API de Telegram, que trae el token del bot embebido
    (https://api.telegram.org/bot<TOKEN>/...) -- se redacta de cualquier
    linea antes de escribirla al archivo o a consola, sin importar el
    nivel configurado (mismo riesgo real que ya se identifico en el
    logging de mictlan-staging)."""

    def filter(self, record: logging.LogRecord) -> bool:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if token:
            texto = record.getMessage()
            if token in texto:
                record.msg = texto.replace(token, "***TOKEN***")
                record.args = ()
        return True


def configurar_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    ruta = os.environ.get("MICTLAN_LOG_PATH", "mictlan.log")
    nivel = os.environ.get("MICTLAN_LOG_LEVEL", "INFO").upper()

    formato = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    redactor = _RedactorToken()

    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    consola.addFilter(redactor)

    archivo = logging.handlers.RotatingFileHandler(
        ruta, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    archivo.setFormatter(formato)
    archivo.addFilter(redactor)

    root.setLevel(nivel)
    root.addHandler(consola)
    root.addHandler(archivo)


__all__ = ["configurar_logging"]
