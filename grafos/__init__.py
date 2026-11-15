"""Asistente EventHub rehecho como grafo de LangGraph, en cuatro versiones.

- v1_grafo_simple: estado TypedDict, clasificación por reglas y arista condicional (sin LLM).
- v2_chatbot:      MessagesState y un nodo chatbot que llama al modelo.
- v3_memoria:      el grafo de v2 compilado con un checkpointer (memoria por thread_id).
- v4_herramientas: nodo de herramientas escrito a mano, bucle chatbot ↔ herramientas y límite de pasos.
"""
