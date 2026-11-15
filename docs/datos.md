# Datos

Todos los datos son inventados y están en [data/](../data/). Se puede usar otra carpeta con la variable `EVENTHUB_DATA_DIR`.

## `events.json` — catálogo de eventos

Lista de 16 objetos:

| Campo | Tipo | Ejemplo |
|---|---|---|
| `id` | string | `"EV002"` |
| `nombre` | string | `"Jazz al Atardecer"` |
| `ciudad` | string | `"Valencia"` |
| `categoria` | string | `"concierto"`, `"teatro"`, `"deporte"`, `"comedia"`, `"danza"` |
| `fecha` | string ISO 8601 | `"2026-12-12T19:30:00"` |
| `precio` | número (EUR) | `22.5` |
| `disponibles` | entero | `40` (`0` = agotado) |

Casos preparados para la demo:

| id | Evento | Ciudad | Precio | Disponibles |
|---|---|---|---|---|
| EV001 | Noche de Rock en el Turia | Valencia | 35 € | 120 |
| **EV002** | **Jazz al Atardecer** (concierto más barato de Valencia) | Valencia | **22,50 €** | 40 |
| EV003 | Gran Gala Sinfónica de Año Nuevo | Valencia | 60 € | **0 (agotado)** |
| EV004 | Indie Fest Valencia | Valencia | 45 € | 300 |
| EV009 | Derbi Madrileño | Madrid | 85 € | **0 (agotado)** |
| EV013 | Rock en la Gran Vía (concierto, 2026-12-11) — evento del pedido EH-1003 | Madrid | 38 € | 150 |
| EV014 | Coros de Navidad en el Retiro (concierto, 2026-12-19) | Madrid | 25 € | 80 |
| EV015 | Sinfonía de Invierno (concierto, 2026-12-27) | Madrid | 55 € | **0 (agotado)** |
| EV016 | Pop Madrid Live (concierto, **2027-01-22**: otro mes) | Madrid | 42 € | 200 |

También hay eventos en Madrid, Sevilla, Barcelona y Málaga de varias categorías.

EV013–EV016 se añadieron para la demo de LangGraph (ver [cambios_datos.md](cambios_datos.md)): con la pregunta «¿mi pedido EH-1003 es para un concierto en Madrid? Si es así, dime otros conciertos en Madrid ese mes» el agente encadena `consultar_pedido` y `buscar_eventos(ciudad="Madrid", categoria="concierto", mes="2026-12")`. EV016 está en enero para comprobar que el filtro `mes` lo excluye.

`reservar_entradas` es lo único que **modifica** este fichero, y lo hace de forma atómica. La demo y los tests trabajan sobre una copia.

## `orders.json` — pedidos

| Campo | Tipo | Ejemplo |
|---|---|---|
| `id_pedido` | string | `"EH-1001"` |
| `email` | string | `"laura.martinez@example.com"` |
| `id_evento` | string | `"EV001"` |
| `cantidad` | entero | `2` |
| `estado` | string | `"pagado"`, `"enviado"`, `"cancelado"`, `"reembolsado"` |
| `fecha_compra` | string ISO 8601 | `"2026-10-15T10:24:00"` |

| Pedido | Email | Estado |
|---|---|---|
| EH-1001 | laura.martinez@example.com | pagado |
| EH-1002 | carlos.ruiz@example.com | enviado |
| EH-1003 | ana.gomez@example.com | pagado (EV013, concierto en Madrid) |
| EH-1004 | javier.lopez@example.com | reembolsado |
| EH-1005 | marta.sanchez@example.com | pagado |
| EH-1006 | pablo.diaz@example.com | cancelado |

El id del pedido y el email se comparan sin distinguir mayúsculas y quitando espacios.

## `policies.md` — políticas

Texto en Markdown que se inserta completo en el prompt de sistema de la cadena y del agente. Secciones:

1. Devoluciones (hasta 14 días antes; gastos de gestión de 1,50 € no reembolsables).
2. Cambio de titular (una vez por entrada, hasta 48 h antes).
3. Cancelación o aplazamiento por el organizador.
4. Entradas agotadas (sin lista de espera).
5. Contacto con soporte (soporte@eventhub.example, +34 900 123 456).

A propósito, **no incluye nada sobre parking ni accesibilidad**. Sirve para comprobar que el asistente responde que no tiene esa información en lugar de inventarla.

Si se edita este fichero, hay que reiniciar el servidor: la cadena y el agente leen las políticas una sola vez al crearse.
