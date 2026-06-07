from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
    DB_NAME: Path = PROJECT_ROOT / "udrop.db"
    DB_INIT: Path = PROJECT_ROOT / "backend" / "sql" / "00_init_v2.sql"
    MIGRATIONS_DIR: Path = PROJECT_ROOT / "backend" / "sql" / "migrations"
    
    # 动态库与存储路径
    LIB_DIR: Path = PROJECT_ROOT / "lib"
    STORAGE_ROOT: Path = PROJECT_ROOT / "storage"
    THUMBNAIL_ROOT: Path = STORAGE_ROOT / "thumbnails"
    FRONTEND_DIST_DIR: Path = PROJECT_ROOT / "frontend" / "dist"
    
    EXPIRE_TIME: int = 0
    TRASH_EXPIRE_TIME: int = 90 #day
    
    # 初始自举配置
    ADMIN_ACCOUNT: Optional[str] = Field(None, env="ADMIN_ACCOUNT")
    ADMIN_PASSWORD: Optional[str] = Field(None, env="ADMIN_PASSWORD")
    
    # 系统动态配置默认值
    ALLOW_REGISTRATION: bool = True
    
    # 启动配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # 日志等级: DEBUG, INFO, WARNING, ERROR, SUCCESS
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")




settings = Settings()