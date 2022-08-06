from typing import Optional

from pydantic import BaseSettings, Field


class GlobalSettings(BaseSettings):
    """Global configurations."""

    # define global variables with the Field class
    ENV_STATE: Optional[str] = Field(None, env="ENV_STATE")

    DB_URL: Optional[str] = None

    MAX_CONNECTIONS: Optional[int] = None
    # Server log file (you can use shell environment variables)
    LOG_FILE: Optional[str] = None
    # Domain name
    DOMAIN_NAME: Optional[str] = None
    # Host name to bind to (will also be used in NNTP responses and headers)
    NNTP_HOSTNAME: Optional[str] = None
    # Port to listen on
    NNTP_PORT: Optional[int] = None
    # type of server ('read-only' or 'read-write')
    SERVER_TYPE: Optional[str] = None
    # authentication settings ('yes' or 'no')
    NNTP_AUTH: Optional[str] = None
    # authentication backend that papercut will use to authenticate the users.
    AUTH_BACKEND: Optional[str] = None

    # cache settings

    # whether to enable the cache system (may need a lot of diskspace). Valid
    # choices are 'yes' or 'no'.
    NNTP_CACHE: Optional[str] = None
    # Cache expiration interval (in seconds)
    NNTP_CACHE_EXPIRE: Optional[int] = None
    # Path to the directory where the cache should be kept (you can use shell
    # environment variables)
    NNTP_CACHE_PATH: Optional[str] = None

    # server behavior
    MAX_EMPTY_REQUESTS: Optional[int] = 10

    class Config:
        """Loads the dotenv file."""

        env_file: str = ".env"


class DevSettings(GlobalSettings):
    """Development configurations."""

    class Config:
        env_file: str = "dev.env"


class ProdSettings(GlobalSettings):
    """Production configurations."""

    class Config:
        env_file: str = "prod.env"


class SettingsFactory:
    """Returns a config instance dependending on the ENV_STATE variable."""

    def __init__(self, env_state: Optional[str]):
        self.env_state = env_state

    def __call__(self):
        if self.env_state == "dev":
            return DevSettings()

        elif self.env_state == "prod":
            return ProdSettings()


settings = SettingsFactory(GlobalSettings().ENV_STATE)()

TORTOISE_ORM = {
    "connections": {"default": settings.DB_URL},
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
