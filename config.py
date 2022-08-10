from logging import Logger
from pathlib import Path

from toml import load

from logger import global_logger

"""
This file will load the server configuration depending on the environment settings in the
pyproject.toml.
Following settings are possible:
  - "dev": development environment, this will load config.dev.toml
  - "prod": production environment, this will load config.prod.toml
  - "test": testing environment, this will load config.test.toml
"""


logger: Logger = global_logger()

try:
    pyproject_toml_path: str = str(Path(__file__).resolve().parent / "pyproject.toml")
    pyproject_config = load(pyproject_toml_path)
except FileNotFoundError:
    logger.error(
        "File 'pyproject.toml' not found in same directory as config.py. This error is fatal,"
        " please fix."
    )
    raise

env = pyproject_config["monntpy"]["env"]
try:
    config_toml_path: str = str(Path(__file__).resolve().parent / f"config.{env}.toml")
    server_config = load(config_toml_path)
except FileNotFoundError:
    logger.error(
        f"config.{env}.toml not found in same directory as config.py. This error is fatal,"
        " please fix either the setting in pyproject.toml or the filesystem."
    )
