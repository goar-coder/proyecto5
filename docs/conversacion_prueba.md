# Conversación de prueba — Asistente EventHub

Generada con `scripts/demo_conversacion.py` el 2026-11-09 17:38 con el modelo `gpt-6-luna`. Se ha usado una copia temporal de `data/`.

### Turno 1 — Políticas  (thread_id=`demo-principal`)

**Usuario:** ¿Cuál es la política de devoluciones?

*Herramientas llamadas:* ninguna

**Asistente:** Puedes solicitar la devolución hasta 14 días antes del evento. Se reembolsa al mismo método de pago en un plazo de 5 a 10 días hábiles. Los gastos de gestión (1,50 € por entrada) no son reembolsables, salvo si el organizador cancela el evento.

No se aceptan devoluciones a menos de 14 días del evento ni de entradas ya utilizadas. Para solicitarla necesitas el identificador del pedido y el email de compra.

### Turno 2 — Búsqueda de eventos  (thread_id=`demo-principal`)

**Usuario:** ¿Qué conciertos hay en Valencia?

*Herramientas llamadas:* `buscar_eventos({"ciudad": "Valencia", "categoria": "concierto"})`

**Asistente:** Estos son los conciertos en Valencia:

- **Noche de Rock en el Turia** — 5 de diciembre de 2026, 21:00 — 35 € — 120 entradas disponibles.
- **Jazz al Atardecer** — 12 de diciembre de 2026, 19:30 — 22,50 € — 40 entradas disponibles.
- **Gran Gala Sinfónica de Año Nuevo** — 1 de enero de 2027, 20:00 — 60 € — agotado.
- **Indie Fest Valencia** — 14 de febrero de 2027, 18:00 — 45 € — 300 entradas disponibles.

### Turno 3 — Referencia al turno anterior (memoria)  (thread_id=`demo-principal`)

**Usuario:** ¿Y el más barato de esos?

*Herramientas llamadas:* `buscar_eventos({"ciudad": "Valencia", "categoria": "concierto"})`

**Asistente:** El más barato es **Jazz al Atardecer**, por **22,50 €**. Quedan 40 entradas.

### Turno 4 — Pedido con email incorrecto  (thread_id=`demo-principal`)

**Usuario:** Quiero saber el estado del pedido PED-1001, mi email es laura@otrodominio.com

*Herramientas llamadas:* `consultar_pedido({"id_pedido": "PED-1001", "email": "laura@otrodominio.com"})`

**Asistente:** No puedo verificar el pedido con esos datos. Revisa el identificador y el email de compra, o contacta con soporte en **soporte@eventhub.example** o al **+34 900 123 456**.

### Turno 5 — Pedido con email correcto  (thread_id=`demo-principal`)

**Usuario:** Perdona, me equivoqué: el email es laura.martinez@example.com

*Herramientas llamadas:* `consultar_pedido({"id_pedido": "PED-1001", "email": "laura.martinez@example.com"})`

**Asistente:** El pedido **PED-1001** está **pagado**. Incluye 2 entradas y se compró el 15 de octubre de 2026.

### Turno 6 — Reserva (requiere confirmación)  (thread_id=`demo-principal`)

**Usuario:** Resérvame 2 entradas del concierto más barato de Valencia

*Herramientas llamadas:* `buscar_eventos({"ciudad": "Valencia", "categoria": "concierto"})`, `reservar_entradas({"id_evento": "EV002", "cantidad": 2})`

**API:** `pendiente_confirmacion` → acción `reservar_entradas` con argumentos `{"id_evento": "EV002", "cantidad": 2}`

### Turno 6b — Confirmación  (thread_id=`demo-principal`)

**Usuario:** POST /chat/confirmar {aprobar: true}

*Herramientas llamadas:* `reservar_entradas({"id_evento": "EV002", "cantidad": 2})`

**Asistente:** He reservado **2 entradas para Jazz al Atardecer**, el concierto más barato de Valencia. **Total: 45 €**. Quedan 38 entradas disponibles.

> Comprobación en events.json (copia): EV002 tenía **40** disponibles y ahora tiene **38**.

### Turno 7 — Comprobar stock tras la reserva  (thread_id=`demo-principal`)

**Usuario:** ¿Cuántas entradas quedan ahora para ese concierto?

*Herramientas llamadas:* `buscar_eventos({"ciudad": "Valencia", "categoria": "concierto"})`

**Asistente:** Ahora quedan **38 entradas** para **Jazz al Atardecer**.

### Turno 8 — Pregunta fuera de las políticas (no debe inventar)  (thread_id=`demo-principal`)

**Usuario:** ¿Hay parking en el recinto?

*Herramientas llamadas:* ninguna

**Asistente:** No tengo información sobre si el recinto dispone de parking. Puedes consultarlo con soporte en **soporte@eventhub.example** o en el **+34 900 123 456**.

### Turno 9 — Otro thread_id (no comparte memoria)  (thread_id=`demo-otro-usuario`)

**Usuario:** ¿Cuál era el concierto más barato que te pregunté antes?

*Herramientas llamadas:* `buscar_eventos({"ciudad": null, "categoria": "concierto"})`

**Asistente:** No veo una pregunta anterior sobre conciertos en esta conversación. De los conciertos disponibles ahora, el más barato es **Jazz al Atardecer**, en Valencia, por **22,50 €**.

