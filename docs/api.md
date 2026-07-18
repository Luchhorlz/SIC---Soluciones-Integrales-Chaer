# API

La API se definirá desde FastAPI/OpenAPI bajo `/v1`. Usará UUID, JSON, fechas ISO 8601 UTC, errores estables, request ID e idempotency keys en operaciones sensibles. El cliente TypeScript será generado, no duplicado manualmente.

En la Fase 1 solo existirán `/health/live` y `/health/ready`. Los recursos de catálogo, usuario, prestador, documentos, suscripciones, solicitudes, contrataciones, opiniones y administración se incorporarán en sus fases con permisos y pruebas.

## Identidad en desarrollo

- `POST /v1/identity/sync-google`: crea o actualiza la identidad verificada y devuelve el UUID interno y sus roles. El token queda ligado al `sub` de Google y al propósito `identity-sync`.
- `PUT /v1/me/roles`: reemplaza los roles autogestionables `CLIENT`/`PROVIDER` del usuario autenticado.
- Requiere un Bearer token interno HS256 de corta duración, audiencia `sic-api` y `sub` UUID.
- Los roles administrativos no pueden asignarse mediante onboarding.

El navegador no llama a estos endpoints directamente. Auth.js y las Server Actions de Next.js actúan como BFF y generan los tokens internos exclusivamente del lado servidor.

## Direcciones

- `GET /v1/me/addresses`
- `POST /v1/me/addresses`
- `PATCH /v1/me/addresses/{id}`
- `DELETE /v1/me/addresses/{id}`

Todas requieren el UUID del usuario derivado del token interno. No existe un endpoint público de direcciones exactas. La primera dirección se convierte automáticamente en predeterminada y el punto se guarda como `geography(Point, 4326)` con índice GiST.
