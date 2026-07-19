# Arquitectura

## Decisión base

SIC será un monolito modular desplegado en procesos/contenedores separados. Next.js cumple la función web y BFF; FastAPI concentra dominio y persistencia. La decisión completa está en `docs/decisions/0001-modular-monolith.md`.

```text
Navegador
  -> Reverse proxy
    -> Next.js Web/BFF
      -> FastAPI privada
        -> PostgreSQL + PostGIS
        -> Redis
        -> S3 compatible / MinIO
        -> Worker Celery
        -> Mercado Pago (suscripciones)
        -> Google Places/Geocoding
```

## Límites

- `apps/web`: UI, SSR/SEO, Auth.js, sesión y BFF.
- `apps/api`: casos de uso, permisos, módulos de dominio, OpenAPI y persistencia.
- `apps/worker`: tareas idempotentes y reintentables.
- `packages/api-client`: cliente TypeScript generado desde OpenAPI.
- `packages/ui`: tokens y componentes compartidos de SIC.
- `infra`: Compose, proxy, backups, monitoreo y empaquetado Windows.
- `seeds`: taxonomía canónica y datos ficticios de desarrollo.

La API no acepta un `user_id` confiado desde el navegador. Next.js valida sesión y emite un token interno de aproximadamente 60 segundos con `sub`, roles, sesión, request ID y audiencia `sic-api`.

## Módulos iniciales del backend

Identity, users, addresses, catalog, providers, provider services, documents, subscriptions, search, requests, bookings, messaging, reviews, notifications, media, moderation, audit y admin. Se crearán cuando su fase los necesite, evitando paquetes vacíos.

En Fase 5, `providers` posee el perfil, portfolio y `ProviderVisibilityService`; `provider_services` posee modalidades, precios, áreas PostGIS, reglas semanales y excepciones de disponibilidad. Los controladores coordinan ambos módulos mediante servicios y repositorios, sin convertir un booleano persistido en fuente de verdad de visibilidad.

En Fase 6, `documents` posee requisitos, envíos, estados, revisiones inmutables y vencimientos; `media` conserva metadatos y hash de objetos privados. El contenido reside en MinIO/S3, no en PostgreSQL. La API valida firma real, tamaño y hash, guarda con clave UUID y consulta ClamAV por `INSTREAM`. Celery ejecuta vencimientos horarios; cada cambio recalcula solo los servicios alcanzados por el tipo documental.

En Fase 7, `subscriptions` posee planes, suscripciones y eventos de cobro. `BillingProvider` evita que los DTO de Mercado Pago entren al dominio. La web inicia el checkout por BFF y sólo redirige a hosts oficiales permitidos; el webhook público atraviesa un proxy mínimo de Next.js hacia la API privada. `provider_services` depende de una interfaz de lectura del estado normalizado y `ProviderVisibilityService` sigue siendo el único evaluador final.

En Fase 8, `search` agrega una proyección pública de sólo lectura para evitar consultas por registro. Puede unir catálogo, oferta, perfil y estado de cuenta, pero no replica reglas de publicación: documentación y suscripción se consultan mediante sus interfaces propietarias y cada candidato pasa por `ProviderVisibilityService`. El detalle está registrado en `docs/decisions/0004-public-search-read-model.md`.

Cada módulo separa transporte (`api.py`), esquemas, casos de uso, repositorios, modelos, permisos, eventos y pruebas. Las transacciones comienzan en el caso de uso.

## Host Windows y URL pública

El requisito de servidor propio se resuelve con una suite local supervisada:

1. `SIC Server.exe` inicia y controla proxy, web, API, worker, base y dependencias locales según el modo de instalación aprobado.
2. `SIC Tray.exe` permanece en Systray y se comunica solo con una API de control local autenticada.
3. El estado Online inicia/verifica la aplicación y un Cloudflare Named Tunnel asociado a `sic.thecottonclub.com.ar`.
4. Offline detiene el túnel público sin destruir los datos; la operación local puede mantenerse o detenerse mediante una opción separada.
5. El panel muestra salud de componentes, URL pública, logs recientes, reinicio y salida segura.

Para el MVP se prioriza un empaquetado Windows reproducible sobre un Windows Service privilegiado. Convertir el host en servicio nativo queda condicionado a la operación real y se documentará en otro ADR si resulta necesario.

## Observabilidad

- `/health/live` comprueba proceso.
- `/health/ready` comprueba dependencias esenciales.
- Logs JSON con request ID.
- Métricas de latencia, errores, búsquedas, conversión, documentos, suscripciones, webhooks y tareas.
- Backups y restauraciones verificadas antes de producción.
