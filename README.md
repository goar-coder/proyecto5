# Asistente EventHub (LangChain + FastAPI)

> Documentación completa en [docs/](docs/README.md): arquitectura, funcionamiento, API, datos y pruebas.

Asistente de atención al cliente para EventHub, una plataforma de venta de entradas, construido en tres pasos:

1. **Cadena LCEL** que responde sobre las políticas de la empresa (`POST /politicas`).
2. **Memoria** por conversación (`thread_id`) con recorte del historial a 10 mensajes.
3. **Herramientas** que el modelo elige solo (buscar eventos, consultar pedidos y reservar entradas con confirmación humana) (`POST /chat`).

## Puesta en marcha (menos de 5 minutos)

Requisitos: Python 3.11 o superior y una clave de la API de OpenAI.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # y pon tu OPENAI_API_KEY en .env
                                   # (si tu modelo no admite temperature, vacía OPENAI_TEMPERATURE)
uvicorn main:app --reload --port 9000
```

La API escucha en el **puerto 9000** (por defecto uvicorn usaría el 8000, por eso hay que pasar `--port 9000`). También se puede arrancar con `python main.py`, que usa el puerto 9000 sin indicarlo.

### Página de prueba del chatbot

Con el servidor arrancado, abre **<http://127.0.0.1:9000/>** ([static/index.html](static/index.html)). Es un chat sencillo que llama a la API:

- **Modo «Chat (agente)»** (`POST /chat`): conversación con memoria. El campo `thread_id` identifica la conversación; «Nueva conversación» genera otro para comprobar que la memoria no se comparte. En cada respuesta se muestran las herramientas que ha llamado el agente. Cuando quiere reservar aparecen los botones **Aprobar / Rechazar**, que llaman a `POST /chat/confirmar`.
- **Modo «Solo políticas»** (`POST /politicas`): solo la cadena LCEL del paso 1, sin memoria ni herramientas.
- Los botones de sugerencias reproducen los turnos de la demo de entrega.

Para escribir libremente sin mensajes de ejemplo, abre **<http://127.0.0.1:9000/chat-libre>** ([static/chat_libre.html](static/chat_libre.html)). Es la misma página sin los botones de sugerencias y con su propia conversación (otro `thread_id` guardado en el navegador).

### Endpoints

También puedes probarlos en <http://127.0.0.1:9000/docs>:

| Endpoint | Body | Respuesta |
|---|---|---|
| `GET /health` | – | `{"status": "ok"}` |
| `POST /politicas` | `{"pregunta": "..."}` | `{"respuesta": "..."}` (paso 1, sin memoria) |
| `POST /chat` | `{"thread_id": "t1", "mensaje": "..."}` | `{"respuesta", "herramientas"}` o `{"estado": "pendiente_confirmacion", "accion", "argumentos"}` |
| `POST /chat/confirmar` | `{"thread_id": "t1", "aprobar": true}` | reanuda el agente y devuelve la respuesta |

Si `/chat` devuelve `pendiente_confirmacion`, ese thread no acepta mensajes nuevos (responde 409) hasta que se llama a `/chat/confirmar`.

Demo de entrega (conversación de 9 turnos; genera `docs/conversacion_prueba.md`):

```bash
python scripts/demo_conversacion.py
```

La demo trabaja sobre una copia temporal de `data/`, así que se puede repetir sin cambiar el stock real.

Tests (no llaman a OpenAI):

```bash
pytest
```

## Versión LangGraph (grafos/)

El asistente también está rehecho como grafo de LangGraph, en cuatro versiones que crecen una sobre otra (cada una con su tag de git):

| Versión | Ejecutar | Qué añade |
|---|---|---|
| 1 | `python -m grafos.v1_grafo_simple` | Estado `TypedDict`, clasificación por reglas y arista condicional (sin LLM) |
| 2 | `python -m grafos.v2_chatbot` | `MessagesState` y nodo chatbot con el prompt y las políticas |
| 3 | `python -m grafos.v3_memoria --demo` | Checkpointer `InMemorySaver`, `thread_id` y `get_state` |
| 4 | `python -m grafos.v4_herramientas` | Nodo de herramientas a mano, bucle chatbot ↔ herramientas y límite de pasos |

- Diagramas: `python scripts/generar_diagramas.py` (sin API key).
- Prueba de entrega: `python scripts/demo_grafos.py` (genera `docs/entrega_langgraph.md`).

Detalles en [docs/langgraph_pruebas.md](docs/langgraph_pruebas.md), [docs/cambios_codigo.md](docs/cambios_codigo.md) y [docs/cambios_datos.md](docs/cambios_datos.md).

## Cómo funciona

### Paso 1 — Cadena LCEL ([llm/chain.py](llm/chain.py))
`ChatPromptTemplate | ChatOpenAI | StrOutputParser`. El mensaje de sistema incluye el texto de `data/policies.md` y obliga a responder solo con esas políticas. Si la respuesta no está ahí, el modelo dice que no tiene la información y remite a soporte. No guarda memoria.

### Paso 2 — Memoria ([memory/](memory/))
- `InMemorySaver` guarda el historial de cada conversación con su `thread_id`. Las conversaciones no se comparten y se pierden al reiniciar el proceso.
- Un middleware `wrap_model_call` recorta **solo lo que se envía al modelo** a los últimos 10 mensajes, sin contar el prompt de sistema. El historial completo sigue en el checkpointer. Se usa `wrap_model_call` y no `before_model` porque lo que devuelve `before_model` se fusiona con el estado guardado.
- Si el corte deja un `ToolMessage` al principio sin su `AIMessage` con `tool_calls`, el corte se adelanta para no enviar mensajes de herramienta huérfanos. Nunca se envían más de 10.

### Paso 3 — Herramientas y agente ([tools/](tools/), [llm/agent.py](llm/agent.py))
- `buscar_eventos(ciudad, categoria)`: filtra sin distinguir mayúsculas ni tildes.
- `consultar_pedido(id_pedido, email)`: solo devuelve el estado si el email coincide. Si el pedido no existe o el email no coincide, devuelve el **mismo** mensaje genérico.
- `reservar_entradas(id_evento, cantidad)`: valida los datos, descuenta el stock y guarda `events.json` de forma atómica (escribe un fichero temporal y lo reemplaza con `os.replace`).
- `create_agent` con el prompt de sistema (políticas y reglas de no inventar), el checkpointer y dos middlewares: el recorte y `HumanInTheLoopMiddleware`, que interrumpe antes de `reservar_entradas`. `/chat/confirmar` reanuda con `Command(resume={"decisions": [{"type": "approve" | "reject"}]})`.
- No hay enrutado por palabras clave: el modelo decide qué herramienta usar a partir de sus docstrings.

## Estructura

```
api/        endpoints FastAPI y esquemas Pydantic
services/   lógica de negocio: eventos, pedidos, reservas y E/S de JSON
tools/      herramientas @tool (finas, llaman a services/)
llm/        único sitio que habla con OpenAI: modelo, cadena LCEL, agente y prompts
memory/     checkpointer, recorte del historial y su middleware
config/     lectura de OPENAI_API_KEY, OPENAI_MODEL y EVENTHUB_DATA_DIR desde .env
data/       events.json, orders.json, policies.md (datos inventados)
scripts/    demo_conversacion.py (sesión 4), demo_grafos.py y generar_diagramas.py (LangGraph)
static/     index.html: página de prueba del chatbot (GET /)
grafos/     versiones LangGraph v1–v4 y diagramas Mermaid
tests/      pytest (servicios, recorte, flujo del agente con modelo falso, API, grafos)
docs/       conversacion_prueba.md (salida de la demo)
main.py     crea la app FastAPI
```

## Datos de ejemplo útiles

- Conciertos en Valencia: `EV001` (35 €), `EV002` (22,50 €, el más barato), `EV003` (agotado) y `EV004` (45 €).
- Pedido de prueba: `EH-1001` con el email `laura.martinez@example.com`.
- Pedido de la demo LangGraph: `EH-1003` (`ana.gomez@example.com`), concierto en Madrid en diciembre de 2026 (EV013); otros conciertos en Madrid ese mes: EV014 y EV015 (agotado).
- Las políticas no dicen nada de parking ni de accesibilidad, así que el asistente debe responder que no tiene esa información.
