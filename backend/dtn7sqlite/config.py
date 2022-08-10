from logging import Logger
from pathlib import Path

from toml import load

from logger import global_logger

logger: Logger = global_logger()

try:
    toml_path: str = str(Path(__file__).resolve().parent / "config.toml")
    config = load(toml_path)
except FileNotFoundError:
    logger.error("File 'config.toml' not found in backend root directory. Using defaults.")
    config = {
        "backend": {"db_url": "sqlite://db.sqlite3"},
        "dtnd": {
            "host": "http://127.0.0.1",
            "port": 3000,
            "rest_path": "",
            "ws_path": "/ws",
            "multi_user": False,
        },
        "backoff": {
            "initial_wait": 0.1,
            "max_retries": 20,
            "reconn_pause": 300,
            "constant_wait": 0.75,
        },
        "bundles": {"lifetime": 86400000, "delivery_notification": False},
        "usenet": {
            "expiry_time": 86400000,
            "email": "t.e.schmitt@posteo.de",
            "newsgroups": [
                "eval.core.monntpy",
                "monntpy.usersgermany.hessen.darmstadt.darmstadt",
                "germany.hessen.darmstadt-dieburg.dieburg",
                "germany.hessen.darmstadt-dieburg.rossdorf",
            ],
        },
    }


TORTOISE_ORM = {
    "connections": {"default": config["backend"]["db_url"]},
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
