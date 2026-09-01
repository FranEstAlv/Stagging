from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from mictlan import almacen_modulos, db, heartbeat, moderacion, roles, sdk, vencimientos
from mictlan.mensajes import enviar_mensaje_servicio, install_mensajes
from mictlan.modules.canales import install_canales
from mictlan.modules.creditos import install_creditos
from mictlan.modules.grupos import install_grupos
from mictlan.modules.mando import install_mando
from mictlan.modules.mando.baneo import install_baneo
from mictlan.modules.perfil import install_perfil
from mictlan.modules.reporte import install_reporte

load_dotenv()

# Logging propio, exclusivo de esta copia de staging -- no existe en la
# produccion real (ver "Logging propio de Mictlan (plan)" en CLAUDE.md).
# Va a stdout, que systemd vuelca al journal (visible con
# journalctl -u mictlan-staging.service, sin sudo, service es User=olimpo).
#
# Nivel TRACE (mas verboso que DEBUG) para ver tambien el detalle de red de
# httpx/httpcore/telegram -- eso incluye la URL completa de cada request a
# la API de Telegram, que trae el token del bot embebido
# (https://api.telegram.org/bot<TOKEN>/...). El filtro de abajo lo redacta
# de cualquier linea de log antes de escribirla al journal.
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


class _RedactorToken(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if _TOKEN:
            texto = record.getMessage()
            if _TOKEN in texto:
                record.msg = texto.replace(_TOKEN, "***TOKEN***")
                record.args = ()
        return True


_handler = logging.StreamHandler()
_handler.addFilter(_RedactorToken())
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.basicConfig(level=TRACE, handlers=[_handler])
logger = logging.getLogger("mictlan-staging")

START_MENSAJE = "Bienvenido a Mictlan."


async def _log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    mensaje = update.effective_message
    query = update.callback_query
    logger.info(
        "chat_id=%s chat_type=%s user_id=%s username=%s texto=%r callback=%r",
        chat.id if chat else None,
        chat.type if chat else None,
        user.id if user else None,
        user.username if user else None,
        mensaje.text if mensaje else None,
        query.data if query else None,
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message:
        await enviar_mensaje_servicio(context, message.chat_id, START_MENSAJE)


async def _post_init(app: Application) -> None:
    await db.init_pool()
    await roles.asegurar_root(int(os.environ["ROOT_ID"]))
    await sdk.descubrir_e_instalar(app)


async def _post_shutdown(app: Application) -> None:
    await almacen_modulos.cerrar_todas()
    await db.close_pool()


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", start_command))
    install_mensajes(app)
    install_perfil(app)
    # install_baneo ANTES de install_mando: su ConversationHandler y su
    # CallbackQueryHandler de "ver reporte" necesitan interceptar
    # "mando:usuarios:banear:..."/"mando:usuarios:reporte:..." antes de
    # que el router generico de /mando (pattern "^mando:") los reciba --
    # dentro del mismo grupo de handlers, PTB solo corre el primero que
    # matchea. Ver modules/mando/baneo.py.
    install_baneo(app)
    install_mando(app)
    install_reporte(app)
    install_grupos(app)
    install_creditos(app)
    install_canales(app)
    moderacion.install_moderacion(app)
    vencimientos.install_vencimientos(app)
    heartbeat.install_heartbeat(app)
    # Observador de solo lectura -- grupo aparte, no interfiere con los
    # handlers reales de arriba.
    app.add_handler(MessageHandler(filters.ALL, _log_update), group=-1)
    app.add_handler(CallbackQueryHandler(_log_update, pattern=".*"), group=-1)
    logger.info("Mictlan (staging) arrancando...")
    # allowed_updates=ALL_TYPES es necesario para que lleguen los eventos
    # "chat_member" (miembro cualquiera entrando a un grupo gestionado,
    # ver moderacion.py) -- a diferencia de "my_chat_member" (alta del
    # BOT, usado en modules/grupos.py), Telegram NO manda "chat_member"
    # por defecto si no se pide explicitamente.
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
