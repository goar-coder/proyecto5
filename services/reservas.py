"""Reserva de entradas: descuenta stock en events.json."""

import threading

from services.datos import escribir_json_seguro, leer_json
from services.eventos import ARCHIVO_EVENTOS, normalizar

# Evita que dos peticiones simultáneas lean el mismo stock y lo sobrescriban.
_cerrojo = threading.Lock()


class ErrorReserva(ValueError):
    """Reserva no válida (evento inexistente, cantidad inválida o sin stock)."""


def reservar_entradas(id_evento: str, cantidad: int) -> dict:
    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
        raise ErrorReserva("La cantidad debe ser un número entero mayor que 0.")
    with _cerrojo:
        eventos = leer_json(ARCHIVO_EVENTOS)
        evento = next((e for e in eventos if normalizar(e["id"]) == normalizar(id_evento)), None)
        if evento is None:
            raise ErrorReserva(f"No existe ningún evento con id {id_evento!r}.")
        if evento["disponibles"] < cantidad:
            raise ErrorReserva(
                f"No hay entradas suficientes para '{evento['nombre']}': "
                f"quedan {evento['disponibles']} y se piden {cantidad}."
            )
        evento["disponibles"] -= cantidad
        escribir_json_seguro(ARCHIVO_EVENTOS, eventos)
        return {
            "id_evento": evento["id"],
            "nombre": evento["nombre"],
            "cantidad": cantidad,
            "precio_unitario": evento["precio"],
            "total": round(evento["precio"] * cantidad, 2),
            "disponibles_restantes": evento["disponibles"],
        }
