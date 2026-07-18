# AGENTS.md

## Fuente de verdad

Leer completos antes de modificar el proyecto:

1. `PLAN_MAESTRO_CODEX_SIC.md`.
2. `README.md`.
3. `docs/architecture.md`, `docs/domain.md`, `docs/roadmap.md` y ADRs.
4. `docs/design-reference.md` y las referencias de `Resultado visual/` para trabajo de interfaz.

## Forma de trabajo

- Trabajar por fases pequeñas, verificables y reversibles.
- No adelantar fases futuras ni inventar decisiones comerciales.
- Mantener TypeScript estricto y Python tipado.
- Cada cambio funcional incluye validación, errores, pruebas y documentación.
- Ejecutar lint, typecheck, tests y build aplicables antes de cerrar.
- Usar migraciones Alembic; no borrar tablas ni migraciones aplicadas.
- No ejecutar producción ni cambiar DNS, túneles, secretos o infraestructura externa sin autorización explícita.
- Nunca guardar secretos, domicilios exactos, documentos privados ni datos reales de usuarios en Git.
- Preservar literalmente `SIC` y `Soluciones Integrales Chaer` en la marca.

## Arquitectura

- Monorepo con Next.js App Router como web/BFF y FastAPI como API interna.
- PostgreSQL/PostGIS, Redis, almacenamiento S3 compatible y worker Celery.
- El navegador no accede directamente a FastAPI.
- `ProviderVisibilityService` es la única fuente de verdad de visibilidad.
- Monolito modular: evitar microservicios y acceso directo entre tablas de módulos.
- El host Windows/Systray controla la suite local y el Cloudflare Named Tunnel mediante procesos supervisados.

## Diseño

- Mobile-first y WCAG 2.2 AA.
- Bordó principal, dorado como acento y superficies claras.
- Manrope como tipografía inicial.
- Las imágenes son referencias de composición; no se deben copiar inconsistencias de negocio. Por ejemplo, el MVP no cobra el trabajo del cliente ni promete “pagos protegidos”.

## Seguridad y datos

- Deny by default; RBAC más ABAC.
- API privada con token BFF de corta duración.
- Archivos privados en bucket privado, URLs firmadas, validación MIME y antivirus.
- Logs estructurados sin secretos, documentos ni direcciones exactas.
- Webhooks firmados e idempotentes.

## Commits

- Commits estrechos y descriptivos.
- No incluir `.env`, credenciales, runtime, bases locales, binarios generados o datos privados.
- No mezclar cambios ajenos o no relacionados.
