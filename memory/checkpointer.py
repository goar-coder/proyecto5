"""Checkpointer en memoria: guarda el estado (historial) de cada conversación.

Cada conversación se identifica por un `thread_id` que se pasa en
config={"configurable": {"thread_id": ...}}. Al reiniciar el proceso se pierde.
"""

from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
