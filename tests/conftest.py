import shutil
from pathlib import Path

import pytest

DATA_ORIGINAL = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def datos_temporales(tmp_path, monkeypatch):
    """Copia data/ a una carpeta temporal y apunta EVENTHUB_DATA_DIR a ella,
    para que los tests puedan escribir sin tocar los datos reales."""
    destino = tmp_path / "data"
    shutil.copytree(DATA_ORIGINAL, destino)
    monkeypatch.setenv("EVENTHUB_DATA_DIR", str(destino))
    return destino
