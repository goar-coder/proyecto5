"""Versión 3: memoria con checkpointer.

Es el MISMO grafo de la v2 (START → chatbot → END), pero compilado con un
checkpointer InMemorySaver. Ahora cada invocación lleva un `thread_id` en la
config, y el checkpointer guarda el estado de ese hilo después de cada paso:
basta con enviar el mensaje nuevo, el historial lo recupera LangGraph.

Hilos distintos = estados distintos: el hilo 1 no ve lo que se habló en el 2.
`grafo.get_state(config)` devuelve la última instantánea guardada de un hilo.

Uso:
    python -m grafos.v3_memoria          # bucle en terminal (/hilo <id>, /historial, salir)
    python -m grafos.v3_memoria --demo   # demostración de hilos aislados + get_state
"""

import sys

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from grafos.v2_chatbot import crear_builder


def construir_grafo(modelo=None, checkpointer=None):
    # Checkpointer propio de esta versión (no se comparte con el de la API de la sesión 4).
    return crear_builder(modelo).compile(checkpointer=checkpointer or InMemorySaver())


def config_hilo(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def enviar(grafo, thread_id: str, texto: str) -> str:
    """Envía SOLO el mensaje nuevo; el checkpointer aporta el historial del hilo."""
    estado = grafo.invoke({"messages": [HumanMessage(texto)]}, config_hilo(thread_id))
    return estado["messages"][-1].text


def formatear_estado(grafo, thread_id: str) -> str:
    """Resumen legible de get_state: mensajes guardados, siguiente nodo y checkpoint."""
    snapshot = grafo.get_state(config_hilo(thread_id))
    mensajes = snapshot.values.get("messages", [])
    lineas = [
        f"get_state(thread_id={thread_id!r})",
        f"  mensajes guardados: {len(mensajes)}",
        f"  next: {snapshot.next}  (vacío = el grafo terminó el turno)",
        f"  checkpoint_id: {snapshot.config['configurable'].get('checkpoint_id')}",
        f"  paso: {snapshot.metadata.get('step') if snapshot.metadata else None}",
    ]
    for i, m in enumerate(mensajes, 1):
        lineas.append(f"  [{i}] {m.type}: {m.text}")
    return "\n".join(lineas)


def demo_hilos(grafo=None) -> list[tuple[str, str, str]]:
    """Demuestra que los hilos no comparten memoria. Devuelve (hilo, pregunta, respuesta)."""
    grafo = grafo or construir_grafo()
    turnos = [
        ("hilo-1", "Hola, me llamo Laura. ¿Cuál es la política de devoluciones?"),
        ("hilo-2", "¿Cómo me llamo?"),
        ("hilo-1", "¿Cómo me llamo?"),
    ]
    return [(hilo, texto, enviar(grafo, hilo, texto)) for hilo, texto in turnos]


def _demo() -> None:
    grafo = construir_grafo()
    for hilo, texto, respuesta in demo_hilos(grafo):
        print(f"[{hilo}] Tú: {texto}\n[{hilo}] Asistente: {respuesta}\n")
    print(formatear_estado(grafo, "hilo-1"))
    print()
    print(formatear_estado(grafo, "hilo-2"))


def main() -> None:
    if "--demo" in sys.argv:
        _demo()
        return
    grafo = construir_grafo()
    hilo = "hilo-1"
    print("Chatbot EventHub (v3, con memoria). Comandos: /hilo <id>, /historial, salir.")
    while True:
        try:
            texto = input(f"\n[{hilo}] Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if texto.lower() in {"salir", "exit", "quit"}:
            break
        if texto.startswith("/hilo"):
            hilo = texto.removeprefix("/hilo").strip() or hilo
            print(f"Ahora en el hilo {hilo!r}")
        elif texto == "/historial":
            print(formatear_estado(grafo, hilo))
        elif texto:
            print(f"Asistente: {enviar(grafo, hilo, texto)}")


if __name__ == "__main__":
    main()
