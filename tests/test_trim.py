from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from memory.trim import MAX_MENSAJES, recortar_historial


def _ai_con_tool(i: int) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"id": f"call{i}", "name": "buscar_eventos", "args": {}}])


def _sin_huerfanos(mensajes) -> bool:
    """Cada ToolMessage debe tener antes un AIMessage con su tool_call_id."""
    ids_vistos = set()
    for m in mensajes:
        if isinstance(m, AIMessage):
            ids_vistos |= {tc["id"] for tc in m.tool_calls}
        if isinstance(m, ToolMessage) and m.tool_call_id not in ids_vistos:
            return False
    return True


def _conversacion(turnos: int):
    """Turnos de 4 mensajes: humano, AI con tool_call, resultado de herramienta, AI final."""
    mensajes = []
    for i in range(turnos):
        mensajes += [
            HumanMessage(f"pregunta {i}"),
            _ai_con_tool(i),
            ToolMessage("resultado", tool_call_id=f"call{i}"),
            AIMessage(f"respuesta {i}"),
        ]
    return mensajes


def test_historial_corto_no_se_toca():
    mensajes = [HumanMessage("hola"), AIMessage("hola")]
    assert recortar_historial(mensajes) == mensajes


def test_nunca_mas_de_10_y_sin_huerfanos_para_cualquier_longitud():
    completo = _conversacion(8)  # 32 mensajes
    for n in range(len(completo) + 1):
        recortado = recortar_historial(completo[:n])
        assert len(recortado) <= MAX_MENSAJES
        assert _sin_huerfanos(recortado)
        assert recortado == completo[:n][-len(recortado):] if recortado else True


def test_corte_en_tool_message_avanza():
    # 11 mensajes: el corte a 10 deja fuera el AIMessage con tool_calls de call0
    mensajes = [_ai_con_tool(0), ToolMessage("r", tool_call_id="call0")] + [HumanMessage(str(i)) for i in range(9)]
    recortado = recortar_historial(mensajes)
    assert not isinstance(recortado[0], ToolMessage)
    assert len(recortado) == 9


def test_varias_tool_messages_paralelas_huerfanas():
    ai = AIMessage(content="", tool_calls=[
        {"id": "a", "name": "x", "args": {}}, {"id": "b", "name": "y", "args": {}}])
    mensajes = [HumanMessage("q"), ai, ToolMessage("1", tool_call_id="a"), ToolMessage("2", tool_call_id="b")]
    mensajes += [HumanMessage(str(i)) for i in range(8)]  # total 12 → ventana empieza en ToolMessage "a"
    recortado = recortar_historial(mensajes)
    assert len(recortado) == 8
    assert _sin_huerfanos(recortado)
