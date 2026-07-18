# SIC — Soluciones Integrales Chaer

Marketplace web de servicios presenciales y remotos. Los clientes encuentran y contratan servicios concretos; los prestadores configuran sus aptitudes, cobertura, documentación y suscripción.

## Estado

El proyecto alcanzó la **Fase 4 — Catálogo y administración**. La base del monorepo, identidad, direcciones privadas, integración BFF de Google y catálogo canónico están implementados; las credenciales externas y la ejecución completa con PostgreSQL/PostGIS local siguen siendo requisitos del entorno.

## Producto acordado

- Dominio público previsto: `https://sic.thecottonclub.com.ar`.
- Repositorio previsto: `https://github.com/Luchhorlz/SIC---Soluciones-Integrales-Chaer`.
- País inicial: Argentina.
- Marca: `SIC` / `Soluciones Integrales Chaer`.
- Cliente Windows propio en formato `.exe`, persistente en Systray, con control Online/Offline y acceso al estado del sistema.
- Publicación estable mediante Cloudflare Named Tunnel; no se usarán URLs temporales.

## Documentación

- [Arquitectura](docs/architecture.md)
- [Dominio](docs/domain.md)
- [Roadmap](docs/roadmap.md)
- [Plan de Fase 1](docs/phase-1-plan.md)
- [Diseño y assets](docs/design-reference.md)
- [Taxonomía canónica](docs/taxonomy.md)
- [Seguridad](docs/security.md)
- [Despliegue](docs/deployment.md)
- [Preguntas abiertas](docs/open-questions.md)

La especificación fuente es `PLAN_MAESTRO_CODEX_SIC.md`. Las imágenes aprobadas están en `Resultado visual/`.

## Desarrollo

La previsualización local está disponible en `http://127.0.0.1:3000` después de ejecutar:

```powershell
.\infra\scripts\Start-SicLocal.ps1
```

Estado y parada:

```powershell
.\infra\scripts\Get-SicStatus.ps1
.\infra\scripts\Stop-SicLocal.ps1
```

Cuando Docker Desktop esté instalado, la suite completa se iniciará con `docker compose up --build`.

Rutas visuales disponibles durante el desarrollo:

- `/ingresar`: ingreso con Google y estado de configuración.
- `/onboarding/rol`: selección interactiva de cliente/prestador.
- `/cuenta`: panel inicial del cliente.
- `/cuenta/direcciones`: gestión privada de direcciones y vista geográfica.
- `/admin/catalogo`: administración protegida de categorías, subcategorías y servicios.

La geocodificación requiere Places API (New), Maps Static API, `GOOGLE_MAPS_API_KEY` y `GOOGLE_MAPS_URL_SIGNING_SECRET`. Ambos valores permanecen fuera de Git y del JavaScript enviado al navegador.

El catálogo aprobado se genera desde la lista entregada por el propietario y se importa de forma repetible:

```powershell
cd apps\api
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m sic_api.modules.catalog.seed --file ..\..\seeds\taxonomy.json
```

El mismo comando puede ejecutarse nuevamente: actualiza por código estable y no duplica registros.

## Reglas centrales

- El catálogo pertenece a SIC; el prestador habilita servicios del catálogo.
- No hay publicaciones públicas de clientes ni bolsa de trabajo.
- La ubicación solo condiciona modalidades presenciales.
- La documentación profesional requerida debe estar aprobada y vigente.
- La suscripción habilita visibilidad, pero no reemplaza las demás validaciones.
- El MVP cobra la suscripción del prestador; no procesa el pago del servicio entre cliente y prestador.
