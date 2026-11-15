# Funcionamiento: los tres pasos

## Paso 1 — Cadena LCEL sobre políticas

Fichero: [llm/chain.py](../llm/chain.py) · Endpoint: `POST /politicas`

```python
prompt | modelo | parser
```

| Pieza | Qué hace | Entrada → salida |
|---|---|---|
| `ChatPromptTemplate` | Construye los mensajes: un *system* con las reglas y el texto completo de `policies.md` (fijado con `.partial`), y un *human* con `{pregunta}` | `{"pregunta": str}` → lista de mensajes |
| `ChatOpenAI` | Llama al modelo de OpenAI | mensajes → `AIMessage` |
| `StrOutputParser` | Extrae el texto del `AIMessage` | `AIMessage` → `str` |

El operador `|` de LCEL encadena *Runnables*: la salida de cada uno es la entrada del siguiente. La cadena se construye una vez (`lru_cache`) y **no tiene memoria**: cada pregunta es independiente.

Para que el modelo no invente, el mensaje de sistema ([llm/prompts.py](../llm/prompts.py), `REGLAS_POLITICAS`) le obliga a responder solo con las políticas. Si la respuesta no está en ellas, debe decir que no tiene la información y remitir a soporte. Por eso a «¿Hay parking?» responde que no lo sabe.

## Paso 2 — Memoria por conversación

Ficheros: [memory/](../memory/)

### Checkpointer

`InMemorySaver` ([memory/checkpointer.py](../memory/checkpointer.py)) guarda el estado del agente (la lista de mensajes) tras cada paso del grafo. Cada conversación es un **`thread_id`**:

```python
agente.invoke({"messages": [...]}, {"configurable": {"thread_id": "conversacion-1"}})
```

Dos `thread_id` distintos no comparten nada (turno 9 de la [demo](conversacion_prueba.md)). El mismo checkpointer guarda también las interrupciones pendientes del paso 3, y eso es lo que permite reanudar más tarde con `/chat/confirmar`.

### Recorte a 10 mensajes

El historial completo se guarda en el checkpointer, pero **al modelo solo se le envían los últimos 10 mensajes**. El prompt de sistema va aparte y no cuenta.

- [memory/trim.py](../memory/trim.py) — `recortar_historial(mensajes, maximo=10)`: función pura que se prueba sin modelo.
- [memory/middleware.py](../memory/middleware.py) — `recortar_mensajes`: middleware `@wrap_model_call` que hace `request.override(messages=recortar_historial(request.messages))` antes de cada llamada al modelo.

**Por qué `wrap_model_call` y no `before_model`.** Lo que devuelve `before_model` es una actualización del *estado*: se fusiona con el reducer `add_messages` y se guarda en el checkpointer. Recortar ahí obligaría a borrar mensajes del historial con `RemoveMessage`. `wrap_model_call` solo modifica la *petición* al modelo, así que el historial guardado no cambia.

**Mensajes de herramienta huérfanos.** OpenAI rechaza un `ToolMessage` si antes no está el `AIMessage` con el `tool_call` correspondiente. Si el corte de 10 cae justo después de ese `AIMessage`, la ventana empieza con uno o varios `ToolMessage` huérfanos. En ese caso el corte **avanza** hasta el primer mensaje que no sea de herramienta. Se envían menos de 10, nunca más:

```
historial:  … H  AI(tool_calls=[a,b])  T(a)  T(b)  AI  H  AI  H  AI  H  AI  H
                                       └──────── últimos 10 ────────────────┘
ventana:    T(a) T(b) son huérfanos → se descartan → se envían 8
```

## Paso 3 — Herramientas y agente

Ficheros: [tools/eventhub_tools.py](../tools/eventhub_tools.py), [services/](../services/), [llm/agent.py](../llm/agent.py) · Endpoints: `POST /chat`, `POST /chat/confirmar`

### Herramientas

Se definen con `@tool`. El modelo ve el **nombre, los *type hints* y el docstring**, y con eso decide cuándo y cómo usarlas. No hay enrutado por palabras clave. Las herramientas son finas: delegan en `services/` y devuelven JSON.

| Herramienta | Servicio | Comportamiento |
|---|---|---|
| `buscar_eventos(ciudad=None, categoria=None)` | [services/eventos.py](../services/eventos.py) | Filtra sin distinguir mayúsculas ni tildes (`unicodedata`, «Málaga» = «malaga») y ordena por fecha. Devuelve id, nombre, ciudad, categoría, fecha, precio y disponibles (0 = agotado) |
| `consultar_pedido(id_pedido, email)` | [services/pedidos.py](../services/pedidos.py) | Solo da el estado si **id y email coinciden**. Si el pedido no existe o el email es otro, devuelve el **mismo** mensaje genérico, para no revelar qué pedidos existen |
| `reservar_entradas(id_evento, cantidad)` | [services/reservas.py](../services/reservas.py) | Valida que el evento existe, que la cantidad es un entero > 0 y que hay stock. Descuenta y guarda `events.json`. **Requiere confirmación humana** |

**Escritura segura de `events.json`** ([services/datos.py](../services/datos.py), `escribir_json_seguro`). Se escribe en un fichero temporal del mismo directorio, se hace `fsync` y se sustituye con `os.replace`, que es atómico. Si el proceso se corta, el fichero original queda intacto. Además, un `threading.Lock` evita que dos reservas simultáneas lean el mismo stock.

### Agente

```python
create_agent(
    model=crear_modelo(),
    tools=[buscar_eventos, consultar_pedido, reservar_entradas],
    system_prompt=construir_system_prompt(),   # reglas + policies.md
    checkpointer=checkpointer,                 # paso 2
    middleware=[recortar_mensajes,             # paso 2: ≤ 10 mensajes al modelo
                HumanInTheLoopMiddleware(...)],# confirmación de reservas
)
```

Reglas principales del prompt de sistema:

- No inventar. Si no lo sabe, lo dice y remite a soporte.
- Datos de eventos y pedidos **siempre** con herramientas, nunca de memoria (la disponibilidad cambia tras una reserva).
- Para un pedido hacen falta id y email. Si falta alguno, se pide.
- Para reservar se llama directamente a `reservar_entradas`, **sin pedir confirmación por texto**, porque esa confirmación la hace el sistema.

### Confirmación humana (*human in the loop*)

`HumanInTheLoopMiddleware(interrupt_on={"reservar_entradas": {"allowed_decisions": ["approve", "reject"]}})`

1. El modelo decide llamar a `reservar_entradas`.
2. El middleware lanza una **interrupción** de LangGraph antes de ejecutarla. El estado queda guardado en el checkpointer y `/chat` responde `{"estado": "pendiente_confirmacion", "accion", "argumentos"}`.
3. Mientras está pendiente, ese thread no acepta mensajes nuevos (409).
4. `POST /chat/confirmar {thread_id, aprobar}` reanuda con:
   - `Command(resume={"decisions": [{"type": "approve"}]})`: la herramienta se ejecuta y el modelo informa del resultado.
   - `Command(resume={"decisions": [{"type": "reject", "message": "..."}]})`: no se ejecuta. El modelo recibe un `ToolMessage` de rechazo y responde que no ha reservado.

El middleware está en modo *batched* (el modo por defecto en la versión instalada): una interrupción por turno del modelo, con una decisión por cada llamada que necesita aprobación. `confirmar()` aplica la misma decisión a todas.
