"""Punto de entrada: crea la aplicación FastAPI.

La API se sirve en el puerto 9000:
    uvicorn main:app --reload --port 9000
    o bien:  python main.py
Documentación interactiva: http://127.0.0.1:9000/docs
"""

from fastapi import FastAPI

from api.routes import router

PUERTO = 9000

app = FastAPI(title="Asistente EventHub", version="1.0.0")
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=PUERTO, reload=True)
