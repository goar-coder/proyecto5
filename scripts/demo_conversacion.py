"""Prueba de entrega: conversación de varios turnos contra la API real.

- Usa TestClient sobre main.app (prueba los endpoints sin levantar uvicorn).
- Trabaja sobre una COPIA temporal de data/ (EVENTHUB_DATA_DIR), así la
  reserva no modifica data/events.json del repositorio.
- Imprime la conversación y la guarda en docs/conversacion_prueba.md.

Uso:  python scripts/demo_conversacion.py
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# La copia de datos se prepara antes de importar la app.
_tmp = Path(tempfile.mkdtemp(prefix="eventhub_demo_"))
shutil.copytree(RAIZ / "data", _tmp / "data")
os.environ["EVENTHUB_DATA_DIR"] = str(_tmp / "data")

from fastapi.testclient import TestClient  # noqa: E402

from config.settings import openai_api_key, openai_model  # noqa: E402
from main import app  # noqa: E402

SALIDA = RAIZ / "docs" / "conversacion_prueba.md"
THREAD = "demo-principal"
THREAD_2 = "demo-otro-usuario"

cliente = TestClient(app)
lineas: list[str] = []


def escribir(texto: str = "") -> None:
    print(texto)
    lineas.append(texto)


def disponibles(id_evento: str) -> int:
    eventos = json.loads((_tmp / "data" / "events.json").read_text(encoding="utf-8"))
    return next(e["disponibles"] for e in eventos if e["id"] == id_evento)


def mostrar(titulo: str, peticion: str, respuesta: dict) -> None:
    escribir(f"### {titulo}")
    escribir()
    escribir(f"**Usuario:** {peticion}")
    escribir()
    herramientas = respuesta.get("herramientas") or []
    if herramientas:
        llamadas = ", ".join(
            f"`{h['nombre']}({json.dumps(h['argumentos'], ensure_ascii=False)})`" for h in herramientas
        )
        escribir(f"*Herramientas llamadas:* {llamadas}")
    else:
        escribir("*Herramientas llamadas:* ninguna")
    escribir()
    if respuesta.get("estado") == "pendiente_confirmacion":
        escribir(
            f"**API:** `pendiente_confirmacion` → acción `{respuesta['accion']}` "
            f"con argumentos `{json.dumps(respuesta['argumentos'], ensure_ascii=False)}`"
        )
    else:
        escribir(f"**Asistente:** {respuesta['respuesta']}")
    escribir()


def chat(thread_id: str, mensaje: str, titulo: str) -> dict:
    r = cliente.post("/chat", json={"thread_id": thread_id, "mensaje": mensaje})
    r.raise_for_status()
    datos = r.json()
    mostrar(f"{titulo}  (thread_id=`{thread_id}`)", mensaje, datos)
    return datos


def main() -> None:
    if not openai_api_key():
        sys.exit("Falta OPENAI_API_KEY: copia .env.example a .env y pon tu clave.")

    escribir("# Conversación de prueba — Asistente EventHub")
    escribir()
    escribir(f"Generada con `scripts/demo_conversacion.py` el {datetime.now():%Y-%m-%d %H:%M} "
             f"con el modelo `{openai_model()}`. Se ha usado una copia temporal de `data/`.")
    escribir()

    chat(THREAD, "¿Cuál es la política de devoluciones?", "Turno 1 — Políticas")
    chat(THREAD, "¿Qué conciertos hay en Valencia?", "Turno 2 — Búsqueda de eventos")
    chat(THREAD, "¿Y el más barato de esos?", "Turno 3 — Referencia al turno anterior (memoria)")
    chat(THREAD, "Quiero saber el estado del pedido EH-1001, mi email es laura@otrodominio.com",
         "Turno 4 — Pedido con email incorrecto")
    chat(THREAD, "Perdona, me equivoqué: el email es laura.martinez@example.com",
         "Turno 5 — Pedido con email correcto")

    antes = disponibles("EV002")
    pendiente = chat(THREAD, "Resérvame 2 entradas del concierto más barato de Valencia",
                     "Turno 6 — Reserva (requiere confirmación)")
    if pendiente.get("estado") != "pendiente_confirmacion":
        escribir("> ⚠️ El agente no pidió confirmación de reserva en este turno.")
    else:
        r = cliente.post("/chat/confirmar", json={"thread_id": THREAD, "aprobar": True})
        r.raise_for_status()
        mostrar(f"Turno 6b — Confirmación  (thread_id=`{THREAD}`)", "POST /chat/confirmar {aprobar: true}", r.json())
    despues = disponibles("EV002")
    escribir(f"> Comprobación en events.json (copia): EV002 tenía **{antes}** disponibles y ahora tiene **{despues}**.")
    escribir()

    chat(THREAD, "¿Cuántas entradas quedan ahora para ese concierto?", "Turno 7 — Comprobar stock tras la reserva")
    chat(THREAD, "¿Hay parking en el recinto?", "Turno 8 — Pregunta fuera de las políticas (no debe inventar)")
    chat(THREAD_2, "¿Cuál era el concierto más barato que te pregunté antes?",
         "Turno 9 — Otro thread_id (no comparte memoria)")

    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nTranscripción guardada en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
