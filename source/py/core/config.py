from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
    DB_NAME: Path = PROJECT_ROOT / "udrop.db"
    DB_INIT: Path = PROJECT_ROOT / "test" / "init.sql"
    
    # 动态库与存储路径
    LIB_DIR: Path = PROJECT_ROOT / "lib"
    STORAGE_ROOT: Path = PROJECT_ROOT / "storage"
    THUMBNAIL_ROOT: Path = STORAGE_ROOT / "thumbnails"
    
    EXPIRE_TIME: int = 0
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")




settings = Settings()