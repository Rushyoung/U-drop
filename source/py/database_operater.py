import sqlite3
from core.config import settings

DB_NAME = settings.DB_NAME
DB_INIT = settings.DB_INIT
conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
with open(DB_INIT, 'r', encoding='utf-8') as f:
    sqlscript = f.read() 
conn.executescript(sqlscript)
try:
    while True:
        sql = input('sql> ').strip()
        if sql.lower() in ('exit', 'quit'):
            break
        if not sql:
            continue
        cur.execute(sql)
        if sql.lstrip().upper().startswith('SELECT'):
            for row in cur.fetchall():
                print(row)
        else:
            conn.commit()
            print(f"OK, {cur.rowcount} row(s)")
except Exception as e:
    print("错误：", e)
finally:
    cur.close()
    conn.close()

