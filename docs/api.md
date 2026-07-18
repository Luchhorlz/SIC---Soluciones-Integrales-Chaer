# API

La API se definirá desde FastAPI/OpenAPI bajo `/v1`. Usará UUID, JSON, fechas ISO 8601 UTC, errores estables, request ID e idempotency keys en operaciones sensibles. El cliente TypeScript será generado, no duplicado manualmente.

En la Fase 1 solo existirán `/health/live` y `/health/ready`. Los recursos de catálogo, usuario, prestador, documentos, suscripciones, solicitudes, contrataciones, opiniones y administración se incorporarán en sus fases con permisos y pruebas.

## Identidad en desarrollo

- `PUT /v1/me/roles`: reemplaza los roles autogestionables `CLIENT`/`PROVIDER` del usuario autenticado.
- Requiere un Bearer token interno HS256 de corta duración, audiencia `sic-api` y `sub` UUID.
- Los roles administrativos no pueden asignarse mediante onboarding.
