# Cambios en los datos (versión LangGraph)

Los datos de [data/](../data/) se adaptaron para que la prueba de la versión 4 funcione con la pregunta del enunciado:

> «¿Mi pedido **EH-1003** es para un concierto en Madrid? Si es así, dime otros conciertos en Madrid ese mes.»

Con los datos anteriores la pregunta no tenía sentido por tres motivos:
- los pedidos se llamaban `PED-xxxx`;
- el pedido 1003 era de un partido de fútbol;
- no había ningún concierto en Madrid.

Los cambios están en el commit «Datos y filtro mes para la versión LangGraph» (`433cd4d`).

## `orders.json`

| Antes | Después | Cambio |
|---|---|---|
| PED-1001 · laura.martinez · EV001 · pagado | **EH-1001** · laura.martinez · EV001 · pagado | solo el id |
| PED-1002 · carlos.ruiz · EV005 · enviado | **EH-1002** · carlos.ruiz · EV005 · enviado | solo el id |
| PED-1003 · ana.gomez · EV009 (Derbi Madrileño, deporte) · cancelado | **EH-1003** · ana.gomez · **EV013** (Rock en la Gran Vía, concierto en Madrid) · **pagado** | id, evento y estado |
| PED-1004 · javier.lopez · EV007 · reembolsado | **EH-1004** · javier.lopez · EV007 · reembolsado | solo el id |
| PED-1005 · marta.sanchez · EV010 · pagado | **EH-1005** · marta.sanchez · EV010 · pagado | solo el id |
| — | **EH-1006** · pablo.diaz@example.com · EV009 · 2 entradas · **cancelado** | nuevo |

Por qué:
- **Prefijo `EH-`**: coincide con el enunciado, así que la pregunta se puede usar tal cual.
- **EH-1003 → EV013**: el pedido tiene que ser de un concierto en Madrid para que el agente encadene la segunda búsqueda. El email (`ana.gomez@example.com`) no cambia.
- **EH-1006**: al cambiar EH-1003 había desaparecido el único pedido cancelado. Se añade otro, del mismo EV009, para conservar el caso.

## `events.json`

Se añaden 4 conciertos en Madrid. Los eventos EV001–EV012 no cambian, y en total pasan de 12 a 16.

| id | Nombre | Fecha | Precio | Disponibles | Para qué sirve |
|---|---|---|---|---|---|
| EV013 | Rock en la Gran Vía | 2026-12-11 21:00 | 38 € | 150 | Evento del pedido EH-1003 |
| EV014 | Coros de Navidad en el Retiro | 2026-12-19 19:00 | 25 € | 80 | Otro concierto el mismo mes (el más barato) |
| EV015 | Sinfonía de Invierno | 2026-12-27 20:00 | 55 € | **0** | Otro concierto el mismo mes, **agotado** |
| EV016 | Pop Madrid Live | **2027-01-22** 20:30 | 42 € | 200 | Concierto en Madrid de **otro mes**: el filtro `mes="2026-12"` debe excluirlo |

Resultado esperado de la pregunta del enunciado: sí, EH-1003 es un concierto en Madrid (EV013, diciembre de 2026), y los otros conciertos de ese mes son EV014 y EV015 (agotado).

Además, EV002 (Jazz al Atardecer) volvió a tener **40** disponibles. Una reserva hecha desde la página web lo había dejado en 38 y los tests fallaban. Ese cambio va en un commit anterior («arreglo de la version del test»).

## `policies.md`

Sin cambios.

## Ajustes en el resto del proyecto por el cambio de datos

| Fichero | Cambio |
|---|---|
| [tests/test_services.py](../tests/test_services.py) | `PED-1001`/`PED-9999`/`ped-1001` → `EH-…`; el recuento total de eventos pasa de 12 a 16; tests nuevos del filtro `mes` |
| [tests/test_api.py](../tests/test_api.py) | `PED-1001` → `EH-1001` en la comprobación de `/chat-libre` |
| [tools/eventhub_tools.py](../tools/eventhub_tools.py) | Ejemplo del docstring de `consultar_pedido`: `"EH-1001"` |
| [scripts/demo_conversacion.py](../scripts/demo_conversacion.py) | Turno 4 de la demo de la sesión 4: `EH-1001` |
| [static/index.html](../static/index.html) | Botón de sugerencia: `EH-1001` |
| [README.md](../README.md), [docs/datos.md](datos.md), [docs/tutorial_langgraph.md](tutorial_langgraph.md) | Referencias a `EH-…`; en `datos.md` también las tablas de eventos y pedidos |

**No se ha tocado** [docs/conversacion_prueba.md](conversacion_prueba.md). Es la transcripción real de una ejecución anterior de la demo de la sesión 4 y por eso sigue mostrando `PED-1001`. Si se vuelve a ejecutar `python scripts/demo_conversacion.py`, se regenera con `EH-1001`.

## Compatibilidad con la sesión 4

- **El agente y la API siguen funcionando.** Los campos de los JSON son los mismos y solo cambian valores y registros.
- **Los conciertos de Valencia no cambian** (EV001–EV004), así que la demo de la sesión 4 da los mismos resultados.
- **Lo único visible para un usuario de la API** es que los pedidos se consultan ahora como `EH-xxxx`.
