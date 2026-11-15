# Pruebas

## Tests automáticos

```bash
pytest
```

Los tests **no llaman a OpenAI** y no modifican `data/`. La fixture `datos_temporales` ([tests/conftest.py](../tests/conftest.py)) copia `data/` a un directorio temporal y apunta `EVENTHUB_DATA_DIR` a esa copia.

| Fichero | Qué comprueba |
|---|---|
| [tests/test_services.py](../tests/test_services.py) | Filtros de eventos (ciudad, categoría, mayúsculas y tildes, sin filtros, agotados). Pedido con email correcto, incorrecto e inexistente, con el mismo mensaje en los dos últimos casos. Reserva correcta, sin stock, con cantidad inválida (0, -1, `True`, 1.5) y con evento inexistente. Que los datos reales no cambian |
| [tests/test_trim.py](../tests/test_trim.py) | Recorte del historial: nunca más de 10 mensajes y sin `ToolMessage` huérfanos para cualquier longitud de conversación, también con llamadas a herramientas en paralelo |
| [tests/test_chain.py](../tests/test_chain.py) | La cadena LCEL inyecta las políticas y las reglas en el *system* y devuelve `str` (con un modelo falso) |
| [tests/test_agent_flow.py](../tests/test_agent_flow.py) | Agente real con un modelo falso guionizado: búsqueda, interrupción antes de reservar (sin descontar stock), 409 lógico con una acción pendiente, aprobación (descuenta) y rechazo (no descuenta) |
| [tests/test_api.py](../tests/test_api.py) | Endpoints con `TestClient`: página `/`, 503 sin clave, flujo `/chat` → pendiente → 409 → `/chat/confirmar` |

## Demo de entrega

```bash
python scripts/demo_conversacion.py
```

Necesita `OPENAI_API_KEY`. Usa `TestClient` sobre la app real, así que no hace falta arrancar uvicorn, y trabaja sobre una copia temporal de `data/`. Imprime la conversación y la guarda en [conversacion_prueba.md](conversacion_prueba.md).

| Turno | thread_id | Qué demuestra |
|---|---|---|
| 1 | demo-principal | Responde la política de devoluciones sin herramientas |
| 2 | demo-principal | `buscar_eventos` con ciudad y categoría. El agotado aparece como tal |
| 3 | demo-principal | Memoria: «¿y el más barato de esos?» se resuelve con el contexto |
| 4 | demo-principal | `consultar_pedido` con email incorrecto → mensaje genérico |
| 5 | demo-principal | Memoria + `consultar_pedido` con el email correcto → estado |
| 6 / 6b | demo-principal | `reservar_entradas` → `pendiente_confirmacion` → aprobar → stock de 40 a 38, comprobado leyendo el fichero |
| 7 | demo-principal | Vuelve a consultar con la herramienta y ve el stock actualizado |
| 8 | demo-principal | Parking: dice que no tiene la información y no inventa |
| 9 | demo-otro-usuario | Otro thread_id: no recuerda nada de la conversación anterior |

El modelo no es determinista, así que el texto exacto cambia entre ejecuciones.

## Página de prueba

Con el servidor arrancado (`python main.py`), abre <http://127.0.0.1:9000/> ([static/index.html](../static/index.html)):

- **Chat (agente)**: usa `/chat` con el `thread_id` del campo superior. Bajo cada respuesta se ven las herramientas llamadas. Las reservas muestran una tarjeta con **Aprobar / Rechazar** (`/chat/confirmar`) y, mientras está pendiente, no se pueden enviar mensajes nuevos.
- **Nueva conversación**: genera otro `thread_id` para probar que la memoria no se comparte. El último `thread_id` se recuerda en el navegador, pero la memoria del servidor se pierde al reiniciarlo.
- **Solo políticas**: usa `/politicas` (cadena del paso 1, sin memoria).
- **Sugerencias**: botones con los mismos mensajes de la demo.

### Chat libre

<http://127.0.0.1:9000/chat-libre> ([static/chat_libre.html](../static/chat_libre.html)) es la misma página **sin mensajes de ejemplo fijados**, para probar el chat escribiendo lo que quieras. Funciona igual: modos chat y políticas, `thread_id`, Nueva conversación, herramientas llamadas y Aprobar / Rechazar. Guarda su `thread_id` aparte, así que no continúa la conversación de la página principal.

## Prueba manual rápida con curl

```bash
curl -s -X POST localhost:9000/chat -H 'Content-Type: application/json' \
  -d '{"thread_id":"manual","mensaje":"Reserva 1 entrada de Indie Fest Valencia"}'
curl -s -X POST localhost:9000/chat/confirmar -H 'Content-Type: application/json' \
  -d '{"thread_id":"manual","aprobar":false}'
```

Ojo: si apruebas una reserva desde la página o con curl, el servidor modifica el `data/events.json` real. Para restaurarlo: `git checkout data/events.json`.
