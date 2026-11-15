"""Consulta de eventos."""

import unicodedata

from services.datos import leer_json

ARCHIVO_EVENTOS = "events.json"


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin espacios sobrantes: 'Málaga ' → 'malaga'."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sin_tildes.casefold().strip()


def listar_eventos() -> list[dict]:
    return leer_json(ARCHIVO_EVENTOS)


def obtener_evento(id_evento: str) -> dict | None:
    objetivo = normalizar(id_evento)
    return next((e for e in listar_eventos() if normalizar(e["id"]) == objetivo), None)


def buscar_eventos(ciudad: str | None = None, categoria: str | None = None) -> list[dict]:
    """Eventos que cumplen los filtros dados (los vacíos se ignoran), ordenados por fecha."""
    resultado = []
    for e in listar_eventos():
        if ciudad and normalizar(e["ciudad"]) != normalizar(ciudad):
            continue
        if categoria and normalizar(e["categoria"]) != normalizar(categoria):
            continue
        resultado.append(
            {k: e[k] for k in ("id", "nombre", "ciudad", "categoria", "fecha", "precio", "disponibles")}
        )
    return sorted(resultado, key=lambda e: e["fecha"])
