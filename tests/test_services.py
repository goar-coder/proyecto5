import json

import pytest

from services import eventos, pedidos, reservas


# --- eventos ---------------------------------------------------------------

def test_filtro_por_ciudad_y_categoria(datos_temporales):
    resultado = eventos.buscar_eventos(ciudad="Valencia", categoria="concierto")
    assert {e["id"] for e in resultado} == {"EV001", "EV002", "EV003", "EV004"}
    assert all(set(e) >= {"id", "nombre", "fecha", "precio", "disponibles"} for e in resultado)


def test_filtro_sin_mayusculas_ni_tildes(datos_temporales):
    assert eventos.buscar_eventos(ciudad="MALAGA") == eventos.buscar_eventos(ciudad="Málaga")
    assert len(eventos.buscar_eventos(ciudad="  málaga ")) == 1
    assert eventos.buscar_eventos(categoria="Concierto") == eventos.buscar_eventos(categoria="concierto")


def test_sin_filtros_devuelve_todo_y_ciudad_inexistente_nada(datos_temporales):
    assert len(eventos.buscar_eventos()) == 16
    assert eventos.buscar_eventos(ciudad="Bilbao") == []


def test_incluye_evento_agotado(datos_temporales):
    agotados = [e for e in eventos.buscar_eventos(ciudad="valencia") if e["disponibles"] == 0]
    assert [e["id"] for e in agotados] == ["EV003"]


# --- pedidos ---------------------------------------------------------------

def test_pedido_email_correcto(datos_temporales):
    r = pedidos.consultar_pedido("EH-1001", "laura.martinez@example.com")
    assert r["encontrado"] is True and r["estado"] == "pagado"


def test_pedido_email_correcto_sin_distinguir_mayusculas(datos_temporales):
    r = pedidos.consultar_pedido(" eh-1001 ", "Laura.Martinez@Example.com")
    assert r["encontrado"] is True


def test_pedido_email_incorrecto_e_inexistente_dan_el_mismo_mensaje(datos_temporales):
    incorrecto = pedidos.consultar_pedido("EH-1001", "otra@example.com")
    inexistente = pedidos.consultar_pedido("EH-9999", "laura.martinez@example.com")
    assert incorrecto == inexistente
    assert incorrecto == {"encontrado": False, "mensaje": pedidos.MENSAJE_PEDIDO_NO_VERIFICADO}
    assert "estado" not in incorrecto


# --- reservas --------------------------------------------------------------

def _disponibles(carpeta, id_evento):
    datos = json.loads((carpeta / "events.json").read_text(encoding="utf-8"))
    return next(e["disponibles"] for e in datos if e["id"] == id_evento)


def test_reserva_descuenta_y_guarda(datos_temporales):
    r = reservas.reservar_entradas("EV002", 2)
    assert r["disponibles_restantes"] == 38 and r["total"] == 45.0
    assert _disponibles(datos_temporales, "EV002") == 38
    assert not list(datos_temporales.glob("*.tmp"))  # no quedan temporales


def test_reserva_sin_stock(datos_temporales):
    with pytest.raises(reservas.ErrorReserva, match="No hay entradas suficientes"):
        reservas.reservar_entradas("EV003", 1)
    with pytest.raises(reservas.ErrorReserva):
        reservas.reservar_entradas("EV002", 41)
    assert _disponibles(datos_temporales, "EV002") == 40


@pytest.mark.parametrize("cantidad", [0, -1, True, 1.5])
def test_reserva_cantidad_invalida(datos_temporales, cantidad):
    with pytest.raises(reservas.ErrorReserva, match="cantidad"):
        reservas.reservar_entradas("EV002", cantidad)
    assert _disponibles(datos_temporales, "EV002") == 40


def test_reserva_evento_inexistente(datos_temporales):
    with pytest.raises(reservas.ErrorReserva, match="No existe"):
        reservas.reservar_entradas("EV999", 1)


def test_datos_reales_no_se_tocan(datos_temporales):
    from tests.conftest import DATA_ORIGINAL
    reservas.reservar_entradas("EV001", 5)
    assert _disponibles(DATA_ORIGINAL, "EV001") == 120


# --- filtro por mes --------------------------------------------------------

def test_filtro_por_mes_con_ciudad_y_categoria(datos_temporales):
    resultado = eventos.buscar_eventos(ciudad="Madrid", categoria="concierto", mes="2026-12")
    assert [e["id"] for e in resultado] == ["EV013", "EV014", "EV015"]  # EV016 es de enero


def test_filtro_por_mes_solo(datos_temporales):
    resultado = eventos.buscar_eventos(mes="2027-01")
    assert resultado and all(e["fecha"].startswith("2027-01") for e in resultado)
    assert "EV016" in {e["id"] for e in resultado}


@pytest.mark.parametrize("mes", ["diciembre", "2026-13", "2026-1", "12-2026"])
def test_filtro_por_mes_invalido(datos_temporales, mes):
    with pytest.raises(ValueError, match="AAAA-MM"):
        eventos.buscar_eventos(mes=mes)


def test_herramienta_buscar_eventos_mes_invalido_devuelve_error(datos_temporales):
    from tools.eventhub_tools import buscar_eventos as herramienta
    assert "error" in json.loads(herramienta.invoke({"mes": "diciembre"}))
