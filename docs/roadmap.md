# Roadmap

## Fase 0 — Descubrimiento y documentación

En curso. Auditoría, arquitectura, dominio, seguridad inicial, referencias visuales, decisiones abiertas y plan de Fase 1. Sin funcionalidades complejas ni dependencias instaladas.

## Fase 1 — Base del monorepo

Next.js, FastAPI, PostgreSQL/PostGIS, Redis, Compose, healthchecks, CI, migración inicial y cliente OpenAPI generado. Criterio: arranque reproducible, migraciones limpias y CI verde.

## Fases 2 a 4 — Identidad y catálogo

Google/Auth.js y roles; direcciones/geocodificación; taxonomía y administración del catálogo.

## Fases 5 a 7 — Oferta segura

Perfil y servicios del prestador; documentos y revisión; suscripción mensual mediante Mercado Pago sandbox.

## Fases 8 a 10 — Marketplace

Búsqueda geográfica/remota y perfiles públicos; solicitudes, presupuestos y contrataciones; mensajería, notificaciones, favoritos y opiniones verificadas.

## Fases 11 y 12 — Operación y lanzamiento

Paneles de cliente, prestador y administración; hardening, accesibilidad, SEO, backups, observabilidad, staging y runbooks.

## Línea de infraestructura Windows

Se desarrolla incrementalmente junto a las fases:

- Base: comandos reproducibles y healthchecks.
- Host: supervisor local y API de control autenticada.
- Tray: Online/Offline, estado, abrir web, logs y salida segura.
- Publicación: Named Tunnel y hostname estable.
- Empaquetado: `.exe` firmado cuando se definan certificado y mecanismo de actualización.

No se activará producción desde una fase de desarrollo sin aprobación explícita.
