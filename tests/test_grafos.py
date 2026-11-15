"""Tests de las cuatro versiones del grafo. Ninguno llama a OpenAI."""

import pytest

from grafos import v1_grafo_simple as v1


# --- Versión 1: grafo simple sin LLM ---------------------------------------

@pytest.mark.parametrize("mensaje, intencion", [
    ("¿Qué conciertos hay en Valencia?", "eventos"),
    ("Quiero entradas para el teatro", "eventos"),
    ("¿Cómo va mi pedido?", "pedido"),
    ("estado de eh-1003", "pedido"),
    ("Mi pedido está cancelado, ¿qué hago?", "pedido"),  # pedido tiene prioridad
    ("¿Puedo DEVOLVER mis entradas?", "politicas"),  # politicas va antes que eventos
    ("¿Se puede cambiar el titular?", "politicas"),
    ("¿Qué POLÍTICA tenéis?", "politicas"),
    ("¿Qué tiempo hace hoy?", "otro"),
    ("", "otro"),
])
def test_v1_clasifica_y_responde_segun_la_ruta(mensaje, intencion):
    estado = v1.construir_grafo().invoke({"mensaje": mensaje})
    assert estado["intencion"] == intencion
    assert estado["respuesta"] == v1.RESPUESTAS[intencion]


def test_v1_diagrama_tiene_arista_condicional(tmp_path, monkeypatch):
    monkeypatch.setattr("grafos.comun.CARPETA_DIAGRAMAS", tmp_path)
    from grafos.comun import guardar_diagrama
    mermaid = guardar_diagrama(v1.construir_grafo(), "v1").read_text(encoding="utf-8")
    for nodo in ("clasificar", "responder_eventos", "responder_pedido", "responder_politicas", "responder_otro"):
        assert nodo in mermaid
    assert "clasificar -. &nbsp;pedido&nbsp; .-> responder_pedido" in mermaid  # rama condicional


# --- Modelos falsos ----------------------------------------------------------

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage  # noqa: E402

from tests.test_agent_flow import ModeloGuionizado, _llamada  # noqa: E402


class ModeloQueRecuerda(GenericFakeChatModel):
    """Responde con el texto de todos los mensajes humanos que recibe y guarda lo recibido.
    Sirve para comprobar qué historial le llega al modelo."""

    recibido: list = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult
        self.recibido.append(list(messages))
        humanos = " | ".join(m.text for m in messages if isinstance(m, HumanMessage))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(f"vistos: {humanos}"))])


# --- Versión 2: chatbot ------------------------------------------------------

from grafos import v2_chatbot as v2  # noqa: E402


def test_v2_chatbot_antepone_sistema_y_anade_respuesta():
    modelo = ModeloQueRecuerda(messages=iter([]), recibido=[])
    estado = v2.construir_grafo(modelo).invoke({"messages": [HumanMessage("hola")]})
    assert [m.type for m in estado["messages"]] == ["human", "ai"]
    assert estado["messages"][-1].text == "vistos: hola"
    enviado = modelo.recibido[0]
    assert isinstance(enviado[0], SystemMessage)
    assert "Devoluciones" in enviado[0].content  # las políticas van en el prompt
    assert "EventHub" in enviado[0].content


def test_v2_sin_checkpointer_no_recuerda():
    grafo = v2.construir_grafo(ModeloQueRecuerda(messages=iter([]), recibido=[]))
    grafo.invoke({"messages": [HumanMessage("me llamo Laura")]})
    estado = grafo.invoke({"messages": [HumanMessage("¿cómo me llamo?")]})
    assert estado["messages"][-1].text == "vistos: ¿cómo me llamo?"


# --- Versión 3: memoria ------------------------------------------------------

from grafos import v3_memoria as v3  # noqa: E402


def test_v3_hilos_aislados_y_get_state():
    grafo = v3.construir_grafo(ModeloQueRecuerda(messages=iter([]), recibido=[]))
    resultados = v3.demo_hilos(grafo)
    # hilo-2 solo ve su propia pregunta; hilo-1 ve también lo que se dijo antes en hilo-1
    assert resultados[1][2] == "vistos: ¿Cómo me llamo?"
    assert "me llamo Laura" in resultados[2][2] and resultados[2][2].endswith("¿Cómo me llamo?")

    snapshot = grafo.get_state(v3.config_hilo("hilo-1"))
    assert [m.type for m in snapshot.values["messages"]] == ["human", "ai", "human", "ai"]
    assert snapshot.next == ()
    assert len(grafo.get_state(v3.config_hilo("hilo-2")).values["messages"]) == 2

    texto = v3.formatear_estado(grafo, "hilo-1")
    assert "mensajes guardados: 4" in texto and "[4] ai:" in texto


def test_v3_hilo_nuevo_esta_vacio():
    grafo = v3.construir_grafo(ModeloQueRecuerda(messages=iter([]), recibido=[]))
    assert grafo.get_state(v3.config_hilo("nadie")).values == {}
