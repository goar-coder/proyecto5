"""Configuración de la aplicación leída del entorno / fichero .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

# Carga .env (si existe) sin pisar variables ya definidas en el entorno.
load_dotenv(RAIZ_PROYECTO / ".env")

MODELO_POR_DEFECTO = "gpt-4.1-mini"


def openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def openai_model() -> str:
    return os.getenv("OPENAI_MODEL") or MODELO_POR_DEFECTO


def data_dir() -> Path:
    """Carpeta de datos. Se lee en cada llamada para que tests y demo puedan
    apuntar a una copia temporal con EVENTHUB_DATA_DIR."""
    return Path(os.getenv("EVENTHUB_DATA_DIR") or RAIZ_PROYECTO / "data")


def openai_temperature() -> float | None:
    """Temperatura del modelo, o None para no enviarla (modelos que no la admiten)."""
    valor = os.getenv("OPENAI_TEMPERATURE", "").strip()
    return float(valor) if valor else None
