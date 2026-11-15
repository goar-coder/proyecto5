# Cambios en el código (versión LangGraph)

Este documento resume qué se añadió y qué se modificó para rehacer el asistente de EventHub como un grafo de LangGraph en cuatro versiones. El código de la sesión 4 (API FastAPI con `create_agent`) **sigue funcionando** y conserva sus tests.

Cómo probar cada versión: [langgraph_pruebas.md](langgraph_pruebas.md). Cambios en los datos: [cambios_datos.md](cambios_datos.md).

## Organización y historial de git

Las cuatro versiones están en la misma rama, en el paquete [grafos/](../grafos/), una por fichero. Así se pueden abrir, ejecutar y comparar a la vez. Cada versión tiene su commit y su tag:

| Commit | Tag | Contenido |
|---|---|---|
| `433cd4d` | – | Datos de prueba y filtro `mes` |
| `09adf11` | `v1-grafo-simple` | Versión 1 |
| `047bb2b` | `v2-chatbot` | Versión 2 |
| `dbcdb6f` | `v3-memoria` | Versión 3 |
| `3388465` | `v4-herramientas` | Versión 4 y `scripts/generar_diagramas.py` |
| (siguiente) | – | Demo de entrega, ajuste del prompt de la v4 y documentación |

`git diff v2-chatbot v3-memoria` muestra exactamente lo que añade cada versión.

## Ficheros nuevos

```
grafos/
  __init__.py             descripción del paquete
  comun.py                prompt_sistema() y guardar_diagrama()
  v1_grafo_simple.py      versión 1
  v2_chatbot.py           versión 2
  v3_memoria.py           versión 3
  v4_herramientas.py      versión 4
  diagramas/v1.mmd        diagrama Mermaid de la v1 (generado)
  diagramas/v4.mmd        diagrama Mermaid de la v4 (generado)
scripts/
  generar_diagramas.py    genera los .mmd sin API key
  demo_grafos.py          prueba de entrega → docs/entrega_langgraph.md
tests/
  test_grafos.py          tests de las 4 versiones (sin OpenAI)
docs/
  langgraph_pruebas.md    cómo probar cada versión
  cambios_datos.md        cambios en data/
  cambios_codigo.md       este documento
  entrega_langgraph.md    salida de la demo (generado)
```

## Ficheros modificados

| Fichero | Cambio |
|---|---|
| [services/eventos.py](../services/eventos.py) | `buscar_eventos(ciudad, categoria, mes=None)`. `mes` tiene formato `AAAA-MM` y se valida con `^\d{4}-(0[1-9]\|1[0-2])$`: si no cumple el formato, lanza `ValueError`. Filtra con `fecha.startswith(mes)` |
| [tools/eventhub_tools.py](../tools/eventhub_tools.py) | La herramienta `buscar_eventos` acepta `mes` (el docstring explica el formato al modelo). Si recibe un `ValueError`, devuelve `{"error": ...}` en JSON para que el modelo pueda corregirse en vez de romper el grafo. El ejemplo de id de pedido pasa a ser `EH-1001` |
| [tests/test_services.py](../tests/test_services.py) | Tests del filtro `mes` y ajustes por los datos nuevos |
| `tests/test_api.py`, `scripts/demo_conversacion.py`, `static/index.html` | `PED-` → `EH-` |
| `README.md`, `docs/README.md`, `docs/datos.md`, `docs/tutorial_langgraph.md` | Referencias nuevas y enlaces a estos documentos |

El agente de la sesión 4 usa la misma herramienta, así que **también gana el filtro `mes`**. Es un parámetro opcional, por lo que no cambia nada de lo que ya hacía.

No hay dependencias nuevas: `langgraph` ya estaba en `requirements.txt`.

---

## Piezas comunes — [grafos/comun.py](../grafos/comun.py)

- **`prompt_sistema(con_herramientas)`**
  - Reutiliza `REGLAS_POLITICAS` y `cargar_politicas()` de [llm/prompts.py](../llm/prompts.py), las mismas reglas de «no inventar» y las mismas políticas que la sesión 4.
  - **Sin herramientas (v2 y v3):** le dice al modelo que no tiene acceso al catálogo ni a los pedidos.
  - **Con herramientas (v4):** añade las reglas para usarlas:
    - usar siempre `buscar_eventos` y `consultar_pedido`;
    - pedir el id **y** el email si falta alguno;
    - usar el filtro `mes` cuando la pregunta hable de un mes;
    - encadenar herramientas cuando haga falta.
  - No incluye las reglas de reserva del agente de la sesión 4, porque aquí no hay reservas.
- **`guardar_diagrama(grafo, nombre)`**: escribe `grafo.get_graph().draw_mermaid()` en `grafos/diagramas/<nombre>.mmd`. Se usa `draw_mermaid()` (texto) y no `draw_mermaid_png()`, porque este último depende por defecto del servicio en línea mermaid.ink.

El modelo se crea siempre con `crear_modelo()` de [llm/models.py](../llm/models.py), así que se usan el mismo `OPENAI_MODEL` y la misma `OPENAI_TEMPERATURE` que en la sesión 4. Cada `construir_grafo(modelo=None)` acepta un modelo falso para los tests.

## Versión 1 — [grafos/v1_grafo_simple.py](../grafos/v1_grafo_simple.py)

- **Estado:** `EstadoV1(TypedDict, total=False)` con `mensaje`, `intencion` (`Literal["eventos","pedido","politicas","otro"]`) y `respuesta`. Con `total=False` se puede invocar solo con `{"mensaje": ...}`.
- **Nodo `clasificar`**:
  - Normaliza el texto con `normalizar()` de [services/eventos.py](../services/eventos.py) (minúsculas y sin tildes).
  - Aplica las reglas en orden: el patrón `EH-<n>` o «pedido»/«compra» → `pedido`; «devol», «reembols», «titular», «cancel», «aplaz», «politica» → `politicas`; «evento», «concierto», «teatro», «entrada»… → `eventos`; si no, `otro`.
  - Las palabras clave se buscan como **inicio de palabra** (`\bdevol`): encajan «devolver» y «devolución», pero no fragmentos sueltos dentro de otras palabras.
- **Nodos de respuesta fija:** `responder_eventos`, `responder_pedido`, `responder_politicas` y `responder_otro`. Los tres primeros son los que pide el enunciado; el cuarto atiende la intención `otro`, que también necesita un destino.
- **Arista condicional:** `add_conditional_edges("clasificar", ruta_por_intencion, {intención: nodo})`. El diccionario hace que el diagrama dibuje cada rama con su etiqueta.

## Versión 2 — [grafos/v2_chatbot.py](../grafos/v2_chatbot.py)

- **Estado:** `MessagesState`. La clave `messages` lleva el reducer `add_messages`, que **añade** los mensajes devueltos por los nodos en lugar de sustituir la lista.
- **Nodo `chatbot`:** `modelo.invoke([SystemMessage(prompt), *messages])`. El mensaje de sistema se antepone en cada llamada y **no se guarda** en el estado.
- **`crear_builder(modelo)`** devuelve el `StateGraph` sin compilar (START → chatbot → END). La v2 lo compila sin checkpointer y la v3 reutiliza ese mismo builder.
- **Bucle en terminal:** como aún no hay checkpointer, el bucle guarda el estado devuelto y lo reenvía en la siguiente llamada. Es justo lo que la v3 delega en LangGraph.

## Versión 3 — [grafos/v3_memoria.py](../grafos/v3_memoria.py)

- `construir_grafo()` = `crear_builder(modelo).compile(checkpointer=InMemorySaver())`. El grafo es idéntico al de la v2; solo cambia la compilación.
- Usa un `InMemorySaver` **propio**, no el de [memory/checkpointer.py](../memory/checkpointer.py) que usa la API, para no mezclar conversaciones.
- **`enviar(grafo, thread_id, texto)`** pasa **solo el mensaje nuevo** con `config={"configurable": {"thread_id": ...}}`. El historial lo aporta el checkpointer.
- **`demo_hilos()`:** tres turnos repartidos entre `hilo-1` y `hilo-2`, que demuestran que no comparten memoria.
- **`formatear_estado()`:** resume `get_state(config)` con el número de mensajes, `next`, `checkpoint_id`, el paso y la lista de mensajes.
- Modo interactivo con `/hilo <id>` y `/historial`, y modo `--demo`.

## Versión 4 — [grafos/v4_herramientas.py](../grafos/v4_herramientas.py)

- **Estado:** `EstadoV4(MessagesState)` con `pasos: int`, las rondas de herramientas del turno actual.
- **Herramientas:** `buscar_eventos` y `consultar_pedido` reutilizadas de la sesión 4. `reservar_entradas` no se incluye, porque el enunciado no la pide y necesitaría confirmación humana.
- **Nodo `chatbot`:** el modelo con `bind_tools(HERRAMIENTAS)` y `prompt_sistema(con_herramientas=True)`.
- **Nodo `herramientas`, escrito a mano** (sin `ToolNode`):
  - Recorre los `tool_calls` del último `AIMessage`, busca cada herramienta por nombre y la ejecuta con `invoke(args)`.
  - Añade un `ToolMessage` por llamada, con su `tool_call_id`.
  - Si la herramienta no existe o lanza una excepción (por ejemplo, porque falta un argumento), crea igualmente un `ToolMessage` con `status="error"`. Así el modelo ve el error y el grafo no se rompe.
  - Devuelve `pasos + 1`.
- **Arista condicional `ruta_tras_chatbot`:**
  - sin `tool_calls` → `fin` (END);
  - con `tool_calls` y `pasos >= MAX_PASOS` → `limite_alcanzado` (nodo `limite`);
  - en otro caso → `usar_herramientas` (nodo `herramientas`).

  Las ramas tienen nombres distintos de los nodos a propósito: si coinciden, `draw_mermaid()` no dibuja la etiqueta.
- **Bucle:** `herramientas → chatbot`. Después de cada ronda, el modelo decide si pide más herramientas (las encadena) o responde.
- **Límite de pasos:** `MAX_PASOS = 5`.
  - **Contador en el estado en vez de `recursion_limit`:** se ve en el diagrama (nodo `limite`) y en `get_state` (`pasos`), y termina con un mensaje amable en lugar de con una excepción `GraphRecursionError`. El `recursion_limit` por defecto de LangGraph (25) sigue actuando como red de seguridad.
  - **El nodo `limite` responde también a las `tool_calls` pendientes**, con un `ToolMessage` de «no ejecutada: límite de pasos alcanzado», antes de añadir el mensaje final. Si no lo hiciera, el historial guardado tendría un `AIMessage` con `tool_calls` sin respuesta, y OpenAI rechazaría el siguiente turno de ese hilo.
  - **Reinicio por turno:** `enviar()` invoca con `{"messages": [humano], "pasos": 0}`. Como `pasos` no tiene reducer, el valor nuevo sustituye al guardado, así que cada turno empieza de cero aunque el hilo tenga memoria.
- Se compila con `InMemorySaver`, igual que la v3, para mantener la memoria por hilo.
- `enviar()` devuelve `{"respuesta", "herramientas", "pasos"}`, con las herramientas llamadas **en ese turno** y en orden. El `formatear_estado()` propio de la v4 muestra también los `tool_calls`, los `ToolMessage` y `pasos`. La v3 no se tocó.

### Ajuste del prompt tras la primera ejecución real

En la primera ejecución de la demo, el modelo buscó los conciertos de Madrid **sin** el filtro `mes` y filtró él mismo los resultados. Se reforzó la regla en `prompt_sistema(True)`: pasar siempre los filtros que conozca y usar `mes` cuando la pregunta hable de un mes, deduciéndolo de la fecha si hace falta. Ahora el modelo llama a `buscar_eventos(..., mes="2026-12")`.

A veces hace una búsqueda previa para averiguar la fecha del evento del pedido, porque `consultar_pedido` devuelve el `id_evento` pero no la fecha. Para que siempre fueran exactamente dos llamadas, habría que añadir los datos del evento a la respuesta de `consultar_pedido`. No se ha hecho, para no cambiar el comportamiento de la sesión 4.

## Scripts

- **[scripts/generar_diagramas.py](../scripts/generar_diagramas.py):** construye la v1 y la v4 (esta última con un modelo falso que acepta `bind_tools`) y escribe los `.mmd`. No necesita clave ni red.
- **[scripts/demo_grafos.py](../scripts/demo_grafos.py):** igual que `demo_conversacion.py`, copia `data/` a un directorio temporal y apunta `EVENTHUB_DATA_DIR` allí. Ejecuta la v1, la v3 y la v4 contra OpenAI y escribe [entrega_langgraph.md](entrega_langgraph.md). Comprueba y marca si en la conversación A se encadenaron `consultar_pedido` y `buscar_eventos`.

## Tests — [tests/test_grafos.py](../tests/test_grafos.py)

Hay 21 tests nuevos para los grafos, más 7 en `test_services.py` para el filtro `mes`. Ninguno llama a OpenAI:
- `ModeloGuionizado` (de `tests/test_agent_flow.py`) devuelve respuestas fijas en orden e ignora `bind_tools`;
- `ModeloQueRecuerda` (nuevo) responde con los mensajes humanos que ha recibido, lo que sirve para comprobar qué historial le llega al modelo en la v2 y la v3.

El detalle de cada test está en [langgraph_pruebas.md](langgraph_pruebas.md#tests-automáticos).
