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
