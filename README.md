# SIC — Soluciones Integrales Chaer

Marketplace web de servicios presenciales y remotos. Los clientes encuentran y contratan servicios concretos; los prestadores configuran sus aptitudes, cobertura, documentación y suscripción.

## Estado

El proyecto está en **Fase 0 — Descubrimiento y documentación**. Todavía no se instalaron dependencias ni se implementaron funcionalidades del marketplace.

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

## Reglas centrales

- El catálogo pertenece a SIC; el prestador habilita servicios del catálogo.
- No hay publicaciones públicas de clientes ni bolsa de trabajo.
- La ubicación solo condiciona modalidades presenciales.
- La documentación profesional requerida debe estar aprobada y vigente.
- La suscripción habilita visibilidad, pero no reemplaza las demás validaciones.
- El MVP cobra la suscripción del prestador; no procesa el pago del servicio entre cliente y prestador.
