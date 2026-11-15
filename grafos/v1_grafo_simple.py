"""Versión 1: grafo simple, sin LLM.

    START → clasificar ─┬─(eventos)───► responder_eventos ───► END
                        ├─(pedido)────► responder_pedido ────► END
                        ├─(politicas)─► responder_politicas ─► END
                        └─(otro)──────► responder_otro ──────► END

El estado es un TypedDict. `clasificar` detecta la intención con reglas
(palabras clave) y una arista condicional elige el nodo de respuesta fija.

Uso:  python -m grafos.v1_grafo_simple ["texto"]
"""

import re
import sys
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from grafos.comun import guardar_diagrama
from services.eventos import normalizar

Intencion = Literal["eventos", "pedido", "politicas", "otro"]


class EstadoV1(TypedDict, total=False):
    mensaje: str  # entrada del usuario
    intencion: Intencion  # la escribe `clasificar`
    respuesta: str  # la escribe el nodo de respuesta


# Reglas en orden de prioridad: la primera que encaja gana.
# Las palabras están normalizadas (minúsculas y sin tildes) y se buscan como prefijo de palabra,
# así "devol" encaja con "devolver" y "devolución".
_PATRON_ID_PEDIDO = re.compile(r"\beh-\d+\b")
REGLAS: list[tuple[Intencion, tuple[str, ...]]] = [
    ("pedido", ("pedido", "compra", "mi orden")),
    ("politicas", ("devol", "reembols", "titular", "cancel", "aplaz", "politica", "soporte")),
    ("eventos", ("evento", "concierto", "teatro", "entrada", "deporte", "partido",
                 "comedia", "monologo", "danza", "cartelera", "espectaculo")),
]

RESPUESTAS: dict[Intencion, str] = {
    "eventos": "Puedo ayudarte con eventos: dime la ciudad, el tipo de evento o el mes que te interesa.",
    "pedido": "Para consultar tu pedido necesito su identificador (p. ej. EH-1001) y el email de compra.",
    "politicas": "Puedes consultar nuestras políticas de devoluciones, cambio de titular y cancelaciones. "
                 "¿Sobre cuál tienes dudas?",
    "otro": "No he entendido tu consulta. Puedo ayudarte con eventos, pedidos y políticas de EventHub. "
            "También puedes escribir a soporte@eventhub.example.",
}


def detectar_intencion(mensaje: str) -> Intencion:
    texto = normalizar(mensaje)
    if _PATRON_ID_PEDIDO.search(texto):
        return "pedido"
    for intencion, palabras in REGLAS:
        if any(re.search(rf"\b{re.escape(p)}", texto) for p in palabras):
            return intencion
    return "otro"


# --- Nodos: reciben el estado y devuelven solo las claves que actualizan ----------

def clasificar(estado: EstadoV1) -> dict:
    return {"intencion": detectar_intencion(estado["mensaje"])}


def responder_eventos(estado: EstadoV1) -> dict:
    return {"respuesta": RESPUESTAS["eventos"]}


def responder_pedido(estado: EstadoV1) -> dict:
    return {"respuesta": RESPUESTAS["pedido"]}


def responder_politicas(estado: EstadoV1) -> dict:
    return {"respuesta": RESPUESTAS["politicas"]}


def responder_otro(estado: EstadoV1) -> dict:
    return {"respuesta": RESPUESTAS["otro"]}


# --- Arista condicional -------------------------------------------------------------

def ruta_por_intencion(estado: EstadoV1) -> Intencion:
    return estado["intencion"]


def construir_grafo():
    builder = StateGraph(EstadoV1)
    builder.add_node("clasificar", clasificar)
    builder.add_node("responder_eventos", responder_eventos)
    builder.add_node("responder_pedido", responder_pedido)
    builder.add_node("responder_politicas", responder_politicas)
    builder.add_node("responder_otro", responder_otro)

    builder.add_edge(START, "clasificar")
    # El diccionario traduce lo que devuelve la función de ruta al nombre del nodo destino;
    # además permite que el diagrama dibuje cada rama con su etiqueta.
    builder.add_conditional_edges(
        "clasificar",
        ruta_por_intencion,
        {
            "eventos": "responder_eventos",
            "pedido": "responder_pedido",
            "politicas": "responder_politicas",
            "otro": "responder_otro",
        },
    )
    for nodo in ("responder_eventos", "responder_pedido", "responder_politicas", "responder_otro"):
        builder.add_edge(nodo, END)
    return builder.compile()


EJEMPLOS = [
    "¿Qué conciertos hay en Valencia?",
    "¿Cómo va mi pedido EH-1001?",
    "¿Puedo devolver mis entradas?",
    "¿Qué tiempo hace hoy?",
]


def main() -> None:
    grafo = construir_grafo()
    for mensaje in sys.argv[1:] or EJEMPLOS:
        estado = grafo.invoke({"mensaje": mensaje})
        print(f"> {mensaje}\n  intención: {estado['intencion']}\n  respuesta: {estado['respuesta']}\n")
    print(f"Diagrama guardado en {guardar_diagrama(grafo, 'v1')}")


if __name__ == "__main__":
    main()
