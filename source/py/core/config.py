from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_ROOT:Path = Path(__file__).resolve().parents[3]
    DB_NAME:Path = PROJECT_ROOT / "udrop.db"
    DB_INIT:Path = PROJECT_ROOT / "test" / "init.sql"
    EXPIRE_TIME:int = 0
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")




settings = Settings()