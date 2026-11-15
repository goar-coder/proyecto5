# Cómo probar las versiones LangGraph

El asistente de EventHub está rehecho como grafo de LangGraph en cuatro versiones, cada una sobre la anterior. El código está en [grafos/](../grafos/) y cada versión tiene su tag de git:

| Versión | Fichero | Tag | ¿Necesita OpenAI? |
|---|---|---|---|
| 1. Grafo simple | [grafos/v1_grafo_simple.py](../grafos/v1_grafo_simple.py) | `v1-grafo-simple` | No |
| 2. Chatbot | [grafos/v2_chatbot.py](../grafos/v2_chatbot.py) | `v2-chatbot` | Sí |
| 3. Memoria | [grafos/v3_memoria.py](../grafos/v3_memoria.py) | `v3-memoria` | Sí |
| 4. Herramientas | [grafos/v4_herramientas.py](../grafos/v4_herramientas.py) | `v4-herramientas` | Sí |

## Preparación

```bash
source .venv/bin/activate
pip install -r requirements.txt      # no hay dependencias nuevas
cp .env.example .env                 # pon OPENAI_API_KEY (solo para v2, v3, v4 y la demo)
```

Todos los comandos se lanzan **desde la raíz del proyecto** y con `python -m`, para que funcionen los imports (`grafos`, `services`, `llm`…).

Para ver el código tal como estaba en una versión concreta: `git checkout v2-chatbot` (y `git checkout main` para volver).

> Las versiones 2, 3 y 4 trabajan sobre `data/` directamente. La v4 solo **lee** datos (no hay reservas), así que no modifica nada. Los tests y la demo usan una copia temporal.

---

## Versión 1 — grafo simple (sin LLM)

```
START → clasificar ─┬─(eventos)───► responder_eventos ───► END
                    ├─(pedido)────► responder_pedido ────► END
                    ├─(politicas)─► responder_politicas ─► END
                    └─(otro)──────► responder_otro ──────► END
```

**Ejecutar con los ejemplos predefinidos** (también guarda el diagrama en `grafos/diagramas/v1.mmd`):

```bash
python -m grafos.v1_grafo_simple
```

**Clasificar tus propios textos** (cada argumento es un mensaje):

```bash
python -m grafos.v1_grafo_simple "¿Cómo va mi pedido EH-1001?" "¿Puedo cambiar el titular?" "hola"
```

Salida esperada:

| Mensaje | Intención | Por qué |
|---|---|---|
| ¿Qué conciertos hay en Valencia? | `eventos` | contiene «concierto» |
| ¿Cómo va mi pedido EH-1001? | `pedido` | patrón `EH-<número>` o «pedido» |
| ¿Puedo devolver mis entradas? | `politicas` | «devol»; las políticas se miran antes que los eventos, así que «entradas» no gana |
| Mi pedido está cancelado | `pedido` | «pedido» tiene prioridad sobre «cancel» |
| ¿Qué tiempo hace hoy? | `otro` | ninguna regla encaja |

Las reglas no distinguen mayúsculas ni tildes («POLÍTICA» = «politica»). El orden de prioridad es pedido → políticas → eventos → otro.

---

## Versión 2 — chatbot

```
START → chatbot → END
```

```bash
python -m grafos.v2_chatbot
```

Abre un bucle en la terminal: escribe y responde el modelo (con el prompt de EventHub y las políticas). Se sale con `salir` o con Ctrl+D.

Qué probar:

| Escribe | Debe pasar |
|---|---|
| ¿Cuál es la política de devoluciones? | Responde con los 14 días y los gastos de 1,50 € de `policies.md` |
| ¿Hay parking en el recinto? | Dice que no tiene esa información y remite a soporte (no inventa) |
| ¿Qué conciertos hay en Valencia? | Dice que no tiene acceso al catálogo: la v2 todavía no tiene herramientas |
| Me llamo Ana → ¿Cómo me llamo? | Lo recuerda **dentro de la sesión**, porque el bucle de la terminal reenvía el historial. Al cerrar el programa se pierde |

---

## Versión 3 — memoria (checkpointer y `thread_id`)

Es el mismo grafo que la v2, compilado con `InMemorySaver`.

**Demo automática** (hilos aislados más `get_state`):

```bash
python -m grafos.v3_memoria --demo
```

1. `hilo-1`: «Hola, me llamo Laura. ¿Cuál es la política de devoluciones?»
2. `hilo-2`: «¿Cómo me llamo?» → **no lo sabe** (otro hilo, otro estado).
3. `hilo-1`: «¿Cómo me llamo?» → **Laura**.
4. Imprime `get_state` de los dos hilos: `hilo-1` con 4 mensajes y `hilo-2` con 2.

**Modo interactivo:**

```bash
python -m grafos.v3_memoria
```

| Comando | Qué hace |
|---|---|
| (texto) | Envía el mensaje al hilo actual (por defecto `hilo-1`) |
| `/hilo <id>` | Cambia de conversación, p. ej. `/hilo hilo-2` |
| `/historial` | Muestra `get_state` del hilo actual: mensajes guardados, `next` y `checkpoint_id` |
| `salir` | Termina |

Prueba recomendada: di tu nombre en `hilo-1`, cambia con `/hilo hilo-2`, pregunta tu nombre (no lo sabe), vuelve con `/hilo hilo-1`, pregunta otra vez (lo sabe) y escribe `/historial`.

---

## Versión 4 — herramientas

```
START → chatbot ─┬─(usar_herramientas)─► herramientas ──► chatbot   (bucle)
                 ├─(limite_alcanzado)──► limite ────────► END
                 └─(fin)───────────────► END
```

```bash
python -m grafos.v4_herramientas
```

Al arrancar guarda el diagrama en `grafos/diagramas/v4.mmd`. Tiene los mismos comandos que la v3 (`/hilo`, `/historial`, `salir`), y antes de cada respuesta muestra las herramientas llamadas:

```
[hilo-1] Tú: ¿Mi pedido EH-1003 es para un concierto en Madrid? Si es así, dime otros conciertos en Madrid ese mes. Mi email es ana.gomez@example.com
  ↳ consultar_pedido({"id_pedido": "EH-1003", "email": "ana.gomez@example.com"})
  ↳ buscar_eventos({"ciudad": "Madrid", "categoria": "concierto", "mes": "2026-12"})
Asistente: Sí, tu pedido es para Rock en la Gran Vía (11 de diciembre)...
```

Qué probar:

| Escribe | Debe pasar |
|---|---|
| La pregunta del enunciado **con** email (arriba) | Encadena `consultar_pedido` y `buscar_eventos` en la misma respuesta. Resultado: EV013 es un concierto en Madrid en diciembre; los otros son EV014 (Coros de Navidad, 25 €) y EV015 (Sinfonía de Invierno, agotado). EV016 (enero) no sale |
| La misma pregunta **sin** email | No llama a ninguna herramienta y **pide el email**. Al dárselo («ana.gomez@example.com») encadena las herramientas |
| EH-1003 con un email incorrecto | Mensaje genérico: no revela si el pedido existe |
| ¿Qué conciertos hay en Madrid en enero de 2027? | `buscar_eventos(ciudad="Madrid", categoria="concierto", mes="2027-01")` → solo EV016 |
| ¿Cuál de esos es el más barato? (después de una búsqueda) | Usa la memoria del hilo para entender «esos» |
| `/historial` | `get_state` con los `tool_calls`, los `ToolMessage` y el contador `pasos` del último turno |

A veces el modelo hace una búsqueda más (3 herramientas en vez de 2). `consultar_pedido` devuelve el `id_evento` pero no la fecha, así que primero busca el evento para saber el mes y después filtra por él. Las dos formas son correctas.

**Límite de pasos.** Con un modelo real es difícil provocar un bucle infinito, por eso el límite se prueba con un test (ver abajo). `MAX_PASOS = 5` rondas de herramientas por turno. Si el modelo pide una sexta, el nodo `limite` responde a las llamadas pendientes con «no ejecutada» y termina con un mensaje amable que remite a soporte.

---

## Diagramas (versiones 1 y 4)

```bash
python scripts/generar_diagramas.py
```

Escribe [grafos/diagramas/v1.mmd](../grafos/diagramas/v1.mmd) y [grafos/diagramas/v4.mmd](../grafos/diagramas/v4.mmd) con `get_graph().draw_mermaid()`. No necesita clave ni internet: la v4 se construye con un modelo falso, porque la forma del grafo no depende del LLM.

Para verlos: pega el contenido en <https://mermaid.live>, ábrelos en VS Code con una extensión de Mermaid, o mira [entrega_langgraph.md](entrega_langgraph.md), donde aparecen como bloques `mermaid` (GitHub los dibuja).

## Demo de entrega

```bash
python scripts/demo_grafos.py
```

Necesita `OPENAI_API_KEY` y trabaja sobre una copia temporal de `data/`. Genera [entrega_langgraph.md](entrega_langgraph.md) con todo lo que pide la entrega:

1. Los diagramas de las versiones 1 y 4.
2. La tabla de clasificaciones de la v1.
3. Los hilos aislados de la v3 y el `get_state` del `hilo-1` (4 mensajes).
4. La v4:
   - conversación A: la pregunta del enunciado; comprueba y marca con ✅ que se encadenaron `consultar_pedido` y `buscar_eventos`, y añade una pregunta de seguimiento;
   - conversación B: sin email, el agente lo pide y después encadena las herramientas;
   - el `get_state` del hilo A (10–12 mensajes según cuántas herramientas use, con `tool_calls` y `ToolMessage`).

El modelo no es determinista, así que el texto exacto cambia entre ejecuciones.

## Tests automáticos

```bash
pytest                       # todo (sesión 4 + grafos)
pytest tests/test_grafos.py  # solo las versiones LangGraph
```

No llaman a OpenAI: usan modelos falsos (`ModeloGuionizado`, de [tests/test_agent_flow.py](../tests/test_agent_flow.py), y `ModeloQueRecuerda`, que responde con los mensajes humanos que ha visto).

| Versión | Test | Qué comprueba |
|---|---|---|
| 1 | `test_v1_clasifica_y_responde_segun_la_ruta` | 10 casos: las 4 intenciones, prioridades, mayúsculas, tildes y texto vacío |
| 1 | `test_v1_diagrama_tiene_arista_condicional` | El Mermaid tiene los 5 nodos y las ramas condicionales |
| 2 | `test_v2_chatbot_antepone_sistema_y_anade_respuesta` | El modelo recibe el `SystemMessage` con las políticas; el estado queda `[human, ai]` |
| 2 | `test_v2_sin_checkpointer_no_recuerda` | Sin checkpointer, dos `invoke` no comparten historial |
| 3 | `test_v3_hilos_aislados_y_get_state` | `hilo-2` no ve `hilo-1`; `get_state` del `hilo-1` tiene 4 mensajes y `next == ()` |
| 3 | `test_v3_hilo_nuevo_esta_vacio` | Un hilo sin usar no tiene estado |
| 4 | `test_v4_encadena_dos_herramientas_en_una_respuesta` | La pregunta del enunciado: `consultar_pedido` → `buscar_eventos(mes="2026-12")` → respuesta; mensajes `human, ai, tool, ai, tool, ai`; EV013 en el pedido; EV013–EV015 sin EV016 |
| 4 | `test_v4_sin_herramientas_termina_directamente` | Sin `tool_calls` va a END con `pasos = 0` |
| 4 | `test_v4_limite_de_pasos_termina_con_mensaje_amable` | Un modelo que pide herramientas sin parar termina con `MENSAJE_LIMITE`, `pasos = MAX_PASOS` y ninguna `tool_call` sin responder |
| 4 | `test_v4_contador_se_reinicia_en_cada_turno` | `pasos` vuelve a 0 en cada turno |
| 4 | `test_v4_herramienta_desconocida_y_argumentos_invalidos` | Una herramienta inexistente o con argumentos que faltan da un `ToolMessage` con `status="error"`, sin romper el grafo |
| 4 | `test_v4_diagrama` | El Mermaid tiene el bucle `herramientas --> chatbot` y las tres ramas |

Para el filtro `mes` hay tests en [tests/test_services.py](../tests/test_services.py): mes con ciudad y categoría, mes solo, formatos inválidos y la herramienta devolviendo `{"error": ...}`.
