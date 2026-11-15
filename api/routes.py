"""Endpoints HTTP. Solo traducen HTTP ↔ funciones de llm/."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.schemas import (
    Confirmacion,
    MensajeChat,
    PreguntaPolitica,
    RespuestaChat,
    RespuestaPendiente,
    RespuestaTexto,
)
from config.settings import openai_api_key
from llm import agent
from llm.chain import responder_politica

router = APIRouter()

PAGINA_PRUEBA = Path(__file__).resolve().parent.parent / "static" / "index.html"
PAGINA_CHAT_LIBRE = PAGINA_PRUEBA.with_name("chat_libre.html")


def requiere_api_key() -> None:
    """Devuelve un error claro en vez de un 500 si falta la clave de OpenAI."""
    if not openai_api_key():
        raise HTTPException(503, "Falta OPENAI_API_KEY: copia .env.example a .env, pon tu clave y reinicia el servidor.")


@router.get("/", include_in_schema=False)
def pagina_prueba() -> FileResponse:
    """Página web sencilla para probar el chatbot desde el navegador."""
    return FileResponse(PAGINA_PRUEBA)


@router.get("/chat-libre", include_in_schema=False)
def pagina_chat_libre() -> FileResponse:
    """Página de prueba del chatbot sin mensajes de ejemplo: se escribe libremente."""
    return FileResponse(PAGINA_CHAT_LIBRE)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/politicas", response_model=RespuestaTexto, dependencies=[Depends(requiere_api_key)])
def politicas(body: PreguntaPolitica) -> RespuestaTexto:
    """Paso 1: responde sobre políticas usando solo la cadena LCEL (sin memoria)."""
    return RespuestaTexto(respuesta=responder_politica(body.pregunta))


def _respuesta(resultado: dict) -> RespuestaChat | RespuestaPendiente:
    if resultado.get("estado") == "pendiente_confirmacion":
        return RespuestaPendiente(**resultado)
    return RespuestaChat(**resultado)


@router.post("/chat", response_model=RespuestaChat | RespuestaPendiente, dependencies=[Depends(requiere_api_key)])
def chat(body: MensajeChat):
    """Pasos 2 y 3: agente con memoria por thread_id y herramientas.

    Si el agente quiere reservar, devuelve estado "pendiente_confirmacion" y hay
    que llamar a /chat/confirmar."""
    try:
        return _respuesta(agent.enviar_mensaje(body.thread_id, body.mensaje))
    except agent.ConfirmacionPendiente:
        raise HTTPException(409, "Hay una acción pendiente de confirmar en esta conversación: usa /chat/confirmar.")


@router.post("/chat/confirmar", response_model=RespuestaChat | RespuestaPendiente, dependencies=[Depends(requiere_api_key)])
def chat_confirmar(body: Confirmacion):
    """Aprueba o rechaza la acción pendiente y reanuda el agente."""
    try:
        return _respuesta(agent.confirmar(body.thread_id, body.aprobar))
    except agent.ConfirmacionNoPendiente:
        raise HTTPException(409, "No hay ninguna acción pendiente de confirmar en esta conversación.")
