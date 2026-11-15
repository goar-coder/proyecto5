# Documentación del Asistente EventHub

El Asistente EventHub atiende a los clientes de EventHub, una plataforma (ficticia) de venta de entradas. Hace tres cosas:

- **Responde sobre las políticas** de la empresa (devoluciones, cambios de titular, cancelaciones…), solo con lo que está escrito en ellas.
- **Recuerda la conversación**, así que entiende preguntas como «¿y el más barato de esos?».
- **Usa herramientas que elige el propio modelo** para buscar eventos, consultar pedidos y reservar entradas. Antes de reservar pide confirmación a una persona.

Está hecho con **LangChain v1** (`create_agent`), **LangGraph** (checkpointer e interrupciones), un modelo de **OpenAI** y **FastAPI**. Se sirve en el **puerto 9000**.

## Índice

| Documento | Contenido |
|---|---|
| [tutorial_langchain.md](tutorial_langchain.md) | **Tutorial de LangChain** explicado con el código de este proyecto (modelos, prompts, LCEL, herramientas, agentes, memoria, middleware, human in the loop, tests) |
| [tutorial_langgraph.md](tutorial_langgraph.md) | **Tutorial de LangGraph**: grafos de estado, reducers, aristas condicionales, agente ReAct a mano, checkpointers, `interrupt` y `Command`, viaje en el tiempo, streaming, `Send`, subgrafos, contexto y tests |
| [arquitectura.md](arquitectura.md) | Capas, carpetas, flujo de una petición y configuración |
| [funcionamiento.md](funcionamiento.md) | Los tres pasos en detalle: cadena LCEL, memoria y herramientas con confirmación humana |
| [api.md](api.md) | Referencia de endpoints, formatos, ejemplos con `curl` y errores |
| [datos.md](datos.md) | Formato de `events.json`, `orders.json` y `policies.md` |
| [pruebas.md](pruebas.md) | Tests, demo de entrega y página web de prueba |
| [conversacion_prueba.md](conversacion_prueba.md) | Transcripción real generada por la demo |
| **Versión LangGraph** | |
| [langgraph_pruebas.md](langgraph_pruebas.md) | **Cómo probar** las 4 versiones del grafo (`grafos/`), los diagramas y la demo de entrega |
| [cambios_codigo.md](cambios_codigo.md) | Cambios de código de la versión LangGraph: ficheros nuevos y modificados y decisiones de diseño |
| [cambios_datos.md](cambios_datos.md) | Cambios en `data/` para la versión LangGraph (pedidos `EH-xxxx`, conciertos en Madrid) |
| [entrega_langgraph.md](entrega_langgraph.md) | Prueba de entrega generada por `scripts/demo_grafos.py`: diagramas v1 y v4, herramientas encadenadas y `get_state` |

## Inicio rápido

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # pon tu OPENAI_API_KEY
python main.py                # o: uvicorn main:app --reload --port 9000
```

| URL | Para qué |
|---|---|
| <http://127.0.0.1:9000/> | Página de prueba del chatbot (con mensajes de ejemplo) |
| <http://127.0.0.1:9000/chat-libre> | Página de prueba del chatbot sin mensajes de ejemplo |
| <http://127.0.0.1:9000/docs> | Swagger UI (documentación interactiva de la API) |
| <http://127.0.0.1:9000/health> | Comprobación de que el servidor está vivo |
