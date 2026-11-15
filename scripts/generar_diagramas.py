"""Genera los diagramas Mermaid de las versiones 1 y 4 en grafos/diagramas/.

La estructura del grafo no depende del LLM, así que la v4 se construye con un
modelo falso: no hace falta OPENAI_API_KEY ni conexión a internet.

Uso:  python scripts/generar_diagramas.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402

from grafos import v1_grafo_simple, v4_herramientas  # noqa: E402
from grafos.comun import guardar_diagrama  # noqa: E402


class _ModeloSoloEstructura(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def main() -> None:
    grafos = {
        "v1": v1_grafo_simple.construir_grafo(),
        "v4": v4_herramientas.construir_grafo(_ModeloSoloEstructura(messages=iter([]))),
    }
    for nombre, grafo in grafos.items():
        print(f"Diagrama {nombre}: {guardar_diagrama(grafo, nombre).relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
