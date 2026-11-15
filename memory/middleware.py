"""Middleware que limita los mensajes enviados al modelo.

Se usa `wrap_model_call` (y no `before_model`) a propósito: `before_model`
devuelve una actualización del *estado*, que se fusiona con el reducer
`add_messages` y quedaría guardada en el checkpointer. Aquí solo cambiamos la
petición al modelo (`request.messages`): el historial completo sigue en el
checkpointer y el modelo ve como máximo los últimos 10 mensajes. El prompt de
sistema va aparte (`request.system_message`) y no cuenta en el límite.
"""

from langchain.agents.middleware import wrap_model_call

from memory.trim import recortar_historial


@wrap_model_call
def recortar_mensajes(request, handler):
    return handler(request.override(messages=recortar_historial(request.messages)))
