"""Prueba de entrega de las versiones LangGraph (llama a OpenAI).

Genera docs/entrega_langgraph.md con:
  1. Los diagramas Mermaid de las versiones 1 y 4.
  2. Ejemplos de clasificación de la versión 1 (sin LLM).
  3. La versión 3: hilos aislados y get_state de un hilo con 4 mensajes.
  4. La versión 4: la pregunta del enunciado (dos herramientas encadenadas en
     una misma respuesta), el caso sin email y el get_state del hilo.

Trabaja sobre una COPIA temporal de data/ (EVENTHUB_DATA_DIR).

Uso:  python scripts/demo_grafos.py
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

_tmp = Path(tempfile.mkdtemp(prefix="eventhub_grafos_"))
shutil.copytree(RAIZ / "data", _tmp / "data")
os.environ["EVENTHUB_DATA_DIR"] = str(_tmp / "data")

from config.settings import openai_api_key, openai_model  # noqa: E402
from grafos import v1_grafo_simple as v1  # noqa: E402
from grafos import v3_memoria as v3  # noqa: E402
from grafos import v4_herramientas as v4  # noqa: E402
from grafos.comun import guardar_diagrama  # noqa: E402

SALIDA = RAIZ / "docs" / "entrega_langgraph.md"
lineas: list[str] = []


def escribir(texto: str = "") -> None:
    print(texto)
    lineas.append(texto)


def bloque(texto: str, lenguaje: str = "text") -> None:
    escribir(f"```{lenguaje}")
    escribir(texto)
    escribir("```")
    escribir()


def turno_v4(grafo, hilo: str, texto: str) -> dict:
    r = v4.enviar(grafo, hilo, texto)
    escribir(f"**Usuario** (`{hilo}`): {texto}")
    escribir()
    if r["herramientas"]:
        escribir(f"*Herramientas llamadas en esta respuesta ({len(r['herramientas'])}, "
                 f"{r['pasos']} ronda(s)):*")
        for h in r["herramientas"]:
            escribir(f"- `{h['nombre']}({json.dumps(h['argumentos'], ensure_ascii=False)})`")
    else:
        escribir("*Herramientas llamadas:* ninguna")
    escribir()
    escribir(f"**Asistente:** {r['respuesta']}")
    escribir()
    return r


def main() -> None:
    if not openai_api_key():
        sys.exit("Falta OPENAI_API_KEY: copia .env.example a .env y pon tu clave.")

    escribir("# Entrega — Asistente EventHub como grafo de LangGraph")
    escribir()
    escribir(f"Generada con `scripts/demo_grafos.py` el {datetime.now():%Y-%m-%d %H:%M} "
             f"con el modelo `{openai_model()}`, sobre una copia temporal de `data/`.")
    escribir()

    # --- 1. Diagramas ----------------------------------------------------------
    grafo_v1 = v1.construir_grafo()
    grafo_v4 = v4.construir_grafo()
    escribir("## 1. Diagramas")
    escribir()
    for titulo, nombre, grafo in [("Versión 1 — grafo simple", "v1", grafo_v1),
                                  ("Versión 4 — herramientas", "v4", grafo_v4)]:
        escribir(f"### {titulo}")
        escribir()
        bloque(guardar_diagrama(grafo, nombre).read_text(encoding="utf-8").strip(), "mermaid")

    # --- 2. Versión 1 ----------------------------------------------------------
    escribir("## 2. Versión 1 — clasificación por reglas (sin LLM)")
    escribir()
    escribir("| Mensaje | Intención | Respuesta fija |")
    escribir("|---|---|---|")
    for mensaje in v1.EJEMPLOS:
        estado = grafo_v1.invoke({"mensaje": mensaje})
        escribir(f"| {mensaje} | `{estado['intencion']}` | {estado['respuesta']} |")
    escribir()

    # --- 3. Versión 3 ----------------------------------------------------------
    escribir("## 3. Versión 3 — memoria por hilo")
    escribir()
    grafo_v3 = v3.construir_grafo()
    for hilo, texto, respuesta in v3.demo_hilos(grafo_v3):
        escribir(f"**[{hilo}] Usuario:** {texto}")
        escribir()
        escribir(f"**[{hilo}] Asistente:** {respuesta}")
        escribir()
    escribir("El `hilo-2` no sabe el nombre porque su estado es independiente del `hilo-1`.")
    escribir()
    escribir("### `get_state` del hilo-1")
    escribir()
    bloque(v3.formatear_estado(grafo_v3, "hilo-1"))

    # --- 4. Versión 4 ----------------------------------------------------------
    escribir("## 4. Versión 4 — herramientas encadenadas")
    escribir()
    escribir("### Conversación A: pregunta del enunciado (con email)")
    escribir()
    r = turno_v4(grafo_v4, "conv-a",
                 "¿Mi pedido EH-1003 es para un concierto en Madrid? Si es así, dime otros "
                 "conciertos en Madrid ese mes. Mi email es ana.gomez@example.com")
    nombres = {h["nombre"] for h in r["herramientas"]}
    if {"consultar_pedido", "buscar_eventos"} <= nombres:
        escribir("> ✅ El agente encadenó `consultar_pedido` y `buscar_eventos` en la misma respuesta.")
    else:
        escribir("> ⚠️ El agente NO encadenó las dos herramientas en esta respuesta.")
    escribir()
    turno_v4(grafo_v4, "conv-a", "¿Cuál de esos es el más barato?")

    escribir("### Conversación B: sin email (el agente lo pide antes de seguir)")
    escribir()
    turno_v4(grafo_v4, "conv-b",
             "¿Mi pedido EH-1003 es para un concierto en Madrid? Si es así, dime otros "
             "conciertos en Madrid ese mes.")
    turno_v4(grafo_v4, "conv-b", "Mi email es ana.gomez@example.com")

    escribir("### `get_state` del hilo conv-a")
    escribir()
    bloque(v4.formatear_estado(grafo_v4, "conv-a"))

    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nTranscripción guardada en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
