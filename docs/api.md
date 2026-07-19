# API

La API se definirá desde FastAPI/OpenAPI bajo `/v1`. Usará UUID, JSON, fechas ISO 8601 UTC, errores estables, request ID e idempotency keys en operaciones sensibles. El cliente TypeScript será generado, no duplicado manualmente.

Los recursos se incorporan por fase. El contrato actual se exporta desde FastAPI a `apps/web/openapi.json` y genera `apps/web/src/generated/api-schema.d.ts`; el BFF consume esos tipos y evita duplicar DTOs manualmente.

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

El BFF expone `POST /api/places/autocomplete` y `POST /api/places/details` únicamente a sesiones autenticadas. La clave de Google permanece del lado servidor. Place Details normaliza dirección y coordenadas y entrega un comprobante firmado, ligado al usuario y a su sesión, que la Server Action verifica antes de crear el recurso. El formulario no puede sustituir esos valores con datos enviados manualmente.

`POST /api/places/map` entrega la imagen autenticada sin exponer la URL firmada de Google. `POST /api/places/pin` permite corregir las coordenadas y emite un comprobante nuevo solo si el punto permanece dentro de 500 metros de la ubicación original validada.

## Catálogo

- `GET /v1/catalog/categories`: jerarquía pública activa de categorías, subcategorías y servicios.
- `GET /v1/catalog/services`: servicios públicos activos.
- `GET /v1/admin/catalog`: jerarquía completa, incluidos elementos inactivos; requiere `ADMIN`.
- `POST /v1/admin/catalog/categories|subcategories|services`: alta controlada; requiere `ADMIN`.
- `PATCH /v1/admin/catalog/categories|subcategories|services/{id}`: edición o activación/desactivación; requiere `ADMIN`.

No existen endpoints `DELETE` del catálogo. Los códigos son estables e independientes del nombre visible; los slugs son únicos por tipo de recurso. El seed aprobado reside en `seeds/taxonomy.json` y usa upsert por código.

## Prestador

Todos requieren token interno, rol `PROVIDER` y propiedad derivada del UUID autenticado:

- `POST /v1/provider/onboarding`
- `GET|PATCH /v1/provider/profile`
- `POST /v1/provider/profile/pause`
- `POST|DELETE /v1/provider/portfolio[/{id}]`
- `GET|POST /v1/provider/services`
- `PATCH /v1/provider/services/{id}`
- `POST /v1/provider/services/{id}/pause`
- `GET|PUT /v1/provider/services/{id}/availability`
- `GET|POST|DELETE /v1/provider/availability/exceptions[/{id}]`

El servicio del prestador referencia una prestación canónica activa y valida sus capacidades de presupuesto, precio directo y urgencia. Las modalidades presenciales que visitan o retiran en el domicilio del cliente exigen un área propia cuyo centro proviene de una dirección Google ya validada y propiedad del usuario.

La respuesta de cada servicio incluye `visible` y `visibility_code`, ambos derivados exclusivamente por `ProviderVisibilityService`. La preparación documental se calcula por requisitos aprobados y vigentes y, desde Fase 7, la suscripción se consulta desde su módulo normalizado; el campo histórico del perfil no es fuente de verdad.

## Documentación profesional

Prestador, siempre por propiedad derivada del token:

- `GET /v1/provider/document-requirements`
- `GET|POST /v1/provider/documents`
- `GET /v1/provider/documents/{id}/download-url`

Revisión privada:

- `GET|POST /v1/admin/document-requirements`; la escritura exige `ADMIN`.
- `GET /v1/admin/documents`; admite `ADMIN` o `DOCUMENT_REVIEWER`.
- `POST /v1/admin/documents/{id}/review|approve|observe|reject|suspend|rescan`.
- `GET /v1/admin/documents/{id}/download-url`.
- `POST /v1/admin/documents/expire`; mantenimiento manual protegido por `ADMIN` además del worker horario.

El upload usa `multipart/form-data`; solo acepta contenido PDF, PNG o JPEG validado y nunca acepta un `provider_id` del navegador. Las URLs de descarga son firmadas, duran 60 segundos por defecto y solo se generan luego del escaneo limpio.

## Suscripciones

Prestador, siempre derivado del token y de su perfil:

- `GET /v1/provider/subscription`: plan activo, estado normalizado y disponibilidad del checkout.
- `POST /v1/provider/subscription/checkout`: crea o reutiliza una suscripción pendiente y devuelve exclusivamente una URL oficial validada.

Administración:

- `GET|POST /v1/admin/subscription-plans`: lista o crea planes; la escritura exige `ADMIN`.
- `PATCH /v1/admin/subscription-plans/{id}`: edita sin borrar; sólo puede existir un plan activo.

Mercado Pago llama públicamente a `POST /api/webhooks/mercado-pago` en Next.js. El BFF reenvía cuerpo, `x-signature`, `x-request-id` y `data.id` a `POST /v1/webhooks/mercado-pago` en la API privada. FastAPI valida la firma antes de persistir, guarda sólo el hash del cuerpo, deduplica por evento externo y consulta `/preapproval/{id}` o `/authorized_payments/{id}` antes de aplicar efectos.

## Búsqueda y perfiles públicos

- `GET /v1/search/providers`: acepta texto, slugs canónicos, modalidad, disponibilidad, orden, cursor y, cuando el navegador la autoriza, latitud/longitud con radio entre 500 m y 100 km.
- `GET /v1/providers/{slug}`: perfil público seguro o `404` si ninguna oferta del prestador es visible.
- `GET /v1/providers/{slug}/services`: únicamente ofertas visibles del mismo perfil.

Los endpoints son consumidos por componentes servidor de Next.js; el navegador navega por el BFF y no conoce `API_INTERNAL_URL`. Una búsqueda presencial exige coordenadas, nunca una localidad escrita libremente. PostGIS filtra con `ST_DWithin` antes de calcular distancia. La respuesta redondea distancias a 100 metros y puntos de mapa a dos decimales; nunca incluye domicilio, `address_id`, punto base ni centro exacto de cobertura. Las modalidades remotas no reciben distancia y su ranking no cambia por ubicación.
