"""Herramientas que el modelo puede invocar. Son finas: validan poco y
delegan en services/. El modelo lee el nombre, los type hints y el docstring."""

import json

from langchain_core.tools import tool

from services import eventos, pedidos, reservas


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


@tool
def buscar_eventos(
    ciudad: str | None = None, categoria: str | None = None, mes: str | None = None
) -> str:
    """Busca eventos de EventHub en el catálogo.

    Úsala siempre que el usuario pregunte por eventos, fechas, precios o
    disponibilidad. Todos los filtros son opcionales; ciudad y categoría no
    distinguen mayúsculas ni tildes.

    Args:
        ciudad: Ciudad del evento, p. ej. "Valencia", "Madrid".
        categoria: Tipo de evento, p. ej. "concierto", "teatro", "deporte", "comedia", "danza".
        mes: Mes del evento en formato "AAAA-MM", p. ej. "2026-12" para diciembre de 2026.

    Returns:
        Lista JSON de eventos con id, nombre, ciudad, categoria, fecha (ISO),
        precio (EUR) y disponibles (0 = agotado), o {"error": ...} si un filtro no es válido.
    """
    try:
        return _json(eventos.buscar_eventos(ciudad=ciudad, categoria=categoria, mes=mes))
    except ValueError as e:
        return _json({"error": str(e)})


@tool
def consultar_pedido(id_pedido: str, email: str) -> str:
    """Consulta el estado de un pedido de entradas.

    Requiere el identificador del pedido Y el email con el que se hizo la compra;
    si el usuario no ha dado alguno de los dos, pídeselo antes de llamar.

    Args:
        id_pedido: Identificador del pedido, p. ej. "EH-1001".
        email: Email usado en la compra.

    Returns:
        JSON con el estado del pedido si los datos coinciden, o un mensaje
        genérico si no se puede verificar.
    """
    return _json(pedidos.consultar_pedido(id_pedido, email))


@tool
def reservar_entradas(id_evento: str, cantidad: int) -> str:
    """Reserva entradas para un evento y descuenta las plazas disponibles.

    Usa el id exacto del evento obtenido con buscar_eventos. Esta acción
    requiere confirmación humana antes de ejecutarse.

    Args:
        id_evento: Identificador del evento, p. ej. "EV002".
        cantidad: Número de entradas a reservar (entero mayor que 0).

    Returns:
        JSON con el resultado de la reserva o con el error.
    """
    try:
        return _json({"ok": True, **reservas.reservar_entradas(id_evento, cantidad)})
    except reservas.ErrorReserva as e:
        return _json({"ok": False, "error": str(e)})


HERRAMIENTAS = [buscar_eventos, consultar_pedido, reservar_entradas]
