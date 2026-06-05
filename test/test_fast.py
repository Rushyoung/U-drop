import uvicorn
from fastapi import FastAPI
import asyncio
from fastapi.responses import FileResponse
import os
import sqlite3
from loguru import logger
from fastapi import Depends

conn = sqlite3.connect("test.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('''
    create table if not exists test(
               id TEXT primary key,
               value TEXT)
             ''')    

app = FastAPI()

def get_logger():
    return logger.bind(service = "test service")

@app.get("/add/{id}/{value}")
async def ad(id : str, value: str, log = Depends(get_logger)):
    new_msg = (id, value)
    log.info(f'add {id} {value}')
    try:
        cursor.execute('''
        insert into test(id, value) values (?, ?)
                    ''',
                    new_msg)
        conn.commit()
    except sqlite3.Error as e:
        log.error(e)
        return 400
    return 200


@app.get("/get")
async def root(log = Depends(get_logger)):
    log.info("view get")
    return conn.execute("select * from test").fetchall()
    


if __name__ == '__main__':
    
    uvicorn.run("test_fast:app")