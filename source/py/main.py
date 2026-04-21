import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.router import router
from core.exceptions import UdropException
from contextlib import asynccontextmanager

from db.bootstrap import initialize_database


@asynccontextmanager
async def lifespan(app:FastAPI):
    initialize_database()
    yield

app = FastAPI(lifespan=lifespan)

@app.exception_handler(UdropException)
def udrop_exception_handler(req:Request, exc:UdropException):
    return JSONResponse(
        status_code = exc.code,
        content={
            "success": "False",
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )


app.include_router(router, prefix="/api/v1")



if __name__ == '__main__':
    uvicorn.run("main:app", reload= True)


