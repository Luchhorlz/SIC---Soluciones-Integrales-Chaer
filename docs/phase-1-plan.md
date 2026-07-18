# Plan exacto — Fase 1

## Objetivo

Crear una base reproducible del monorepo sin implementar aún funcionalidades de negocio.

## Secuencia

1. Verificar herramientas disponibles y fijar versiones compatibles de Node/pnpm, Python/uv, Docker y .NET.
2. Crear el monorepo mínimo: `apps/web`, `apps/api`, `packages/api-client`, `packages/ui`, `infra` y `seeds`, sin módulos futuros vacíos.
3. Inicializar Next.js App Router con TypeScript estricto, Tailwind, Manrope, tokens SIC, una portada de estado y pruebas mínimas.
4. Inicializar FastAPI async con configuración validada, logging JSON, request ID y endpoints `/health/live` y `/health/ready`.
5. Agregar SQLAlchemy 2, Alembic y una migración inicial técnica contra PostgreSQL/PostGIS.
6. Incorporar Redis y un worker Celery con una tarea de diagnóstico, sin lógica comercial.
7. Configurar MinIO y Mailpit para desarrollo; ClamAV queda detrás de un perfil opcional.
8. Crear Compose con healthchecks y red privada; exponer solo el proxy/web necesario.
9. Generar OpenAPI y el cliente TypeScript; hacer que la web consulte la salud de la API mediante el BFF.
10. Agregar lint, format, typecheck y tests en ambos stacks.
11. Crear CI con servicios PostGIS/Redis, migraciones, pruebas, build y verificación del cliente generado.
12. Crear scripts PowerShell de arranque/parada/estado que luego consumirá el host `.exe`.
13. Documentar comandos, variables y troubleshooting; actualizar changelog y ADRs.

## Verificaciones de aceptación

- Un checkout limpio puede instalar con lockfiles y arrancar con `docker compose up --build`.
- Web, API, worker, PostGIS y Redis alcanzan estado saludable.
- La web obtiene el healthcheck a través del BFF, no desde el navegador directo a la API.
- Alembic migra una base temporal desde cero y puede inspeccionar el estado actual.
- Lint, typecheck, tests y builds pasan.
- OpenAPI y cliente generado no presentan diferencias pendientes.
- `.env.example` está documentado y ninguna credencial aparece en Git.

## Fuera de Fase 1

Google OAuth, usuarios, catálogo, mapas, Mercado Pago, documentación real, búsqueda, contratación, UI completa, túnel productivo y empaquetado final `.exe`.

## Bloqueos

Ninguna decisión comercial abierta bloquea esta fase. Antes de iniciar se mostrará el resultado de la verificación de herramientas y las versiones propuestas; no se instalará nada global sin necesidad y autorización.
