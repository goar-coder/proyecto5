"""Paso 3: agente con herramientas, memoria por thread_id y confirmación humana.

El modelo decide solo qué herramienta usar (no hay enrutado por palabras clave).
"""

from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.types import Command

from llm.models import crear_modelo
from llm.prompts import REGLAS_POLITICAS, cargar_politicas
from memory.checkpointer import checkpointer
from memory.middleware import recortar_mensajes
from tools.eventhub_tools import HERRAMIENTAS

HERRAMIENTAS_CON_CONFIRMACION = {"reservar_entradas"}


def construir_system_prompt() -> str:
    return f"""Eres el asistente de atención al cliente de EventHub, una plataforma de venta de entradas.

Reglas generales:
- No inventes datos. Si no sabes algo o no tienes una herramienta para averiguarlo,
  dilo y sugiere contactar con soporte (soporte@eventhub.example, +34 900 123 456).
- Para cualquier dato de eventos (qué hay, fechas, precios, disponibilidad) usa SIEMPRE
  la herramienta buscar_eventos; no respondas de memoria ni con datos de turnos anteriores
  si pueden haber cambiado (por ejemplo, la disponibilidad tras una reserva).
- Para el estado de un pedido usa SIEMPRE consultar_pedido. Necesitas el id del pedido y el
  email; si falta alguno, pídelo. Si la herramienta no lo verifica, no des pistas sobre si
  el pedido existe.
- Cuando el usuario pida reservar y sepas el evento y la cantidad, llama DIRECTAMENTE a
  reservar_entradas con el id exacto del evento. NO pidas confirmación por texto: el sistema
  muestra automáticamente la acción al usuario para que la apruebe o rechace antes de
  ejecutarla. Si falta el evento o la cantidad, pregúntalo. Si el usuario rechaza la reserva,
  no la vuelvas a intentar salvo que lo pida de nuevo.
- Usa el contexto de la conversación para entender referencias como "esos" o "el más barato".
- Responde en español, de forma breve y clara.

{REGLAS_POLITICAS}

=== POLÍTICAS DE EVENTHUB ===
{cargar_politicas()}
=== FIN DE LAS POLÍTICAS ==="""


def construir_agente(modelo=None):
    return create_agent(
        model=modelo or crear_modelo(),
        tools=HERRAMIENTAS,
        system_prompt=construir_system_prompt(),
        checkpointer=checkpointer,
        middleware=[
            # 1) Recorta a 10 mensajes lo que se envía al modelo (no el historial guardado).
            recortar_mensajes,
            # 2) Pausa la ejecución antes de reservar hasta que un humano apruebe o rechace.
            HumanInTheLoopMiddleware(
                interrupt_on={
                    nombre: {"allowed_decisions": ["approve", "reject"]}
                    for nombre in HERRAMIENTAS_CON_CONFIRMACION
                },
                description_prefix="La reserva necesita confirmación",
            ),
        ],
    )


@lru_cache
def obtener_agente():
    return construir_agente()


class ConfirmacionNoPendiente(Exception):
    """Se pidió confirmar pero no hay nada pendiente en ese thread."""


class ConfirmacionPendiente(Exception):
    """Se envió un mensaje nuevo con una acción pendiente de confirmar."""


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _interrupciones(agente, thread_id: str):
    return agente.get_state(_config(thread_id)).interrupts


def _mensajes(agente, thread_id: str) -> list[BaseMessage]:
    return agente.get_state(_config(thread_id)).values.get("messages", [])


def _resultado(agente, thread_id: str, n_previos: int) -> dict[str, Any]:
    """Construye la respuesta: texto final o acción pendiente, y herramientas llamadas."""
    nuevos = _mensajes(agente, thread_id)[n_previos:]
    herramientas = [
        {"nombre": tc["name"], "argumentos": tc["args"]}
        for m in nuevos if isinstance(m, AIMessage) for tc in m.tool_calls
    ]
    interrupciones = _interrupciones(agente, thread_id)
    if interrupciones:
        acciones = [
            {"accion": a["name"], "argumentos": a["args"]}
            for i in interrupciones for a in i.value["action_requests"]
        ]
        return {
            "estado": "pendiente_confirmacion",
            "accion": acciones[0]["accion"],
            "argumentos": acciones[0]["argumentos"],
            "acciones": acciones,
            "herramientas": herramientas,
        }
    texto = next(
        (m.text for m in reversed(nuevos) if isinstance(m, AIMessage) and not m.tool_calls),
        "",
    )
    resultados = [m.content for m in nuevos if isinstance(m, ToolMessage)]
    return {"respuesta": texto, "herramientas": herramientas, "resultados_herramientas": resultados}


def enviar_mensaje(thread_id: str, mensaje: str, agente=None) -> dict[str, Any]:
    agente = agente or obtener_agente()
    if _interrupciones(agente, thread_id):
        raise ConfirmacionPendiente()
    n_previos = len(_mensajes(agente, thread_id))
    agente.invoke({"messages": [{"role": "user", "content": mensaje}]}, _config(thread_id))
    return _resultado(agente, thread_id, n_previos)


def confirmar(thread_id: str, aprobar: bool, agente=None) -> dict[str, Any]:
    agente = agente or obtener_agente()
    interrupciones = _interrupciones(agente, thread_id)
    if not interrupciones:
        raise ConfirmacionNoPendiente()
    n_previos = len(_mensajes(agente, thread_id))
    # Modo "batched": una interrupción por turno con una decisión por cada acción.
    n_acciones = len(interrupciones[0].value["action_requests"])
    decision = (
        {"type": "approve"}
        if aprobar
        else {"type": "reject", "message": "El usuario ha rechazado la reserva."}
    )
    acciones = interrupciones[0].value["action_requests"]
    agente.invoke(Command(resume={"decisions": [decision] * n_acciones}), _config(thread_id))
    resultado = _resultado(agente, thread_id, n_previos)
    if aprobar:
        # Las herramientas aprobadas se ejecutan en esta reanudación.
        resultado["herramientas"] = [
            {"nombre": a["name"], "argumentos": a["args"]} for a in acciones
        ] + resultado["herramientas"]
    return resultado
