# ADR 0003 — Cobro de suscripción aislado e idempotente

## Estado

Aceptada para Fase 7.

## Contexto

SIC debe cobrar únicamente la membresía mensual del prestador, conservar la API detrás de Next.js y evitar que un webhook repetido o manipulado publique servicios. El precio comercial todavía no fue definido y no corresponde inventar niveles.

## Decisión

- Mantener un plan inicial configurable en PostgreSQL, con una sola fila activa y estructura preparada para más planes.
- Crear suscripciones sin plan externo asociado mediante `/preapproval` en estado `pending`; el checkout lo aloja Mercado Pago.
- Encapsular HTTP en `MercadoPagoBillingProvider` y exponer al dominio sólo DTO normalizados.
- Publicar `/api/webhooks/mercado-pago` en Next.js y reenviar bytes, query y cabeceras a la API privada.
- Validar HMAC y timestamp antes de persistir; guardar sólo el hash del cuerpo.
- Insertar `billing_events` antes de consultar el recurso y deduplicar por identificador externo.
- Consultar el recurso autenticado a Mercado Pago y recién entonces actualizar `provider_subscriptions`.
- Permitir visibilidad únicamente con `ACTIVE` o `AUTHORIZED`; cualquier baja oculta sin borrar datos.

## Consecuencias

El flujo puede probarse con credenciales sandbox sin manejar tarjetas ni exponer FastAPI. Un fallo externo devuelve error para que Mercado Pago reintente y el evento fallido queda auditable. El paso a producción requiere precio aprobado, credenciales productivas, URL HTTPS estable y una prueba integral explícitamente autorizada.
