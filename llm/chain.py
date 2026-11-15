"""Paso 1: cadena LCEL que responde preguntas sobre las políticas de EventHub.

La cadena es:   prompt  |  modelo  |  parser
- No tiene memoria: cada llamada es independiente.
- Las políticas se inyectan en el mensaje de sistema, así el modelo solo
  "conoce" lo que está escrito en data/policies.md.
"""

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from llm.models import crear_modelo
from llm.prompts import REGLAS_POLITICAS, cargar_politicas


def construir_cadena_politicas() -> Runnable:
    # 1) ChatPromptTemplate: plantilla de mensajes. Tiene dos variables:
    #    - {politicas}: el texto de policies.md (se rellena con .partial abajo).
    #    - {pregunta}: lo que pregunta el usuario en cada invocación.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Eres el asistente de atención al cliente de EventHub.\n\n"
                       + REGLAS_POLITICAS
                       + "\n\n=== POLÍTICAS DE EVENTHUB ===\n{politicas}\n=== FIN DE LAS POLÍTICAS ==="),
            ("human", "{pregunta}"),
        ]
    ).partial(politicas=cargar_politicas())  # fijamos las políticas una sola vez

    # 2) ChatOpenAI: recibe la lista de mensajes ya formateada y devuelve un AIMessage.
    modelo = crear_modelo()

    # 3) StrOutputParser: extrae el texto (.content) del AIMessage → str.
    parser = StrOutputParser()

    # El operador | (LCEL) encadena los Runnables: la salida de uno es la entrada
    # del siguiente. Entrada: {"pregunta": str}  →  Salida: str.
    return prompt | modelo | parser


@lru_cache
def obtener_cadena_politicas() -> Runnable:
    """Construye la cadena una vez y la reutiliza."""
    return construir_cadena_politicas()


def responder_politica(pregunta: str) -> str:
    return obtener_cadena_politicas().invoke({"pregunta": pregunta})
