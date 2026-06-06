import os
import sys
import time
from pathlib import Path
from db.connection import open_connection
from core.config import settings
from core.logger import logger

def initialize_database(conn=None) -> None:
    """
    微型数据库迁移引擎 (方案B) - 修复老库过渡逻辑
    """
    if conn is None:
        conn = open_connection()
        should_close = True
    else:
        should_close = False

    try:
        logger.debug("--- 数据库迁移引擎启动 ---")

        # 1. 建立迁移管理表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at INTEGER NOT NULL
            )
        """)
        conn.commit()

        # 2. 检查底座状态 (V0)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table_exists = cursor.fetchone()

        if not users_table_exists:
            logger.info("检测到全新数据库，正在铺设 V0 底座 (init.sql)...")
            with open(settings.DB_INIT, "r", encoding="utf-8") as f:
                sqlscript = f.read()
            conn.executescript(sqlscript)
            conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", 
                         ("000_init", int(time.time())))
            conn.commit()
            logger.success("V0 底座铺设完成。")
        else:
            # --- 【关键修复：处理老库过渡】 ---
            cursor = conn.execute("SELECT COUNT(*) FROM schema_migrations")
            if cursor.fetchone()[0] == 0:
                logger.info("检测到存量数据库，正在自动标记基准版本 (000_init)...")
                conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", 
                             ("000_init", int(time.time())))
                conn.commit()
            logger.debug("数据库底座已就绪。")

        # 3. 审计已执行的版本
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY applied_at ASC")
        applied_versions = [row[0] for row in cursor.fetchall()]
        logger.info(f"当前数据库版本: {applied_versions[-1] if applied_versions else 'Unknown'}")

        # 4. 扫描并执行增量
        if not settings.MIGRATIONS_DIR.exists():
            settings.MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

        migration_files = sorted([f for f in os.listdir(settings.MIGRATIONS_DIR) if f.endswith(".sql")])
        
        new_count = 0
        for filename in migration_files:
            if filename in applied_versions:
                logger.debug(f"迁移脚本已在记录中，跳过: {filename}")
                continue
            
            logger.info(f"发现未同步改动，正在应用增量: {filename} ...")
            file_path = settings.MIGRATIONS_DIR / filename
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                
                start_time = time.perf_counter()
                conn.execute("BEGIN TRANSACTION")
                conn.executescript(sql_content)
                conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", 
                             (filename, int(time.time())))
                conn.commit()
                duration = (time.perf_counter() - start_time) * 1000
                logger.success(f"增量脚本 {filename} 应用成功! (耗时: {duration:.2f}ms)")
                new_count += 1
            except Exception as e:
                conn.rollback()
                logger.critical(f"!!! 迁移严重故障: {filename} 执行失败 !!! 错误原因: {e}")
                raise e

        if new_count > 0:
            logger.info(f"数据库升级完毕，共应用 {new_count} 个增量脚本。")
        else:
            logger.debug("数据库已是最新状态，无需应用增量。")

    finally:
        if should_close:
            conn.close()
            # 安全加固：设置数据库文件权限 (仅所有者读写)
            try:
                if sys.platform == "win32":
                    logger.info(f"初始化 | Windows 环境跳过权限设置")
                else:
                    for suffix in ("", "-wal", "-shm"):
                        db_file = str(settings.DB_NAME) + suffix
                        if os.path.exists(db_file):
                            os.chmod(db_file, 0o600)
                    logger.info(f"初始化 | 数据库权限已加固: {settings.DB_NAME}")
            except Exception as e:
                logger.warning(f"初始化 | 无法设置数据库文件权限: {e}")
        logger.debug("--- 数据库迁移引擎工作结束 ---")
