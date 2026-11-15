"""Lectura y escritura de los ficheros JSON de data/."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from config.settings import data_dir


def ruta(nombre: str) -> Path:
    return data_dir() / nombre


def leer_json(nombre: str) -> Any:
    with ruta(nombre).open(encoding="utf-8") as f:
        return json.load(f)


def escribir_json_seguro(nombre: str, datos: Any) -> None:
    """Escritura atómica: se escribe en un temporal del mismo directorio y se
    reemplaza el original con os.replace, así nunca queda un fichero a medias."""
    destino = ruta(nombre)
    fd, tmp = tempfile.mkstemp(dir=destino.parent, prefix=f".{destino.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, destino)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
