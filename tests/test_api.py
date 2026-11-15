from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import main
from llm import agent as agente_mod
from tests.test_agent_flow import ModeloGuionizado, _llamada


def test_pagina_de_prueba_y_error_sin_api_key(monkeypatch):
    monkeypatch.setattr("api.routes.openai_api_key", lambda: None)
    cliente = TestClient(main.app)
    r = cliente.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "/chat/confirmar" in r.text
    r = cliente.post("/chat", json={"thread_id": "x", "mensaje": "hola"})
    assert r.status_code == 503 and "OPENAI_API_KEY" in r.json()["detail"]


def test_pagina_chat_libre_sin_mensajes_de_ejemplo():
    r = TestClient(main.app).get("/chat-libre")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "/chat/confirmar" in r.text
    assert "EH-1001" not in r.text and "SUGERENCIAS" not in r.text


def test_chat_pendiente_y_confirmar(datos_temporales, monkeypatch):
    monkeypatch.setattr("api.routes.openai_api_key", lambda: "sk-test")
    ag = agente_mod.construir_agente(ModeloGuionizado(messages=iter([
        _llamada("reservar_entradas", {"id_evento": "EV004", "cantidad": 3}, "c1"),
        AIMessage("Listo."),
    ])))
    monkeypatch.setattr(agente_mod, "obtener_agente", lambda: ag)
    cliente = TestClient(main.app)

    assert cliente.get("/health").json() == {"status": "ok"}
    assert cliente.post("/chat/confirmar", json={"thread_id": "api1", "aprobar": True}).status_code == 409

    r = cliente.post("/chat", json={"thread_id": "api1", "mensaje": "reserva 3 de EV004"}).json()
    assert r["estado"] == "pendiente_confirmacion"
    assert r["accion"] == "reservar_entradas" and r["argumentos"] == {"id_evento": "EV004", "cantidad": 3}

    assert cliente.post("/chat", json={"thread_id": "api1", "mensaje": "otra cosa"}).status_code == 409

    r = cliente.post("/chat/confirmar", json={"thread_id": "api1", "aprobar": True}).json()
    assert r["respuesta"] == "Listo."
    # La herramienta aprobada se ejecuta en la reanudación
    assert r["herramientas"] == [{"nombre": "reservar_entradas", "argumentos": {"id_evento": "EV004", "cantidad": 3}}]
