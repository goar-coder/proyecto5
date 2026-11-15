# Arquitectura

## Capas

La aplicación está separada en capas, y cada capa solo llama a la de debajo:

```
            navegador / curl / demo
                     │  HTTP (puerto 9000)
                     ▼
  api/        FastAPI: valida la entrada (Pydantic), traduce errores a HTTP
                     │
                     ▼
  llm/        cadena LCEL (paso 1) y agente create_agent (pasos 2 y 3)
     │   └── memory/   checkpointer + middleware de recorte
     ▼
  tools/      herramientas @tool: finas, solo adaptan a texto/JSON
                     │
                     ▼
  services/   lógica de negocio: filtrar eventos, verificar pedidos, reservar
                     │
                     ▼
  data/       events.json · orders.json · policies.md
```

- **`llm/` es el único sitio que habla con OpenAI.** El modelo se crea en [llm/models.py](../llm/models.py) (`crear_modelo`). La cadena y el agente lo reciben de ahí, y los tests lo sustituyen por un modelo falso.
- **`services/` no sabe nada de LangChain.** Son funciones Python normales que se pueden probar solas. Las herramientas de `tools/` solo las envuelven con `@tool` y convierten el resultado a JSON.
- **`api/` no tiene lógica.** Recibe el cuerpo, llama a `llm/` y elige el formato de respuesta o el código de error.

## Carpetas y ficheros principales

| Ruta | Responsabilidad |
|---|---|
| [main.py](../main.py) | Crea la app FastAPI (`PUERTO = 9000`). `python main.py` la arranca con recarga automática |
| [api/routes.py](../api/routes.py) | Endpoints `/`, `/health`, `/politicas`, `/chat` y `/chat/confirmar` |
| [api/schemas.py](../api/schemas.py) | Modelos Pydantic de entrada y salida |
| [config/settings.py](../config/settings.py) | Lee `OPENAI_API_KEY`, `OPENAI_MODEL` y `EVENTHUB_DATA_DIR` del entorno o de `.env` |
| [llm/models.py](../llm/models.py) | Crea `ChatOpenAI` (temperature 0) |
| [llm/prompts.py](../llm/prompts.py) | Carga `policies.md` y define las reglas de «no inventar» |
| [llm/chain.py](../llm/chain.py) | Paso 1: cadena `prompt \| modelo \| parser` |
| [llm/agent.py](../llm/agent.py) | Pasos 2 y 3: agente, `enviar_mensaje()` y `confirmar()` |
| [memory/checkpointer.py](../memory/checkpointer.py) | `InMemorySaver` compartido por toda la app |
| [memory/trim.py](../memory/trim.py) | `recortar_historial()`: función pura que deja como mucho 10 mensajes |
| [memory/middleware.py](../memory/middleware.py) | Middleware `wrap_model_call` que aplica el recorte |
| [tools/eventhub_tools.py](../tools/eventhub_tools.py) | `buscar_eventos`, `consultar_pedido` y `reservar_entradas` |
| [services/](../services/) | `eventos.py`, `pedidos.py`, `reservas.py` y `datos.py` (lectura y escritura atómica de JSON) |
| [static/index.html](../static/index.html) | Página de prueba del chatbot (HTML y JS sin dependencias) |
| [scripts/demo_conversacion.py](../scripts/demo_conversacion.py) | Demo de entrega |
| [tests/](../tests/) | pytest, sin llamadas a OpenAI |

## Flujo de una petición a `/chat`

```
POST /chat {thread_id, mensaje}
  │
  ├─ requiere_api_key ............ 503 si no hay OPENAI_API_KEY
  ├─ ¿hay interrupción pendiente en ese thread? ... 409
  │
  └─ agente.invoke({"messages": [mensaje]}, thread_id)
        │  el checkpointer carga el historial guardado de ese thread
        ▼
     ┌─ middleware recortar_mensajes: el modelo ve solo los últimos 10 mensajes
     │  modelo → ¿llama a herramientas?
     │     no ──► respuesta final
     │     sí ──► HumanInTheLoopMiddleware: ¿es reservar_entradas?
     │              sí ──► INTERRUPCIÓN (estado guardado en el checkpointer)
     │              no ──► se ejecuta la herramienta → vuelta al modelo
     └─ (bucle hasta la respuesta final o una interrupción)
        │
        ▼
  respuesta:  {respuesta, herramientas}
         o    {estado: "pendiente_confirmacion", accion, argumentos, ...}
```

`POST /chat/confirmar` reanuda el mismo grafo con `Command(resume=...)`. Si se aprueba, la herramienta se ejecuta. Si se rechaza, el modelo recibe un `ToolMessage` que lo indica y responde en consecuencia.

## Configuración

Variables de entorno, leídas de `.env` si existe:

| Variable | Obligatoria | Por defecto | Uso |
|---|---|---|---|
| `OPENAI_API_KEY` | Sí | – | Clave de OpenAI. Sin ella, los endpoints que usan el modelo responden 503 |
| `OPENAI_MODEL` | No | `gpt-4.1-mini` | Modelo de chat |
| `OPENAI_TEMPERATURE` | No | sin enviar | Temperatura del modelo (en `.env.example`: `0`). Déjala vacía si el modelo no admite `temperature` (p. ej. modelos de razonamiento) |
| `EVENTHUB_DATA_DIR` | No | `./data` | Carpeta de datos. La usan los tests y la demo para trabajar sobre una copia |

`EVENTHUB_DATA_DIR` se lee en cada acceso a datos, no al arrancar, así que se puede cambiar en tiempo de ejecución, que es lo que hacen los tests.

## Limitaciones conocidas

- **La memoria se pierde al reiniciar.** `InMemorySaver` vive en el proceso, y con `--reload` cada cambio de código vacía también las conversaciones. Para producción habría que usar un checkpointer persistente (SQLite o Postgres).
- **Un solo proceso.** El cerrojo de reservas (`threading.Lock`) protege los hilos de un mismo proceso. Con varios *workers* de uvicorn haría falta un bloqueo de fichero o una base de datos.
- **No hay autenticación.** Cualquiera que conozca un `thread_id` puede continuar esa conversación. Los pedidos sí exigen id y email.
