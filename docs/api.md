# Referencia de la API

URL base: **`http://127.0.0.1:9000`**. Todas las peticiones y respuestas usan JSON (UTF-8). La documentación interactiva (Swagger) está en [`/docs`](http://127.0.0.1:9000/docs) y el esquema OpenAPI en `/openapi.json`.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Página web de prueba del chatbot |
| `GET` | `/health` | Estado del servidor |
| `POST` | `/politicas` | Paso 1: pregunta sobre políticas (cadena LCEL, sin memoria) |
| `POST` | `/chat` | Pasos 2 y 3: mensaje al agente (memoria + herramientas) |
| `POST` | `/chat/confirmar` | Aprueba o rechaza una acción pendiente |

---

## `GET /health`

```bash
curl http://127.0.0.1:9000/health
```
```json
{"status": "ok"}
```

## `POST /politicas`

| Campo | Tipo | Obligatorio |
|---|---|---|
| `pregunta` | string (no vacío) | Sí |

```bash
curl -X POST http://127.0.0.1:9000/politicas \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Puedo cambiar el titular de mi entrada?"}'
```
```json
{"respuesta": "Sí, puedes cambiar el titular una sola vez por entrada, sin coste, hasta 48 horas antes del evento…"}
```

## `POST /chat`

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `thread_id` | string (no vacío) | Sí | Identifica la conversación. Con el mismo valor, el agente recuerda los turnos anteriores |
| `mensaje` | string (no vacío) | Sí | Texto del usuario |

**Respuesta normal** (los textos de los ejemplos son orientativos: el modelo redacta cada vez de forma distinta):

```bash
curl -X POST http://127.0.0.1:9000/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "t1", "mensaje": "¿Qué conciertos hay en Valencia?"}'
```
```json
{
  "respuesta": "Estos son los conciertos en Valencia: …",
  "herramientas": [
    {"nombre": "buscar_eventos", "argumentos": {"ciudad": "Valencia", "categoria": "concierto"}}
  ]
}
```

`herramientas` lista las herramientas que el agente ha llamado en este turno, en orden.

**Respuesta con confirmación pendiente** (el agente quiere reservar):

```bash
curl -X POST http://127.0.0.1:9000/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "t1", "mensaje": "Resérvame 2 entradas del más barato"}'
```
```json
{
  "estado": "pendiente_confirmacion",
  "accion": "reservar_entradas",
  "argumentos": {"id_evento": "EV002", "cantidad": 2},
  "acciones": [{"accion": "reservar_entradas", "argumentos": {"id_evento": "EV002", "cantidad": 2}}],
  "herramientas": [
    {"nombre": "buscar_eventos", "argumentos": {"ciudad": "Valencia", "categoria": "concierto"}},
    {"nombre": "reservar_entradas", "argumentos": {"id_evento": "EV002", "cantidad": 2}}
  ]
}
```

`accion` y `argumentos` describen la primera acción pendiente. `acciones` las incluye todas, por si el modelo pidiera varias reservas a la vez. **La reserva aún no se ha hecho.**

## `POST /chat/confirmar`

| Campo | Tipo | Obligatorio |
|---|---|---|
| `thread_id` | string | Sí |
| `aprobar` | boolean | Sí |

```bash
curl -X POST http://127.0.0.1:9000/chat/confirmar \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "t1", "aprobar": true}'
```
```json
{
  "respuesta": "He reservado 2 entradas para Jazz al Atardecer. Total: 45 €. Quedan 38 entradas.",
  "herramientas": [{"nombre": "reservar_entradas", "argumentos": {"id_evento": "EV002", "cantidad": 2}}]
}
```

Con `"aprobar": false` la reserva no se ejecuta y la respuesta indica que se ha cancelado (`herramientas` queda vacío). La respuesta tiene el mismo formato que `/chat`, así que en teoría podría traer otra confirmación pendiente.

## Errores

| Código | Cuándo | `detail` |
|---|---|---|
| 409 | `/chat` con una acción pendiente de confirmar en ese thread | «Hay una acción pendiente de confirmar en esta conversación: usa /chat/confirmar.» |
| 409 | `/chat/confirmar` sin nada pendiente | «No hay ninguna acción pendiente de confirmar en esta conversación.» |
| 422 | Cuerpo inválido (falta un campo, string vacío, tipo incorrecto) | Detalle de validación de FastAPI |
| 503 | Falta `OPENAI_API_KEY` | «Falta OPENAI_API_KEY: copia .env.example a .env, pon tu clave y reinicia el servidor.» |
| 500 | Error del proveedor (clave inválida, modelo inexistente, parámetro no soportado…) | Ver el log de uvicorn |

Los errores de negocio (evento inexistente, sin stock, pedido no verificado) **no** son errores HTTP. La herramienta los devuelve al modelo y este se los explica al usuario en `respuesta`.
