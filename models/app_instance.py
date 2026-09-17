import os

from flask import Flask

from .config import BASE_DIR


class RockApplication:
    """Crea y configura la aplicacion Flask."""

    def __init__(self):
        self.app = Flask(
            __name__,
            template_folder=str(BASE_DIR / "templates"),
            static_folder=str(BASE_DIR / "static"),
        )
        self.app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")
        self.app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


app = RockApplication().app
