"""Modelos de entrada/salida de la API."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class PreguntaPolitica(BaseModel):
    pregunta: str = Field(..., min_length=1, examples=["¿Cuál es la política de devoluciones?"])


class RespuestaTexto(BaseModel):
    respuesta: str


class MensajeChat(BaseModel):
    thread_id: str = Field(..., min_length=1, examples=["conversacion-1"])
    mensaje: str = Field(..., min_length=1, examples=["¿Qué conciertos hay en Valencia?"])


class Confirmacion(BaseModel):
    thread_id: str = Field(..., min_length=1, examples=["conversacion-1"])
    aprobar: bool


class LlamadaHerramienta(BaseModel):
    nombre: str
    argumentos: dict[str, Any]


class AccionPendiente(BaseModel):
    accion: str
    argumentos: dict[str, Any]


class RespuestaChat(BaseModel):
    respuesta: str
    herramientas: list[LlamadaHerramienta] = []


class RespuestaPendiente(BaseModel):
    estado: Literal["pendiente_confirmacion"] = "pendiente_confirmacion"
    accion: str
    argumentos: dict[str, Any]
    acciones: list[AccionPendiente] = []
    herramientas: list[LlamadaHerramienta] = []
