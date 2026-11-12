from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = (BASE_DIR / "event_planner.db").as_posix()


class Settings(BaseSettings):
    APP_NAME: str = "University Event Planner API"
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
