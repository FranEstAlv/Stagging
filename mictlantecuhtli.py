from __future__ import annotations

import os

from dotenv import load_dotenv
from telegram.ext import Application

from mictlan import db
from mictlan.tecuhtli import install_tecuhtli

# Segundo bot, proceso completamente separado de main.py -- su propio
# token (MICTLANTECUHTLI_BOT_TOKEN), su propia Application, la misma
# DATABASE_URL compartida (nunca una API HTTP entre los dos, ver
# mictlan/tecuhtli/__init__.py). No necesita sdk/almacen_modulos/
# roles.asegurar_root -- eso es responsabilidad exclusiva de main.py.

load_dotenv()


async def _post_init(app: Application) -> None:
    await db.init_pool()


async def _post_shutdown(app: Application) -> None:
    await db.close_pool()


def main() -> None:
    token = os.environ["MICTLANTECUHTLI_BOT_TOKEN"]
    app = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    install_tecuhtli(app)
    app.run_polling()


if __name__ == "__main__":
    main()
