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
        "dtnd": {
            "host": "http://127.0.0.1",
            "port": 3000,
            "rest_path": "",
            "ws_path": "/ws",
        },
        "bundles": {"lifetime": "86400000", "deliv_notification": "false"},
    }
