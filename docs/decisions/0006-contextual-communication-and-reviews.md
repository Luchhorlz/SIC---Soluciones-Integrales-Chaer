# ADR 0006 — Comunicación contextual y reputación moderada

## Estado

Aceptada para Fase 10.

## Contexto

SIC necesita coordinación privada entre cliente y prestador, avisos transaccionales y una reputación útil sin habilitar spam, enumeración de usuarios ni reseñas de trabajos inexistentes. La política editorial definitiva todavía no fue aprobada.

## Decisión

- Crear una conversación única por solicitud y derivar ambos participantes desde sus relaciones persistidas.
- Volver de sólo lectura una conversación cerrada cuando no existe contratación.
- Actualizar mensajes mediante sondeo de ocho segundos, pausado al ocultar la pestaña, en lugar de sumar WebSocket al MVP.
- Limitar cada remitente a veinte mensajes por minuto y no ofrecer destinatarios libres ni contacto masivo.
- Guardar notificaciones internas y usar su estado de entrega como bandeja de correo transaccional procesada por Celery.
- Conservar favoritos como relación privada, pero consultar siempre la visibilidad pública antes de mostrarlos.
- Admitir una opinión por booking únicamente después de `COMPLETED` y confirmación del cliente.
- Mantener las opiniones `PENDING` hasta decisión `ADMIN`; sólo `PUBLISHED` participa del promedio.
- Guardar cada contenido anterior en `review_revisions` antes de editar y devolver una reseña editada a moderación.

## Consecuencias

La API no expone un chat general ni permite acceder conociendo UUID. La coordinación funciona sin una conexión permanente compleja y la bandeja interna no depende de SMTP. Una reseña legítima puede demorar en publicarse, pero nunca afecta reputación sin control humano. La política futura puede ajustar criterios de moderación sin cambiar la elegibilidad ni el historial.
