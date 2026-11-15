# Tutorial de LangChain con el Asistente EventHub

Este tutorial explica los conceptos básicos de LangChain v1 usando como ejemplo el código de este repositorio. Cada sección presenta una idea, muestra dónde aparece en el proyecto y propone un fragmento para probarla.

> **Versiones usadas:** `langchain 1.4.9`, `langchain-core 1.7.6`, `langchain-openai 1.7.4`, `langgraph 1.2.20` (fijadas en [requirements.txt](../requirements.txt)). LangChain cambia rápido: si usas otra versión, revisa la API instalada.

**Cómo ejecutar los fragmentos.** Desde la raíz del proyecto, con el venv activado, abre `python` y pégalos. Los que llaman a OpenAI necesitan `.env` con tu clave. Los que usan **modelos falsos** funcionan sin clave y no cuestan nada.

## Índice

1. [El mapa: los paquetes de LangChain](#1-el-mapa-los-paquetes-de-langchain)
2. [Modelos de chat y mensajes](#2-modelos-de-chat-y-mensajes)
3. [Prompts: ChatPromptTemplate](#3-prompts-chatprompttemplate)
4. [LCEL: encadenar con `|`](#4-lcel-encadenar-con-)
5. [Output parsers](#5-output-parsers)
6. [Herramientas con `@tool`](#6-herramientas-con-tool)
7. [Agentes con `create_agent`](#7-agentes-con-create_agent)
8. [Memoria: checkpointer y `thread_id`](#8-memoria-checkpointer-y-thread_id)
9. [Middleware: controlar lo que ve el modelo](#9-middleware-controlar-lo-que-ve-el-modelo)
10. [Human in the loop: interrupciones y `Command`](#10-human-in-the-loop-interrupciones-y-command)
11. [Probar sin gastar: modelos falsos](#11-probar-sin-gastar-modelos-falsos)
12. [Buenas prácticas que sigue el proyecto](#12-buenas-prácticas-que-sigue-el-proyecto)
13. [Ejercicios](#13-ejercicios)

---

## 1. El mapa: los paquetes de LangChain

LangChain está dividido en varios paquetes. En este proyecto se usan cuatro:

| Paquete | Para qué | Dónde se usa |
|---|---|---|
| `langchain-core` | Abstracciones base: mensajes, prompts, *Runnables*, parsers, `@tool` | [llm/chain.py](../llm/chain.py), [tools/](../tools/), [memory/trim.py](../memory/trim.py) |
| `langchain-openai` | Integración con OpenAI (`ChatOpenAI`) | [llm/models.py](../llm/models.py) |
| `langchain` | Alto nivel: `create_agent` y los middlewares | [llm/agent.py](../llm/agent.py), [memory/middleware.py](../memory/middleware.py) |
| `langgraph` | Motor sobre el que corren los agentes: estado, checkpointers, interrupciones, `Command` | [memory/checkpointer.py](../memory/checkpointer.py), [llm/agent.py](../llm/agent.py) |

En la práctica: **`langchain-core` sirve para cadenas sencillas** (paso 1) y **`langchain` + `langgraph` para agentes con estado** (pasos 2 y 3).

---

## 2. Modelos de chat y mensajes

Un **modelo de chat** recibe una lista de **mensajes** y devuelve un mensaje. En el proyecto, el modelo se crea en un único sitio, [llm/models.py](../llm/models.py):

```python
from langchain_openai import ChatOpenAI

def crear_modelo() -> ChatOpenAI:
    kwargs = {}
    temperatura = openai_temperature()          # opcional: algunos modelos no la admiten
    if temperatura is not None:
        kwargs["temperature"] = temperatura
    return ChatOpenAI(model=openai_model(), api_key=openai_api_key(), **kwargs)
```

Tipos de mensaje que aparecen en el proyecto:

| Clase | Rol | Ejemplo en EventHub |
|---|---|---|
| `SystemMessage` | Instrucciones para el modelo | Reglas + texto de `policies.md` |
| `HumanMessage` | Lo que escribe el usuario | «¿Qué conciertos hay en Valencia?» |
| `AIMessage` | Respuesta del modelo. Puede llevar `tool_calls` | «El más barato es Jazz al Atardecer…» |
| `ToolMessage` | Resultado de ejecutar una herramienta, enlazado por `tool_call_id` | JSON con los eventos |

Pruébalo (necesita clave):

```python
from langchain_core.messages import SystemMessage, HumanMessage
from llm.models import crear_modelo

modelo = crear_modelo()
respuesta = modelo.invoke([
    SystemMessage("Responde en una sola frase."),
    HumanMessage("¿Qué es una entrada nominativa?"),
])
print(type(respuesta).__name__)   # AIMessage
print(respuesta.content)
```

> En vez de clases también puedes pasar diccionarios: `{"role": "user", "content": "..."}`. Es lo que hace [llm/agent.py](../llm/agent.py) en `enviar_mensaje`.

---

## 3. Prompts: ChatPromptTemplate

Escribir los mensajes a mano no escala. Un **`ChatPromptTemplate`** es una plantilla de mensajes con variables `{entre_llaves}`. El de la cadena de políticas ([llm/chain.py](../llm/chain.py)):

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres el asistente de atención al cliente de EventHub.\n\n"
               + REGLAS_POLITICAS
               + "\n\n=== POLÍTICAS DE EVENTHUB ===\n{politicas}\n=== FIN DE LAS POLÍTICAS ==="),
    ("human", "{pregunta}"),
]).partial(politicas=cargar_politicas())
```

Conceptos clave:

- **Variables.** La plantilla tiene dos: `{politicas}` y `{pregunta}`.
- **`.partial(...)`** fija una variable de antemano. Las políticas no cambian entre preguntas, así que se rellenan una vez y solo queda `pregunta` por rellenar.
- **Un prompt también es un *Runnable*** (sección 4): se puede invocar directamente.

Pruébalo (sin clave):

```python
from langchain_core.prompts import ChatPromptTemplate

p = ChatPromptTemplate.from_messages(
    [("system", "Políticas: {politicas}"), ("human", "{pregunta}")]
).partial(politicas="Devoluciones hasta 14 días antes.")

print(p.input_variables)                       # ['pregunta']
print(p.invoke({"pregunta": "¿Puedo devolver?"}).to_messages())
# [SystemMessage(content='Políticas: Devoluciones hasta 14 días antes.'), HumanMessage(content='¿Puedo devolver?')]
```

> **Ojo con las llaves.** Como `{` y `}` marcan variables, si el texto de las políticas tuviera llaves literales habría que escribirlas `{{` `}}`. Con `.partial` no hay problema: el valor se inserta tal cual y no se interpreta como plantilla.

---

## 4. LCEL: encadenar con `|`

**LCEL** (*LangChain Expression Language*) es la forma de componer piezas. Casi todo en LangChain es un **`Runnable`**: prompts, modelos, parsers, herramientas e incluso agentes. Todos comparten la misma interfaz:

| Método | Qué hace |
|---|---|
| `.invoke(x)` | Una entrada → una salida |
| `.batch([x1, x2])` | Varias entradas, en paralelo |
| `.stream(x)` | Devuelve la salida en trozos según se genera |
| `.ainvoke`, `.abatch`, `.astream` | Versiones asíncronas |

El operador **`|`** une dos Runnables en una **`RunnableSequence`**: la salida del primero es la entrada del segundo. Es el corazón del paso 1 ([llm/chain.py](../llm/chain.py)):

```python
def construir_cadena_politicas() -> Runnable:
    prompt = ChatPromptTemplate.from_messages([...]).partial(politicas=cargar_politicas())
    modelo = crear_modelo()
    parser = StrOutputParser()
    return prompt | modelo | parser
```

Lo que viaja por la cadena:

```
{"pregunta": "¿Cuál es la política de devoluciones?"}
      │  ChatPromptTemplate
      ▼
[SystemMessage(reglas + políticas), HumanMessage("¿Cuál es la política…?")]
      │  ChatOpenAI
      ▼
AIMessage(content="Puedes solicitar la devolución hasta 14 días antes…")
      │  StrOutputParser
      ▼
"Puedes solicitar la devolución hasta 14 días antes…"
```

El endpoint `POST /politicas` solo hace `cadena.invoke({"pregunta": ...})`.

Pruébalo con un modelo falso (sin clave):

```python
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([("human", "{pregunta}")])
cadena = prompt | FakeListChatModel(responses=["uno", "dos"]) | StrOutputParser()

print(type(cadena).__name__)                                  # RunnableSequence
print(cadena.invoke({"pregunta": "a"}))                       # 'uno'
print(cadena.batch([{"pregunta": "a"}, {"pregunta": "b"}]))   # ['dos', 'uno']  (el modelo falso sigue la lista y vuelve a empezar)
```

Y con el modelo real, en *streaming* (necesita clave):

```python
from llm.chain import obtener_cadena_politicas

for trozo in obtener_cadena_politicas().stream({"pregunta": "¿Puedo cambiar el titular?"}):
    print(trozo, end="", flush=True)
```

Fíjate en que el *streaming* funciona a través de toda la cadena sin escribir nada especial: el parser va pasando cada trozo de texto según llega.

> **¿Por qué `lru_cache` en `obtener_cadena_politicas`?** Construir la cadena lee `policies.md` y crea el cliente HTTP de OpenAI. Hacerlo una sola vez y reutilizarla es más barato. Los Runnables no guardan estado entre llamadas, así que se pueden compartir sin problema.

---

## 5. Output parsers

El modelo devuelve un `AIMessage`, pero a la API le interesa un `str`. Un **output parser** transforma esa salida.

- **`StrOutputParser`** (el que usa el proyecto) devuelve `message.content` como texto.
- Hay otros: `JsonOutputParser`, `PydanticOutputParser`… Para obtener datos estructurados, la opción moderna es `modelo.with_structured_output(MiModeloPydantic)`.

Sin parser, `/politicas` tendría que hacer `respuesta.content` a mano. Con el parser dentro de la cadena, quien la usa recibe directamente lo que necesita.

---

## 6. Herramientas con `@tool`

Una **herramienta** es una función que el modelo puede pedir que se ejecute. El decorador **`@tool`** convierte una función Python en una herramienta que LangChain sabe describir al modelo. Así es `buscar_eventos` en [tools/eventhub_tools.py](../tools/eventhub_tools.py):

```python
from langchain_core.tools import tool

@tool
def buscar_eventos(ciudad: str | None = None, categoria: str | None = None) -> str:
    """Busca eventos de EventHub en el catálogo.

    Úsala siempre que el usuario pregunte por eventos, fechas, precios o
    disponibilidad. Ambos filtros son opcionales y no distinguen mayúsculas ni tildes.

    Args:
        ciudad: Ciudad del evento, p. ej. "Valencia", "Madrid".
        categoria: Tipo de evento, p. ej. "concierto", "teatro", "deporte", "comedia", "danza".
    ...
    """
    return _json(eventos.buscar_eventos(ciudad=ciudad, categoria=categoria))
```

**Qué lee el modelo.** `@tool` toma tres cosas de la función:

| De la función | Se convierte en | Lo usa el modelo para |
|---|---|---|
| Nombre (`buscar_eventos`) | `name` | Saber a qué herramienta llamar |
| Docstring | `description` | **Decidir cuándo** usarla |
| *Type hints* (`str \| None = None`, `int`) | Esquema JSON de los argumentos | **Saber cómo** llamarla |

Pruébalo (sin clave):

```python
import json
from tools.eventhub_tools import buscar_eventos, reservar_entradas
from langchain_core.utils.function_calling import convert_to_openai_tool

print(buscar_eventos.name)    # buscar_eventos
print(json.dumps(convert_to_openai_tool(reservar_entradas)["function"]["parameters"]))
# {"properties": {"id_evento": {"type": "string"}, "cantidad": {"type": "integer"}},
#  "required": ["id_evento", "cantidad"], "type": "object"}

# Una herramienta también es un Runnable: se invoca con un dict de argumentos
print(buscar_eventos.invoke({"ciudad": "valencia", "categoria": "Concierto"})[:80])
```

Ese esquema JSON es exactamente lo que se envía a OpenAI. Por eso **el docstring es parte del prompt**: si es confuso, el modelo usará mal la herramienta. Fíjate en cómo `consultar_pedido` indica en su docstring que hay que pedir el email si falta. Así, en el turno 4 de la [demo](conversacion_prueba.md), el modelo no se inventa el email.

**Herramientas finas.** Las herramientas del proyecto no contienen lógica de negocio: delegan en [services/](../services/). Así:

- `services/` se prueba con pytest sin LangChain ([tests/test_services.py](../tests/test_services.py)).
- La herramienta se ocupa solo de adaptar: recibe los argumentos del modelo y devuelve texto o JSON que el modelo entiende.
- Los errores esperables se convierten en resultados, no en excepciones. `reservar_entradas` captura `ErrorReserva` y devuelve `{"ok": false, "error": "..."}`, y así el modelo puede explicárselo al usuario.

---

## 7. Agentes con `create_agent`

Una cadena sigue siempre los mismos pasos. Un **agente** decide en cada momento qué hacer: el modelo puede responder o pedir una herramienta, ver el resultado y volver a decidir. Este bucle se llama **ReAct**:

```
            ┌──────────────────────────────────────┐
            ▼                                      │
 mensajes ─► modelo ─► ¿tool_calls? ── sí ─► ejecutar herramientas ─┘
                          │
                          no
                          ▼
                    respuesta final
```

En LangChain v1 se crea con **`create_agent`** ([llm/agent.py](../llm/agent.py)):

```python
from langchain.agents import create_agent

def construir_agente(modelo=None):
    return create_agent(
        model=modelo or crear_modelo(),
        tools=HERRAMIENTAS,                      # [buscar_eventos, consultar_pedido, reservar_entradas]
        system_prompt=construir_system_prompt(), # reglas + policies.md
        checkpointer=checkpointer,               # sección 8
        middleware=[recortar_mensajes,           # sección 9
                    HumanInTheLoopMiddleware(...)],  # sección 10
    )
```

`create_agent` devuelve un **grafo de LangGraph compilado** (que también es un Runnable). Puedes ver sus nodos:

```python
from langchain_core.messages import AIMessage
from llm.agent import construir_agente
from tests.test_agent_flow import ModeloGuionizado

ag = construir_agente(ModeloGuionizado(messages=iter([AIMessage("hola")])))
print(list(ag.get_graph().nodes))
# ['__start__', 'model', 'tools', 'HumanInTheLoopMiddleware.after_model', '__end__']
```

**Qué pasa en un turno real.** Esta es la secuencia de mensajes que se guarda cuando el usuario pregunta «¿Qué conciertos hay en Valencia?» (turno 2 de la demo):

```
HumanMessage  "¿Qué conciertos hay en Valencia?"
AIMessage     content=""  tool_calls=[buscar_eventos({"ciudad": "Valencia", "categoria": "concierto"})]
ToolMessage   '[{"id": "EV001", ...}, ...]'      (tool_call_id enlaza con la llamada)
AIMessage     "Estos son los conciertos disponibles en Valencia: …"
```

**El modelo decide, no el código.** En el proyecto no hay ningún `if "concierto" in mensaje`. El modelo elige la herramienta a partir de los docstrings y del prompt de sistema. En el turno 1 («política de devoluciones») no llama a ninguna porque la información ya está en el prompt.

**Prompt de sistema del agente.** Además de las políticas, incluye reglas de comportamiento. Las más instructivas:

- «Para cualquier dato de eventos usa SIEMPRE `buscar_eventos`; no respondas de memoria». Sin esta regla, tras una reserva el modelo podría repetir el stock antiguo que ya vio en un turno anterior. Gracias a ella, el turno 7 vuelve a consultar y ve 38.
- «Llama DIRECTAMENTE a `reservar_entradas`… NO pidas confirmación por texto». Se añadió porque el modelo preguntaba «¿Confirmas?» por su cuenta y no llamaba a la herramienta, de modo que la confirmación real (sección 10) nunca llegaba a activarse. **Lección:** el prompt tiene que explicar al modelo qué partes del flujo controla el sistema.

---

## 8. Memoria: checkpointer y `thread_id`

Los modelos no tienen memoria: cada llamada solo «ve» los mensajes que recibe. Para que el agente recuerde, LangGraph guarda el **estado** del grafo (la lista `messages`) después de cada paso, usando un **checkpointer** ([memory/checkpointer.py](../memory/checkpointer.py)):

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
```

Cada conversación se identifica por un **`thread_id`** que se pasa en `config`:

```python
config = {"configurable": {"thread_id": "conversacion-1"}}
agente.invoke({"messages": [{"role": "user", "content": "¿Qué conciertos hay en Valencia?"}]}, config)
agente.invoke({"messages": [{"role": "user", "content": "¿Y el más barato de esos?"}]}, config)
#                         ↑ solo se envía el mensaje nuevo: el checkpointer añade el historial
```

Con el mismo `thread_id`, el segundo `invoke` empieza con todo el historial anterior. Por eso «esos» se entiende. Con un `thread_id` distinto el agente empieza de cero, como demuestra el turno 9 de la [demo](conversacion_prueba.md).

Para inspeccionar el estado guardado, como hace [llm/agent.py](../llm/agent.py):

```python
estado = agente.get_state(config)
estado.values["messages"]   # historial completo de ese thread
estado.interrupts           # interrupciones pendientes (sección 10)
```

> **`InMemorySaver` es para desarrollo**: vive en la RAM del proceso y se pierde al reiniciar. En producción se usa un checkpointer persistente, por ejemplo con SQLite o Postgres. Basta con cambiar esa línea.

> **¿Por qué no `ConversationBufferMemory`?** Si has visto tutoriales antiguos, las clases `*Memory` y `RunnableWithMessageHistory` eran la forma de hacerlo en LangChain 0.x. En v1, la memoria de los agentes es el checkpointer de LangGraph.

---

## 9. Middleware: controlar lo que ve el modelo

Las conversaciones largas tienen dos problemas: cuestan más tokens y pueden superar el contexto del modelo. El proyecto envía **solo los últimos 10 mensajes**. Para eso usa un **middleware**, un mecanismo de LangChain v1 para engancharse en puntos del bucle del agente:

| Gancho | Cuándo se ejecuta | Qué puede hacer |
|---|---|---|
| `before_agent` / `after_agent` | Al empezar o terminar la invocación | Preparar o limpiar estado |
| `before_model` / `after_model` | Antes o después de cada llamada al modelo | **Modificar el estado** (lo que se guarda) |
| `wrap_model_call` | **Envuelve** la llamada al modelo | Modificar la **petición** (lo que ve el modelo), reintentar, cambiar de modelo… |
| `wrap_tool_call` | Envuelve la ejecución de una herramienta | Reintentos, control de errores… |

El recorte del proyecto ([memory/middleware.py](../memory/middleware.py)):

```python
from langchain.agents.middleware import wrap_model_call
from memory.trim import recortar_historial

@wrap_model_call
def recortar_mensajes(request, handler):
    return handler(request.override(messages=recortar_historial(request.messages)))
```

- `request` es un `ModelRequest` con `messages`, `system_message`, `tools`, `model`…
- `request.override(...)` crea una copia con los campos cambiados, sin modificar el original.
- `handler(request)` ejecuta la llamada real al modelo (o el siguiente middleware).

**¿Por qué `wrap_model_call` y no `before_model`?** Es la decisión de diseño más sutil del proyecto:

- Lo que devuelve `before_model` es una **actualización del estado**. La lista `messages` usa el reducer `add_messages`, que **añade** mensajes en vez de reemplazarlos. Para recortar habría que borrar mensajes con `RemoveMessage`, y eso los borraría **también del checkpointer**: el historial guardado se perdería.
- `wrap_model_call` cambia solo **lo que se envía al modelo** en esa llamada. El checkpointer conserva todo.

Compruébalo: con 7 turnos, el estado guarda 14 mensajes, pero el modelo recibe como máximo 11 (10 más el *system*).

**Los mensajes de herramienta huérfanos.** Cortar «los últimos 10» sin más puede romper la conversación. OpenAI exige que cada `ToolMessage` vaya precedido del `AIMessage` con su `tool_call`. [memory/trim.py](../memory/trim.py) lo resuelve:

```python
def recortar_historial(mensajes, maximo=10):
    ventana = list(mensajes[-maximo:])
    inicio = 0
    while inicio < len(ventana) and isinstance(ventana[inicio], ToolMessage):
        inicio += 1               # el AIMessage que las pidió se quedó fuera → descartarlas
    return ventana[inicio:]
```

Es una **función pura**: no depende de LangChain para ejecutarse y se prueba con todas las longitudes posibles en [tests/test_trim.py](../tests/test_trim.py). **Patrón recomendado:** la lógica va en funciones normales y el middleware solo las conecta.

> LangChain trae middlewares ya hechos con la misma idea: `SummarizationMiddleware` (resume lo antiguo en vez de cortarlo), `ContextEditingMiddleware`, `ModelRetryMiddleware`, `PIIMiddleware`… Están en `langchain.agents.middleware`.

---

## 10. Human in the loop: interrupciones y `Command`

Algunas acciones no deberían ejecutarse sin que una persona las apruebe. Reservar entradas cambia datos, así que en el proyecto requiere confirmación. LangChain lo resuelve con **`HumanInTheLoopMiddleware`** ([llm/agent.py](../llm/agent.py)):

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

HumanInTheLoopMiddleware(
    interrupt_on={"reservar_entradas": {"allowed_decisions": ["approve", "reject"]}},
    description_prefix="La reserva necesita confirmación",
)
```

Debajo hay un mecanismo de LangGraph, las **interrupciones**:

1. El modelo devuelve un `AIMessage` con `tool_calls=[reservar_entradas(...)]`.
2. El middleware (nodo `after_model`, que viste en la sección 7) ve que esa herramienta está en `interrupt_on` y llama a `interrupt(...)`.
3. **El grafo se detiene**. El estado, incluida la petición pendiente, queda guardado en el checkpointer. Por eso las interrupciones **necesitan un checkpointer**.
4. `invoke` termina y el código lee la petición:

   ```python
   interrupciones = agente.get_state(config).interrupts
   interrupciones[0].value["action_requests"]
   # [{"name": "reservar_entradas", "args": {"id_evento": "EV002", "cantidad": 2}, "description": "..."}]
   ```

   La API la devuelve como `{"estado": "pendiente_confirmacion", ...}`.
5. Más tarde, quizá en otra petición HTTP, se **reanuda** con un `Command`:

   ```python
   from langgraph.types import Command

   agente.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config)
   # o bien
   agente.invoke(Command(resume={"decisions": [{"type": "reject", "message": "El usuario ha rechazado la reserva."}]}), config)
   ```

   - **approve**: la herramienta se ejecuta y el modelo informa del resultado.
   - **reject**: no se ejecuta. El modelo recibe un `ToolMessage` de rechazo y responde en consecuencia.
   - También existen `edit` (cambiar los argumentos antes de ejecutar) y `respond` (contestar en lugar de la herramienta). El proyecto solo permite approve y reject.

Esta es la función `confirmar()` de [llm/agent.py](../llm/agent.py), que usa `POST /chat/confirmar`.

> **Modo `batched` frente a `per_call`.** En la versión instalada, el modo por defecto (`batched`) genera **una** interrupción por turno con una lista de acciones, y se responde con una lista `decisions` en el mismo orden. Existe `interrupt_mode="per_call"`, con una interrupción por cada herramienta, que según la documentación pasará a ser el modo por defecto en la próxima versión mayor. Lo comprobamos leyendo el código fuente instalado, no de memoria.

---

## 11. Probar sin gastar: modelos falsos

Llamar a OpenAI en los tests es lento, cuesta dinero y no es determinista. `langchain-core` incluye **modelos falsos** que se comportan como un modelo de chat con respuestas guionizadas:

| Clase | Uso en el proyecto |
|---|---|
| `FakeListChatModel(responses=[...])` | Devuelve textos en orden. [tests/test_chain.py](../tests/test_chain.py) lo usa para probar la cadena |
| `GenericFakeChatModel(messages=iter([...]))` | Devuelve **mensajes completos**, incluidos `AIMessage` con `tool_calls`. Sirve para guionizar un agente |

El modelo guionizado de [tests/test_agent_flow.py](../tests/test_agent_flow.py):

```python
class ModeloGuionizado(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self          # create_agent llama a bind_tools; el modelo falso lo ignora

ag = construir_agente(ModeloGuionizado(messages=iter([
    AIMessage(content="", tool_calls=[{"id": "c2", "name": "reservar_entradas",
                                       "args": {"id_evento": "EV002", "cantidad": 2}}]),
    AIMessage("Reserva hecha."),
])))
```

Con esto se prueba **todo el agente de verdad** (herramientas reales, checkpointer, middleware de recorte, interrupción y `Command`) sin red. El único elemento simulado son las decisiones del modelo.

**Truco de diseño:** `construir_agente(modelo=None)` recibe el modelo como parámetro opcional (*inyección de dependencias*). En producción usa `crear_modelo()` y en los tests el falso. La cadena se prueba igual, sustituyendo `crear_modelo` con `monkeypatch`.

---

## 12. Buenas prácticas que sigue el proyecto

| Práctica | Dónde | Por qué |
|---|---|---|
| Un único punto que crea el modelo | [llm/models.py](../llm/models.py) | Cambiar de modelo o de parámetros en un solo sitio y sustituirlo en los tests |
| Herramientas finas y lógica en `services/` | [tools/](../tools/), [services/](../services/) | Lógica probable sin LLM y herramientas fáciles de leer |
| Docstrings pensados para el modelo | [tools/eventhub_tools.py](../tools/eventhub_tools.py) | El docstring **es** la documentación que lee el modelo |
| Errores de negocio como resultado, no como excepción | `reservar_entradas` | El modelo puede explicar el error al usuario |
| No filtrar información sensible | `consultar_pedido` | El mismo mensaje si el pedido no existe o el email es otro |
| Datos en el prompt solo si son estables | `policies.md` en el *system*. Eventos con herramienta | El stock cambia y no debe responderse de memoria |
| Recortar lo que ve el modelo, no lo que se guarda | [memory/middleware.py](../memory/middleware.py) | Ahorra tokens sin perder historial |
| Confirmación humana para acciones con efectos | `HumanInTheLoopMiddleware` | El modelo puede equivocarse con los argumentos |
| Comprobar la API instalada | Todo el proyecto | LangChain cambia entre versiones: `inspect.signature`, el código fuente, `help()` |
| Tests sin red con modelos falsos | [tests/](../tests/) | Rápidos, gratuitos y deterministas |

---

## 13. Ejercicios

Ordenados de menos a más difícil. Todos se pueden hacer sobre este repositorio.

1. **Streaming en la cadena.** Añade un endpoint `POST /politicas/stream` que devuelva la respuesta de la cadena con `StreamingResponse` de FastAPI usando `cadena.stream(...)`.
2. **Nueva herramienta.** Crea `detalle_evento(id_evento: str)` que devuelva un evento por su id (ya existe `services.eventos.obtener_evento`). Escribe un buen docstring y comprueba en la página de prueba que el modelo la usa cuando preguntas por un evento concreto.
3. **Filtro de precio.** Añade `precio_max: float | None = None` a `buscar_eventos`, primero en el servicio con su test y después en la herramienta. Pregunta «conciertos en Valencia por menos de 40 €» y comprueba que el modelo rellena el nuevo argumento.
4. **Salida estructurada.** Haz una cadena que clasifique la intención del usuario (`politica`, `eventos`, `pedido`, `otro`) con `modelo.with_structured_output(...)` y un modelo Pydantic.
5. **Resumen en vez de recorte.** Sustituye `recortar_mensajes` por `SummarizationMiddleware` y compara qué recuerda el agente en una conversación de más de 10 mensajes.
6. **Permitir editar.** Añade `"edit"` a `allowed_decisions` de `reservar_entradas` y un endpoint que reanude con `{"type": "edit", "edited_action": {"name": "reservar_entradas", "args": {...}}}` para cambiar la cantidad antes de aprobar.
7. **Memoria persistente.** Cambia `InMemorySaver` por un checkpointer de SQLite (paquete `langgraph-checkpoint-sqlite`) y comprueba que la conversación sobrevive a un reinicio del servidor.
