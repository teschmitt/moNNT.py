from logging import Logger
from pathlib import Path

from pytimeparse2 import parse
from toml import load

from logger import global_logger

logger: Logger = global_logger()

try:
    toml_path: str = str(Path(__file__).resolve().parent / "config.toml")
    config = load(toml_path)
    try:
        config["bundles"]["lifetime"] = parse(config["bundles"]["lifetime"]) * 1000
    except TypeError:
        # pytimeparse2 returns None when string is not parseable so multiplication
        # will throw a TypeError
        config["bundles"]["lifetime"] = 86400000

except FileNotFoundError:
    logger.error("File 'config.toml' not found in backend root directory. Using defaults.")
    config = {
        "backend": {"db_url": "sqlite://db.sqlite3"},
        "dtnd": {
            "host": "http://127.0.0.1",
            "node_id": "dtn://n1/",
            "port": 3000,
            "rest_path": "",
            "ws_path": "/ws",
            "multi_user": False,
        },
        "backoff": {
            "initial_wait": 0.1,
            "max_retries": 20,
            "reconnection_pause": 300,
            "constant_wait": 0.75,
        },
        "bundles": {"lifetime": 86400000, "delivery_notification": False},
        "usenet": {
            "expiry_time": 86400000,
            "email": "none@none.com",
            "newsgroups": [
                "monntpy.users",
                "monntpy.dev",
                "monntpy.offtopic",
            ],
        },
    }
