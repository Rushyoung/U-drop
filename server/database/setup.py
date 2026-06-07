from database.connect import Database
from database.models import ALL_MODELS, SysSetting
from core.logger import logger


def setup():
    db = Database()
    db.connect(reuse_if_open=True)
    db.execute_sql("PRAGMA journal_mode=WAL;")
    db.execute_sql("PRAGMA foreign_keys = ON;")
    db.execute_sql("PRAGMA busy_timeout = 5000;")

    cursor = db.execute_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    )
    users_table_exists = cursor.fetchone()

    if not users_table_exists:
        logger.info("检测到全新数据库，正在铺设底座...")
        db.create_tables(ALL_MODELS)
        SysSetting.insert(key="allow_registration", value="true").execute()
        SysSetting.insert(key="auth_rate_limit", value="5").execute()
        SysSetting.insert(key="default_token_expire", value="86400").execute()
        logger.success("底座铺设完成。")
    else:
        db.create_tables(ALL_MODELS)
        logger.debug("数据库底座已就绪。")

    logger.info("数据库初始化完成。")
