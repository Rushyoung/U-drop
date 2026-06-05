from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

# 让 /static/* 能直接访问 test/ 目录（比如 /static/md5.js）
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent), name="static")

@app.get("/")
def g():
    return FileResponse(Path(__file__).resolve().parent / "test.html", media_type="text/html")