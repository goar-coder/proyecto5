"""La cadena se prueba con un modelo falso: no llama a OpenAI."""

from langchain_core.language_models.fake_chat_models import FakeListChatModel

import llm.chain as chain


def test_cadena_inyecta_politicas_y_devuelve_texto(monkeypatch):
    modelo_falso = FakeListChatModel(responses=["Respuesta de prueba"])
    monkeypatch.setattr(chain, "crear_modelo", lambda: modelo_falso)

    cadena = chain.construir_cadena_politicas()
    salida = cadena.invoke({"pregunta": "¿Puedo devolver mi entrada?"})
    assert salida == "Respuesta de prueba"  # StrOutputParser devuelve str

    # El primer paso de la cadena es el prompt: comprobamos lo que recibiría el modelo.
    mensajes = cadena.first.invoke({"pregunta": "hola"}).to_messages()
    assert mensajes[0].type == "system"
    assert "Devoluciones" in mensajes[0].content
    assert "contactar con soporte" in mensajes[0].content
    assert mensajes[1].content == "hola"
