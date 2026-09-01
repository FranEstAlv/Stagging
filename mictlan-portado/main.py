from __future__ import annotations

import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from mictlan import almacen_modulos, db, heartbeat, logging_setup, moderacion, roles, sdk, vencimientos
from mictlan.mensajes import enviar_mensaje_servicio, install_mensajes
from mictlan.modules.canales import install_canales
from mictlan.modules.creditos import install_creditos
from mictlan.modules.grupos import install_grupos
from mictlan.modules.mando import install_mando
from mictlan.modules.mando.baneo import install_baneo
from mictlan.modules.perfil import install_perfil
from mictlan.modules.reporte import install_reporte

load_dotenv()
# Despues de load_dotenv(): MICTLAN_LOG_PATH/MICTLAN_LOG_LEVEL pueden
# venir del .env, no solo del entorno real del proceso.
logging_setup.configurar_logging()

START_MENSAJE = "Bienvenido a Mictlan."


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
    # allowed_updates=ALL_TYPES es necesario para que lleguen los eventos
    # "chat_member" (miembro cualquiera entrando a un grupo gestionado,
    # ver moderacion.py) -- a diferencia de "my_chat_member" (alta del
    # BOT, usado en modules/grupos.py), Telegram NO manda "chat_member"
    # por defecto si no se pide explicitamente.
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
