"""Flujo del agente con un modelo falso guionizado (sin llamar a OpenAI):
comprueba la interrupción antes de reservar, la aprobación y el rechazo."""

import json

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from llm import agent as agente_mod


class ModeloGuionizado(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _llamada(nombre, args, id_):
    return AIMessage(content="", tool_calls=[{"id": id_, "name": nombre, "args": args}])


def _agente(respuestas):
    return agente_mod.construir_agente(ModeloGuionizado(messages=iter(respuestas)))


def test_busqueda_y_reserva_aprobada(datos_temporales):
    ag = _agente([
        _llamada("buscar_eventos", {"ciudad": "Valencia", "categoria": "concierto"}, "c1"),
        AIMessage("Hay 4 conciertos."),
        _llamada("reservar_entradas", {"id_evento": "EV002", "cantidad": 2}, "c2"),
        AIMessage("Reserva hecha."),
    ])
    r = agente_mod.enviar_mensaje("t1", "conciertos en valencia", agente=ag)
    assert r["respuesta"] == "Hay 4 conciertos."
    assert r["herramientas"][0]["nombre"] == "buscar_eventos"

    r = agente_mod.enviar_mensaje("t1", "reserva 2 del más barato", agente=ag)
    assert r["estado"] == "pendiente_confirmacion"
    assert r["accion"] == "reservar_entradas" and r["argumentos"] == {"id_evento": "EV002", "cantidad": 2}
    # Aún no se ha descontado nada
    eventos = json.loads((datos_temporales / "events.json").read_text(encoding="utf-8"))
    assert next(e for e in eventos if e["id"] == "EV002")["disponibles"] == 40

    # Mientras está pendiente no se aceptan mensajes nuevos
    try:
        agente_mod.enviar_mensaje("t1", "hola", agente=ag)
        raise AssertionError("debería haber fallado")
    except agente_mod.ConfirmacionPendiente:
        pass

    r = agente_mod.confirmar("t1", True, agente=ag)
    assert r["respuesta"] == "Reserva hecha."
    eventos = json.loads((datos_temporales / "events.json").read_text(encoding="utf-8"))
    assert next(e for e in eventos if e["id"] == "EV002")["disponibles"] == 38


def test_reserva_rechazada_no_descuenta(datos_temporales):
    ag = _agente([
        _llamada("reservar_entradas", {"id_evento": "EV001", "cantidad": 1}, "c1"),
        AIMessage("De acuerdo, no reservo."),
    ])
    assert agente_mod.enviar_mensaje("t2", "reserva 1 de EV001", agente=ag)["estado"] == "pendiente_confirmacion"
    r = agente_mod.confirmar("t2", False, agente=ag)
    assert r["respuesta"] == "De acuerdo, no reservo."
    assert "rechaz" in r["resultados_herramientas"][0].lower()
    eventos = json.loads((datos_temporales / "events.json").read_text(encoding="utf-8"))
    assert next(e for e in eventos if e["id"] == "EV001")["disponibles"] == 120


def test_confirmar_sin_pendiente(datos_temporales):
    ag = _agente([AIMessage("hola")])
    try:
        agente_mod.confirmar("t3", True, agente=ag)
        raise AssertionError("debería haber fallado")
    except agente_mod.ConfirmacionNoPendiente:
        pass
