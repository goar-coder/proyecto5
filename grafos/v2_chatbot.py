"""Versión 2: chatbot.

    START → chatbot → END

El estado es MessagesState: una sola clave `messages` con el reducer
`add_messages`, que AÑADE los mensajes que devuelve cada nodo en vez de
sustituir la lista. El nodo `chatbot` llama al modelo con el prompt de sistema
de EventHub (reglas + políticas) delante del historial.

Aún no hay checkpointer: el grafo no recuerda nada entre invocaciones. Para
poder conversar, el bucle de terminal guarda el estado devuelto y lo vuelve a
pasar en la siguiente llamada (en la v3 eso lo hará el checkpointer).

Uso:  python -m grafos.v2_chatbot
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from grafos.comun import prompt_sistema
from llm.models import crear_modelo


def crear_builder(modelo=None) -> StateGraph:
    """Grafo START → chatbot → END sin compilar (la v3 lo compila con checkpointer)."""
    modelo = modelo or crear_modelo()
    mensaje_sistema = SystemMessage(prompt_sistema(con_herramientas=False))

    def chatbot(estado: MessagesState) -> dict:
        # El mensaje de sistema no se guarda en el estado: se antepone en cada llamada.
        respuesta = modelo.invoke([mensaje_sistema, *estado["messages"]])
        return {"messages": [respuesta]}  # add_messages lo añade al historial

    builder = StateGraph(MessagesState)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder


def construir_grafo(modelo=None):
    return crear_builder(modelo).compile()


def main() -> None:
    grafo = construir_grafo()
    estado: dict = {"messages": []}
    print("Chatbot EventHub (v2, sin checkpointer). Escribe 'salir' para terminar.")
    while True:
        try:
            texto = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if texto.lower() in {"salir", "exit", "quit"}:
            break
        if not texto:
            continue
        # Sin checkpointer, el historial lo arrastramos nosotros: pasamos los mensajes
        # anteriores más el nuevo, y guardamos el estado que devuelve el grafo.
        estado = grafo.invoke({"messages": [*estado["messages"], HumanMessage(texto)]})
        print(f"Asistente: {estado['messages'][-1].text}")


if __name__ == "__main__":
    main()
