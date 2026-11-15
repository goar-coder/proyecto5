"""Recorte del historial que se envía al modelo."""

from collections.abc import Sequence

from langchain_core.messages import BaseMessage, ToolMessage

MAX_MENSAJES = 10


def recortar_historial(mensajes: Sequence[BaseMessage], maximo: int = MAX_MENSAJES) -> list[BaseMessage]:
    """Devuelve como mucho los últimos `maximo` mensajes.

    Si el corte deja al principio uno o más ToolMessage, su AIMessage con
    `tool_calls` se ha quedado fuera; la API de OpenAI rechaza esos mensajes
    huérfanos. En ese caso se avanza el corte hasta el primer mensaje que no
    sea de herramienta (se envían menos de `maximo`, nunca más).
    """
    if maximo <= 0:
        return []
    ventana = list(mensajes[-maximo:])
    inicio = 0
    while inicio < len(ventana) and isinstance(ventana[inicio], ToolMessage):
        inicio += 1
    return ventana[inicio:]
