# SIC — Soluciones Integrales Chaer

Marketplace web de servicios presenciales y remotos. Los clientes encuentran y contratan servicios concretos; los prestadores configuran sus aptitudes, cobertura, documentación y suscripción.

## Estado

El proyecto alcanzó la **Fase 10 — Comunicación y reputación verificadas**. La base del monorepo, identidad, direcciones privadas, catálogo, oferta profesional, revisión documental, suscripción mensual, búsqueda segura, contratación privada, mensajería contextual, notificaciones, favoritos y opiniones verificadas están implementados; las credenciales externas y la ejecución completa de PostgreSQL/PostGIS, MinIO, ClamAV, SMTP y Mercado Pago sandbox siguen siendo requisitos del entorno local.

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

- `/servicios`: directorio público de las 29 categorías canónicas.
- `/categoria/{slug}` y `/categoria/{slug}/{subcategorySlug}`: navegación por subcategorías y servicios.
- `/servicio/{slug}`: detalle SEO del servicio y búsqueda de prestadores visibles.
- `/buscar`: búsqueda por catálogo, modalidad, ubicación aproximada, disponibilidad, lista y mapa.
- `/prestador/{slug}`: perfil público seguro; responde como no disponible si no supera visibilidad central.
- `/solicitar/{slug}/{offerId}`: solicitud privada sobre una oferta visible, con preferencia horaria y adjuntos controlados.
- `/ingresar`: ingreso con Google y estado de configuración.
- `/onboarding/rol`: selección interactiva de cliente/prestador.
- `/cuenta`: panel inicial del cliente.
- `/cuenta/contrataciones`: solicitudes, presupuestos y turnos privados del cliente.
- `/cuenta/mensajes`: conversaciones privadas ligadas a solicitudes o turnos.
- `/cuenta/notificaciones`: actividad transaccional del cliente.
- `/cuenta/favoritos`: prestadores visibles guardados por el cliente.
- `/cuenta/direcciones`: gestión privada de direcciones y vista geográfica.
- `/admin/catalogo`: administración protegida de categorías, subcategorías y servicios.
- `/onboarding/prestador`: activación del perfil profesional.
- `/prestador/panel`: resumen privado y diagnóstico de visibilidad.
- `/prestador/perfil`: perfil, experiencia y portfolio.
- `/prestador/servicios`: aptitudes, modalidades, precios, cobertura y disponibilidad.
- `/prestador/solicitudes`: bandeja privada para ver, cotizar, aceptar o rechazar pedidos.
- `/prestador/contrataciones`: agenda privada para iniciar, completar, cancelar o registrar ausencia.
- `/prestador/mensajes`: conversaciones contextuales con clientes legítimos.
- `/prestador/opiniones`: reseñas verificadas recibidas y su estado de moderación.
- `/prestador/notificaciones`: actividad transaccional del perfil.
- `/prestador/documentacion`: requisitos, carga privada y seguimiento de documentos.
- `/admin/documentos`: configuración de requisitos y cola de revisión protegida.
- `/prestador/suscripcion`: plan mensual, checkout externo y estado verificado.
- `/admin/suscripciones`: configuración protegida del plan mensual real.
- `/admin/opiniones`: cola protegida para publicar, rechazar u ocultar reseñas.

La geocodificación requiere Places API (New), Maps Static API, `GOOGLE_MAPS_API_KEY` y `GOOGLE_MAPS_URL_SIGNING_SECRET`. Ambos valores permanecen fuera de Git y del JavaScript enviado al navegador.

El catálogo aprobado se genera desde la lista entregada por el propietario y se importa de forma repetible:

```powershell
cd apps\api
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m sic_api.modules.catalog.seed --file ..\..\seeds\taxonomy.json
```

El mismo comando puede ejecutarse nuevamente: actualiza por código estable y no duplica registros.

Los requisitos documentales no se infieren ni se inventan. `seeds/service-requirements.json` comienza vacío y administración los configura por servicio y jurisdicción. Las cargas admiten PDF, PNG y JPEG de hasta 10 MB, se guardan en el bucket privado y deben pasar ClamAV antes de entrar a revisión.

El plan de suscripción también comienza sin datos ficticios: un `ADMIN` define nombre, precio, moneda y beneficios. El checkout sólo se habilita con un plan activo, credenciales sandbox, URL de retorno y secreto de webhook. La URL pública de notificaciones prevista es `/api/webhooks/mercado-pago`; Next.js conserva la API detrás del BFF y reenvía la firma y el cuerpo originales.

Los correos de actividad son transaccionales y salen desde el worker mediante una bandeja persistente. En desarrollo se entregan a Mailpit cuando `SMTP_HOST` y `EMAIL_FROM` están configurados; sin SMTP, las notificaciones dentro de SIC continúan funcionando y no se intenta una entrega externa.

## Reglas centrales

- El catálogo pertenece a SIC; el prestador habilita servicios del catálogo.
- No hay publicaciones públicas de clientes ni bolsa de trabajo.
- La ubicación solo condiciona modalidades presenciales.
- La documentación profesional requerida debe estar aprobada y vigente.
- La suscripción habilita visibilidad, pero no reemplaza las demás validaciones.
- El MVP cobra la suscripción del prestador; no procesa el pago del servicio entre cliente y prestador.
