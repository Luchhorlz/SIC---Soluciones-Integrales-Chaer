# Roadmap

## Fase 0 — Descubrimiento y documentación

Completada. Auditoría, arquitectura, dominio, seguridad inicial, referencias visuales, decisiones abiertas y plan de Fase 1.

## Fase 1 — Base del monorepo

Base implementada y CI verde. La validación completa de Compose queda pendiente de Docker Desktop; el cliente OpenAPI se generará cuando exista el primer recurso de dominio estable.

## Fases 2 a 4 — Identidad y catálogo

Google/Auth.js y roles; direcciones/geocodificación; taxonomía y administración del catálogo.

Estado de Fase 2: estructura Auth.js, Google Provider, pantalla de ingreso, sincronización BFF/API, sesión con UUID interno, selector persistible de roles y autorización del endpoint implementados. Pendiente: credenciales Google y ejecución real de las migraciones en PostgreSQL.

Estado de Fase 3: modelo privado de direcciones con punto PostGIS, migración e índice geográfico, autorización por propietario, dirección predeterminada, CRUD de API, pantalla `/cuenta/direcciones`, Autocomplete/Place Details y corrección firmada del pin implementados. Pendiente: credenciales Google reales, validación contra sus APIs y ejecución de la migración contra PostgreSQL/PostGIS.

Estado de Fase 4: modelos y migración del catálogo, API pública, escritura protegida por `ADMIN`, panel `/admin/catalogo`, desactivación sin borrado, contrato TypeScript generado y seed canónico idempotente implementados. La lista aprobada se preserva completa en `docs/taxonomy.md`; se importan 29 categorías, 140 subcategorías y 1.392 servicios. CI ejecuta PostgreSQL/PostGIS, migraciones y el seed dos veces. Pendiente local: disponer de Docker Desktop o PostgreSQL/PostGIS para cargarlo fuera de CI.

## Fases 5 a 7 — Oferta segura

Perfil y servicios del prestador; documentos y revisión; suscripción mensual mediante Mercado Pago sandbox.

Estado de Fase 5: onboarding profesional, perfil privado, portfolio descriptivo, selección múltiple del catálogo, capacidades de precio, modalidades, cobertura PostGIS por servicio, agenda semanal, períodos no disponibles, pausa y diagnóstico centralizado de visibilidad implementados. El prestador sigue fuera de resultados porque Fases 6 y 7 deben aprobar documentación y suscripción. Pendiente local: credenciales Google y PostgreSQL/PostGIS para uso persistente; CI valida el flujo real sobre PostGIS.

Estado de Fase 6: requisitos administrables por servicio, carga multipart privada, detección de contenido, límite y hash SHA-256, almacenamiento MinIO/S3, escaneo ClamAV, estados de revisión, cola `ADMIN`/`DOCUMENT_REVIEWER`, descargas breves firmadas, historial inmutable y vencimiento automático implementados. La aprobación recalcula únicamente los servicios que requieren ese tipo. No se cargaron requisitos legales ficticios. Pendiente local: ejecutar la suite completa con Docker/MinIO/ClamAV; CI valida migración, permisos, reglas y vencimientos sobre PostgreSQL.

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
