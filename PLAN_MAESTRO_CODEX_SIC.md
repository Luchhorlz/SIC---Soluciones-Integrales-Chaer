# PROMPT MAESTRO PARA CODEX IA — SIC
## Soluciones Integrales Chaer
### Marketplace web de servicios presenciales y remotos

> Pegá este documento completo en el agente de Codex dentro de Visual Studio Code.  
> El agente debe tomarlo como especificación técnica, funcional y operativa del proyecto.

---

# 0. Rol del agente

Actuá como arquitecto de software, desarrollador full stack senior, especialista en seguridad, bases de datos geoespaciales, experiencia de usuario y DevOps.

Tu misión es construir una aplicación web llamada **SIC — Soluciones Integrales Chaer**, un marketplace donde:

- Los clientes buscan y contratan servicios concretos.
- Los prestadores seleccionan las aptitudes y servicios que ofrecen.
- Los servicios pueden ser presenciales, remotos, híbridos, en establecimiento o con retiro y entrega.
- Los prestadores pagan una mensualidad para estar visibles y recibir solicitudes.
- Los servicios presenciales se filtran por cercanía y zona de cobertura.
- Los servicios regulados requieren matrícula o documentación aprobada manualmente por un administrador.
- Los clientes no crean publicaciones públicas, estados ni búsquedas abiertas.
- La plataforma no es una bolsa de empleo ni un clon de LinkedIn.

Trabajá por fases pequeñas, verificables y reversibles. No intentes construir todo de una sola vez.

---

# 1. Reglas obligatorias de trabajo

1. Antes de escribir código:
   - Inspeccioná todo el repositorio.
   - Leé `AGENTS.md`, `README.md`, `docs/` y los archivos de configuración.
   - Informá qué existe, qué falta y qué vas a modificar.
   - No reemplaces código funcional sin justificarlo.

2. Usá documentación oficial y actualizada:
   - Next.js App Router.
   - FastAPI.
   - PostgreSQL y PostGIS.
   - Auth.js.
   - Mercado Pago.
   - Las bibliotecas elegidas en el proyecto.
   - No uses patrones obsoletos memorizados.
   - Consultá la documentación para agentes y `llms.txt` de Next.js cuando corresponda.

3. Mantené siempre actualizados:
   - `README.md`
   - `AGENTS.md`
   - `docs/architecture.md`
   - `docs/domain.md`
   - `docs/roadmap.md`
   - `docs/api.md`
   - `docs/security.md`
   - `docs/deployment.md`
   - `CHANGELOG.md`
   - ADRs en `docs/decisions/`

4. No realices acciones destructivas sin aprobación:
   - No borrar tablas.
   - No eliminar migraciones aplicadas.
   - No resetear bases de datos con información.
   - No sobrescribir archivos de usuario.
   - No cambiar secretos.
   - No ejecutar despliegues de producción.
   - No eliminar buckets ni documentos.

5. Nunca guardar secretos en Git:
   - Crear `.env.example`.
   - Usar variables de entorno.
   - Verificar que `.env`, credenciales, claves y archivos privados estén ignorados.

6. Cada cambio funcional debe incluir:
   - Código.
   - Tipado.
   - Validaciones.
   - Pruebas.
   - Manejo de errores.
   - Actualización de documentación.
   - Migración de base de datos cuando corresponda.

7. Antes de cerrar una tarea ejecutar, según corresponda:
   - lint
   - typecheck
   - tests unitarios
   - tests de integración
   - build
   - migraciones en una base temporal
   - tests end-to-end críticos

8. No inventes requisitos de negocio.
   - Si falta una decisión que afecta dinero, permisos, privacidad o funcionamiento central, presentá opciones y pedí confirmación.
   - Para decisiones técnicas internas, elegí la opción más simple, segura y mantenible y documentala mediante ADR.

9. No construir microservicios en la primera versión.
   - Usar un monolito modular desplegado en contenedores separados.
   - Separar responsabilidades por módulos, no por servicios distribuidos innecesarios.

10. Priorizar un MVP funcional.
    - No desarrollar funciones futuras antes de terminar y probar el núcleo.

---

# 2. Alcance funcional definitivo

## 2.1. Roles

Una cuenta puede tener uno o ambos roles:

- `CLIENT`
- `PROVIDER`

También existen roles administrativos:

- `ADMIN`
- `DOCUMENT_REVIEWER`
- `SUPPORT`

Una misma persona puede contratar servicios como cliente y ofrecer otros como prestador usando la misma cuenta de Google.

## 2.2. Cliente

El cliente puede:

- Registrarse e ingresar con Google.
- Completar teléfono y datos básicos.
- Guardar una o varias direcciones.
- Seleccionar una dirección para una búsqueda presencial.
- Buscar por categoría, subcategoría, servicio o texto libre.
- Filtrar prestadores cercanos.
- Buscar servicios remotos sin restricción geográfica.
- Ver perfiles públicos.
- Guardar favoritos.
- Seleccionar un servicio concreto de un prestador.
- Solicitar presupuesto o reservar según la configuración del servicio.
- Enviar detalles privados, imágenes y documentos dentro de una solicitud.
- Consultar el estado de sus solicitudes.
- Comunicarse con el prestador dentro de una contratación o solicitud.
- Calificar solo servicios completados.

El cliente no puede:

- Crear publicaciones públicas.
- Crear estados.
- Publicar “busco empleado”.
- Publicar solicitudes visibles para todos los prestadores.
- Calificar a alguien sin una contratación completada.

## 2.3. Prestador

El prestador puede:

- Activar su perfil de prestador.
- Elegir nombre personal o comercial.
- Completar descripción, experiencia y portfolio.
- Seleccionar múltiples servicios del catálogo oficial.
- Configurar cada servicio por separado.
- Definir modalidades, precio, cobertura, disponibilidad y urgencias.
- Cargar matrículas y documentación.
- Contratar y administrar su suscripción mensual.
- Aparecer en búsquedas solo cuando cumpla todas las reglas.
- Recibir solicitudes privadas de clientes.
- Aceptar, rechazar o presupuestar.
- Administrar agenda y días no disponibles.
- Comunicarse con clientes.
- Finalizar servicios y recibir opiniones verificadas.
- Pausar servicios individuales o todo el perfil.

## 2.4. Administrador

El administrador puede:

- Administrar usuarios y roles.
- Administrar categorías, subcategorías y servicios.
- Configurar qué documentación requiere cada servicio.
- Revisar, aprobar, observar, rechazar o suspender matrículas.
- Gestionar suscripciones.
- Ver auditoría de acciones.
- Suspender prestadores o servicios.
- Gestionar reportes y reclamos.
- Ver métricas operativas.
- Configurar textos, parámetros y reglas de visibilidad.

---

# 3. Fuera del alcance del MVP

No implementar inicialmente:

- Bolsa de trabajo.
- Publicaciones públicas de clientes.
- Feed social.
- Estados.
- Currículums.
- Contratación laboral.
- Nómina o liquidación de sueldos.
- Escrow.
- Pago del servicio del cliente al prestador dentro de SIC.
- Reparto automático del dinero del servicio.
- Sistema complejo de disputas financieras.
- Videollamadas propias.
- Aplicación móvil nativa.
- Microservicios.
- Kubernetes.
- Inteligencia artificial generativa en producción.
- Ranking opaco basado en aprendizaje automático.
- Internacionalización completa.
- Múltiples monedas en el MVP.

El MVP cobra únicamente la **suscripción mensual al prestador**.  
Los pagos por el trabajo entre cliente y prestador quedan fuera de la plataforma inicialmente, salvo decisión posterior explícita.

Diseñar interfaces internas para permitir integrar pagos de servicios en una fase futura sin reescribir el dominio.

---

# 4. Arquitectura recomendada

## 4.1. Enfoque

Usar una arquitectura de **monolito modular con Backend for Frontend**:

```text
Navegador
   |
   v
Next.js Web/BFF
   |
   v
FastAPI interna
   |
   +--> PostgreSQL + PostGIS
   +--> Redis
   +--> S3 compatible
   +--> Worker de tareas
   +--> Mercado Pago
   +--> Google Maps/Geocoding
```

## 4.2. Razones

- Next.js maneja interfaz, renderizado, SEO y sesión web.
- Auth.js maneja Google OAuth y sesión segura.
- El navegador no accede directamente a la API privada.
- Next.js actúa como BFF y valida la sesión.
- FastAPI concentra reglas de negocio y datos.
- PostgreSQL/PostGIS resuelve relaciones, transacciones y búsquedas geográficas.
- Redis se usa para caché, límites, colas y tareas.
- Un worker procesa tareas lentas o reintentables.
- El almacenamiento de objetos conserva imágenes y documentos fuera de la base.
- Los módulos están separados internamente, pero se despliegan sin complejidad de microservicios.

---

# 5. Stack técnico

## Frontend y BFF

- Next.js con App Router.
- TypeScript estricto.
- React.
- Tailwind CSS.
- Componentes accesibles basados en Radix UI o una capa equivalente.
- React Hook Form.
- Zod para validación de formularios.
- Auth.js con proveedor Google.
- TanStack Query solo donde aporte valor; priorizar Server Components para lectura.
- OpenAPI TypeScript client generado desde FastAPI.
- Playwright para E2E.
- Vitest para utilidades y componentes cuando corresponda.

## Backend

- Python estable compatible con dependencias.
- FastAPI.
- Pydantic.
- SQLAlchemy 2 en modo async.
- Alembic.
- PostgreSQL.
- PostGIS.
- Redis.
- Celery para tareas en segundo plano.
- Pytest.
- HTTPX para integraciones.
- SDK oficial o HTTP validado para Mercado Pago.
- OpenAPI como contrato principal.

## Infraestructura

- Docker y Docker Compose.
- Reverse proxy Caddy o Nginx.
- PostgreSQL con imagen PostGIS.
- Redis.
- MinIO en desarrollo y almacenamiento S3 compatible en producción.
- Mailpit en desarrollo.
- ClamAV o servicio equivalente para escaneo de archivos privados.
- GitHub Actions para CI.
- OpenTelemetry y/o Sentry para observabilidad.
- Backups automatizados.

## Gestores

- `pnpm` para JavaScript/TypeScript.
- `uv` o gestor Python fijado por lockfile.
- Versiones exactas bloqueadas.
- Renovación controlada de dependencias.

---

# 6. Estructura del repositorio

```text
sic-marketplace/
├─ AGENTS.md
├─ README.md
├─ CHANGELOG.md
├─ .env.example
├─ .gitignore
├─ docker-compose.yml
├─ Makefile
├─ apps/
│  ├─ web/
│  │  ├─ src/
│  │  │  ├─ app/
│  │  │  │  ├─ (public)/
│  │  │  │  ├─ (auth)/
│  │  │  │  ├─ (client)/
│  │  │  │  ├─ (provider)/
│  │  │  │  ├─ admin/
│  │  │  │  └─ api/
│  │  │  ├─ components/
│  │  │  ├─ features/
│  │  │  ├─ lib/
│  │  │  ├─ styles/
│  │  │  ├─ types/
│  │  │  └─ auth.ts
│  │  ├─ public/
│  │  │  ├─ brand/
│  │  │  ├─ icons/
│  │  │  └─ images/
│  │  ├─ tests/
│  │  └─ package.json
│  ├─ api/
│  │  ├─ src/
│  │  │  ├─ main.py
│  │  │  ├─ core/
│  │  │  ├─ db/
│  │  │  ├─ modules/
│  │  │  │  ├─ identity/
│  │  │  │  ├─ users/
│  │  │  │  ├─ addresses/
│  │  │  │  ├─ catalog/
│  │  │  │  ├─ providers/
│  │  │  │  ├─ provider_services/
│  │  │  │  ├─ documents/
│  │  │  │  ├─ subscriptions/
│  │  │  │  ├─ search/
│  │  │  │  ├─ requests/
│  │  │  │  ├─ bookings/
│  │  │  │  ├─ messaging/
│  │  │  │  ├─ reviews/
│  │  │  │  ├─ notifications/
│  │  │  │  ├─ media/
│  │  │  │  ├─ moderation/
│  │  │  │  ├─ audit/
│  │  │  │  └─ admin/
│  │  │  └─ integrations/
│  │  ├─ migrations/
│  │  ├─ tests/
│  │  └─ pyproject.toml
│  └─ worker/
│     ├─ src/
│     ├─ tests/
│     └─ pyproject.toml
├─ packages/
│  ├─ api-client/
│  ├─ ui/
│  ├─ config/
│  └─ shared-types/
├─ infra/
│  ├─ docker/
│  ├─ proxy/
│  ├─ scripts/
│  ├─ backups/
│  └─ monitoring/
├─ docs/
│  ├─ architecture.md
│  ├─ domain.md
│  ├─ api.md
│  ├─ security.md
│  ├─ deployment.md
│  ├─ roadmap.md
│  ├─ taxonomy.md
│  ├─ testing.md
│  └─ decisions/
└─ seeds/
   ├─ taxonomy.json
   ├─ service-requirements.json
   └─ demo-data.json
```

No crear paquetes vacíos innecesarios. Crear cada módulo cuando la fase lo requiera.

---

# 7. Límites de módulos

Cada módulo debe tener:

```text
module/
├─ api.py
├─ schemas.py
├─ service.py
├─ repository.py
├─ models.py
├─ permissions.py
├─ events.py
└─ tests/
```

Reglas:

- `api.py`: transporte HTTP, sin lógica de negocio compleja.
- `schemas.py`: entrada y salida.
- `service.py`: casos de uso y reglas.
- `repository.py`: persistencia.
- `models.py`: modelos SQLAlchemy.
- `permissions.py`: autorización.
- `events.py`: eventos internos.
- No acceder a tablas de otro módulo directamente salvo repositorio o contrato documentado.
- Evitar repositorios genéricos que oculten SQL importante.
- Las consultas geoespaciales deben estar explícitas y testeadas.
- Las transacciones deben comenzar en la capa de caso de uso.

---

# 8. Modelo de dominio

## 8.1. Usuarios y roles

### `users`

Campos mínimos:

- `id` UUID.
- `email`.
- `name`.
- `avatar_url`.
- `phone`.
- `phone_verified_at`.
- `status`.
- `created_at`.
- `updated_at`.
- `last_login_at`.

### `user_roles`

- `user_id`.
- `role`.
- `created_at`.

### Estados de usuario

- `ACTIVE`
- `SUSPENDED`
- `BLOCKED`
- `DELETED`

Usar borrado lógico para usuarios y perfiles. No borrar auditoría ni relaciones financieras.

## 8.2. Direcciones

### `addresses`

- `id`.
- `user_id`.
- `label`.
- `formatted_address`.
- `street`.
- `street_number`.
- `unit`.
- `city`.
- `administrative_area`.
- `province`.
- `postal_code`.
- `country_code`.
- `google_place_id`.
- `point geography(Point, 4326)`.
- `is_default`.
- `created_at`.
- `updated_at`.

Reglas:

- Guardar latitud/longitud en PostGIS.
- Crear índice GiST.
- No exponer dirección exacta públicamente.
- No registrar dirección exacta en logs.
- Cifrar campos especialmente sensibles si la estrategia de infraestructura lo permite.
- El cliente puede tener varias direcciones.

## 8.3. Catálogo

### `categories`

- `id`
- `name`
- `slug`
- `description`
- `icon_key`
- `position`
- `is_active`

### `subcategories`

- `id`
- `category_id`
- `name`
- `slug`
- `description`
- `icon_key`
- `position`
- `is_active`

### `services`

- `id`
- `subcategory_id`
- `name`
- `slug`
- `description`
- `icon_key`
- `is_active`
- `allows_fixed_price`
- `allows_quote`
- `allows_urgent`
- `created_at`
- `updated_at`

La taxonomía aprobada es canónica:

- No modificar nombres sin una migración de contenido.
- No eliminar servicios usados.
- Desactivar en lugar de borrar.
- Importar desde `seeds/taxonomy.json`.
- Guardar un código estable independiente del nombre visible.
- La lista maestra aprobada debe copiarse a `docs/taxonomy.md`.
- Si la lista no está disponible, detener la fase de seed y solicitarla al propietario.

## 8.4. Modalidades

Enum:

- `AT_CLIENT_ADDRESS`
- `REMOTE`
- `HYBRID`
- `AT_PROVIDER_LOCATION`
- `PICKUP_DELIVERY`

La modalidad pertenece a cada servicio habilitado por un prestador, no únicamente al perfil general.

## 8.5. Perfil de prestador

### `provider_profiles`

- `id`
- `user_id`
- `display_name`
- `slug`
- `business_name`
- `bio`
- `experience_years`
- `base_address_id`
- `base_point geography(Point, 4326)`
- `profile_status`
- `subscription_visibility_status`
- `rating_average`
- `rating_count`
- `completed_services_count`
- `response_rate`
- `average_response_minutes`
- `profile_completeness`
- `is_identity_verified`
- `paused_at`
- `created_at`
- `updated_at`

Estados:

- `DRAFT`
- `PENDING_REVIEW`
- `APPROVED`
- `PAUSED`
- `SUSPENDED`
- `BLOCKED`

No guardar `is_visible` como única fuente de verdad. La visibilidad debe derivarse de reglas.

## 8.6. Servicios del prestador

### `provider_services`

- `id`
- `provider_id`
- `service_id`
- `status`
- `headline`
- `description`
- `pricing_type`
- `price_amount`
- `price_currency`
- `estimated_duration_minutes`
- `guarantee_days`
- `accepts_urgent`
- `requires_quote_details`
- `created_at`
- `updated_at`

Estados:

- `DRAFT`
- `PENDING_DOCUMENTS`
- `PENDING_REVIEW`
- `ACTIVE`
- `PAUSED`
- `REJECTED`
- `SUSPENDED`

Tipos de precio:

- `FIXED`
- `FROM`
- `QUOTE`
- `HOURLY`
- `PER_SESSION`
- `PER_UNIT`

### `provider_service_modalities`

- `provider_service_id`
- `modality`
- `enabled`

### `provider_service_areas`

Para MVP:

- `id`
- `provider_service_id`
- `center geography(Point, 4326)`
- `radius_meters`
- `urgent_radius_meters`
- `travel_fee_policy`

Futuro:

- polígonos personalizados.
- zonas por localidad.
- múltiples centros.

## 8.7. Disponibilidad

### `availability_rules`

- `provider_id` o `provider_service_id`.
- `day_of_week`.
- `start_time`.
- `end_time`.
- `timezone`.
- `slot_duration_minutes`.
- `is_active`.

### `availability_exceptions`

- `provider_id`.
- `starts_at`.
- `ends_at`.
- `reason`.
- `is_available_override`.

No permitir dobles reservas si la reserva usa agenda confirmada.

## 8.8. Documentación profesional

### `service_document_requirements`

- `service_id`.
- `document_type`.
- `is_required`.
- `jurisdiction_type`.
- `requires_expiration`.
- `instructions`.

### `provider_documents`

- `id`.
- `provider_id`.
- `document_type`.
- `document_number`.
- `holder_name`.
- `issuer`.
- `jurisdiction`.
- `issued_at`.
- `expires_at`.
- `media_file_id`.
- `status`.
- `submitted_at`.
- `reviewed_at`.
- `reviewed_by`.
- `rejection_reason`.
- `internal_notes`.

Estados:

- `DRAFT`
- `UPLOADED`
- `SCANNING`
- `PENDING`
- `IN_REVIEW`
- `OBSERVED`
- `APPROVED`
- `REJECTED`
- `EXPIRED`
- `SUSPENDED`

### `document_reviews`

Registrar cada decisión:

- revisor.
- estado anterior.
- estado nuevo.
- motivo.
- fecha.
- IP o contexto administrativo.
- referencia de auditoría.

Nunca sobrescribir el historial.

## 8.9. Suscripciones

### `subscription_plans`

- `id`
- `name`
- `code`
- `price`
- `currency`
- `billing_frequency`
- `is_active`
- `features_json`
- `mercado_pago_plan_id`

Comenzar con un único plan si el propietario no define múltiples planes.

### `provider_subscriptions`

- `id`
- `provider_id`
- `plan_id`
- `provider_name`
- `external_subscription_id`
- `status`
- `current_period_start`
- `current_period_end`
- `cancel_at_period_end`
- `last_payment_status`
- `created_at`
- `updated_at`

Estados normalizados:

- `PENDING`
- `AUTHORIZED`
- `ACTIVE`
- `PAST_DUE`
- `PAUSED`
- `CANCELLED`
- `EXPIRED`
- `ERROR`

### `billing_events`

- `id`
- `provider_name`
- `external_event_id`
- `event_type`
- `payload_hash`
- `payload_encrypted_or_private_reference`
- `processed_at`
- `processing_status`
- `error_message`

Restricción única por evento externo para idempotencia.

## 8.10. Solicitudes y contrataciones

### `service_requests`

- `id`
- `client_id`
- `provider_service_id`
- `client_address_id`, nullable para remoto.
- `selected_modality`
- `title`
- `description`
- `preferred_start_at`
- `status`
- `created_at`
- `updated_at`

Estados:

- `DRAFT`
- `REQUESTED`
- `VIEWED`
- `QUOTED`
- `ACCEPTED`
- `DECLINED`
- `CANCELLED`
- `EXPIRED`
- `CONVERTED_TO_BOOKING`

### `quotes`

- `id`
- `request_id`
- `provider_id`
- `amount`
- `currency`
- `description`
- `valid_until`
- `status`

Estados:

- `SENT`
- `ACCEPTED`
- `REJECTED`
- `EXPIRED`
- `WITHDRAWN`

### `bookings`

- `id`
- `request_id`
- `client_id`
- `provider_id`
- `provider_service_id`
- `modality`
- `address_snapshot_encrypted`
- `starts_at`
- `ends_at`
- `agreed_price`
- `currency`
- `status`
- `completed_at`
- `cancelled_at`

Estados:

- `PENDING_PROVIDER`
- `CONFIRMED`
- `IN_PROGRESS`
- `COMPLETED`
- `CANCELLED_BY_CLIENT`
- `CANCELLED_BY_PROVIDER`
- `NO_SHOW`
- `DISPUTED`

No confundir la suscripción del prestador con el precio del servicio contratado.

## 8.11. Mensajería

### `conversations`

Siempre vinculada a una solicitud o contratación.

### `messages`

- `conversation_id`
- `sender_id`
- `body`
- `media_file_id`
- `created_at`
- `read_at`
- `moderation_status`

MVP:

- polling inteligente o Server-Sent Events.
- Evitar WebSocket hasta que sea necesario.
- Aplicar rate limiting.
- No permitir contacto masivo no solicitado.

## 8.12. Opiniones

### `reviews`

- `booking_id`
- `client_id`
- `provider_id`
- `rating`
- `comment`
- `status`
- `created_at`

Reglas:

- Solo una opinión por contratación completada.
- Rating entre 1 y 5.
- Moderación administrativa.
- Mantener historial si se edita.
- Calcular promedio de forma segura.
- Usar promedio bayesiano o mínimo de reseñas antes de destacar en fases futuras.

## 8.13. Auditoría

### `audit_logs`

- actor.
- rol.
- acción.
- entidad.
- entidad_id.
- cambios resumidos.
- request_id.
- fecha.
- contexto.

Auditar especialmente:

- cambios de roles.
- aprobación de matrículas.
- suspensiones.
- cambios de plan.
- eventos de pago.
- cambios de catálogo.
- acceso administrativo a documentos.

---

# 9. Regla central de visibilidad

Crear un servicio de dominio único: `ProviderVisibilityService`.

Un prestador o servicio aparece en búsquedas solo cuando:

- Usuario activo.
- Perfil de prestador aprobado.
- Perfil no pausado ni suspendido.
- Suscripción activa o autorizada según regla comercial.
- Servicio del prestador activo.
- Al menos una modalidad habilitada.
- Cobertura configurada si es presencial.
- Documentación requerida aprobada y vigente.
- Disponibilidad válida si el filtro la exige.
- No existe bloqueo administrativo.

No duplicar esta lógica en múltiples controladores.

El resultado debe incluir un código de diagnóstico interno:

- `VISIBLE`
- `NO_ACTIVE_SUBSCRIPTION`
- `PROFILE_NOT_APPROVED`
- `SERVICE_PAUSED`
- `DOCUMENT_PENDING`
- `DOCUMENT_EXPIRED`
- `NO_SERVICE_AREA`
- `ADMIN_SUSPENDED`

Estos motivos no se muestran completos al público, pero sí al prestador y al administrador.

---

# 10. Autenticación y autorización

## 10.1. Inicio con Google

- Usar Auth.js y Google Provider.
- Usar sesiones seguras.
- Cookies `HttpOnly`, `Secure` y `SameSite`.
- Rotar y proteger `AUTH_SECRET`.
- Vincular la identidad de Google con `users`.
- No confiar solo en datos enviados desde el navegador.
- Normalizar email.
- Controlar cuentas bloqueadas después de autenticar.

## 10.2. Patrón BFF

- El navegador se comunica con Next.js.
- Next.js valida la sesión.
- Next.js genera un token interno de vida corta para llamar a FastAPI.
- FastAPI no confía en un `user_id` enviado por el cliente.
- Token interno:
  - expiración máxima aproximada de 60 segundos.
  - `sub`: ID de usuario.
  - `roles`.
  - `session_id`.
  - `request_id`.
  - `aud`: `sic-api`.
  - firma con secreto distinto de Auth.js.
- FastAPI valida audiencia, firma y expiración.
- FastAPI debe estar en red privada, excepto:
  - healthchecks limitados.
  - webhooks necesarios.
  - documentación API deshabilitada o protegida en producción.

## 10.3. Autorización

Combinar:

- RBAC para roles.
- ABAC para propiedad y estado.

Ejemplos:

- Un cliente solo ve sus direcciones y solicitudes.
- Un prestador solo modifica su perfil y servicios.
- Un revisor puede revisar documentos, pero no cambiar planes.
- Un administrador puede suspender, pero toda acción queda auditada.
- Un documento privado solo es visible para su titular y revisores autorizados.

---

# 11. Geolocalización y búsqueda

## 11.1. Geocodificación

- Usar Google Places/Geocoding mediante una capa de integración.
- Guardar `place_id`, dirección normalizada y coordenadas.
- Permitir corregir el pin en el mapa.
- Aplicar restricciones de país configurables.
- No depender del texto libre para calcular distancias.

## 11.2. PostGIS

- Usar `geography(Point, 4326)`.
- Crear índices GiST.
- Usar `ST_DWithin` para filtro por radio.
- Usar `ST_Distance` solo después de reducir candidatos.
- Distancias en metros.
- Testear borde exacto del radio.
- Testear coordenadas inválidas.
- Limitar radios máximos configurables.

Consulta conceptual:

```sql
SELECT provider_services.*, 
       ST_Distance(service_area.center, :client_point) AS distance_meters
FROM provider_services
JOIN provider_service_areas service_area
  ON service_area.provider_service_id = provider_services.id
WHERE provider_services.service_id = :service_id
  AND provider_services.status = 'ACTIVE'
  AND ST_DWithin(
        service_area.center,
        :client_point,
        service_area.radius_meters
      )
ORDER BY distance_meters ASC;
```

No concatenar SQL. Usar parámetros.

## 11.3. Lógica por modalidad

### Presencial en domicilio

- Exige dirección seleccionada.
- Filtra por zona de cobertura.
- Muestra distancia aproximada.
- No muestra domicilio exacto del prestador.

### Remoto

- No filtra por distancia.
- Puede filtrar por idioma, horario, precio, rating y disponibilidad.
- La ubicación no debe afectar el ranking.

### Híbrido

- Requiere cobertura para la fase presencial.
- Debe informar claramente que combina remoto y presencial.

### En establecimiento

- Calcula distancia al establecimiento.
- Muestra zona y dirección pública del local si el prestador la autorizó.

### Retiro y entrega

- Valida cobertura del retiro.
- Puede configurar costo por zona.

## 11.4. Ranking MVP

Aplicar filtros duros primero.

Orden inicial configurable:

1. Coincidencia exacta de servicio.
2. Visibilidad válida.
3. Disponible ahora o en fecha solicitada.
4. Documentación verificada.
5. Calificación.
6. Cantidad de servicios completados.
7. Tiempo de respuesta.
8. Distancia, solo si aplica.
9. Perfil completo.

Los resultados promocionados deben:

- Mostrar etiqueta `Patrocinado` o `Destacado`.
- No ocultar resultados orgánicos.
- No alterar requisitos de seguridad.
- No permitir que un prestador sin documentación aparezca por pagar más.

---

# 12. Documentos, matrículas y archivos

## 12.1. Almacenamiento

- No guardar binarios en PostgreSQL.
- Usar bucket privado.
- Guardar metadatos en `media_files`.
- Generar URLs firmadas con vencimiento corto.
- Separar buckets o prefijos:
  - público.
  - portfolio.
  - documentos privados.
  - adjuntos de conversaciones.
- No usar URLs públicas permanentes para matrículas.

## 12.2. Validación

Al subir:

- Lista blanca de tipos MIME.
- Verificar contenido real, no solo extensión.
- Tamaño máximo.
- Nombre generado por UUID.
- Escaneo antivirus.
- Eliminar metadatos EXIF en imágenes públicas.
- Generar miniaturas.
- Rechazar archivos corruptos.
- Registrar hash SHA-256.
- Evitar duplicados y archivos ejecutables.

## 12.3. Revisión

Flujo:

1. Prestador selecciona servicio regulado.
2. Sistema detecta requisitos.
3. Prestador carga documento.
4. Documento queda `SCANNING`.
5. Worker valida.
6. Documento queda `PENDING`.
7. Revisor abre vista privada.
8. Puede aprobar, observar, rechazar o solicitar información.
9. Se registra auditoría.
10. Si vence, el servicio pasa a no visible.
11. Notificar con anticipación:
    - 30 días.
    - 15 días.
    - 7 días.
    - día de vencimiento.

---

# 13. Suscripción mensual

## 13.1. Integración

- Crear un adaptador `BillingProvider`.
- Implementar inicialmente `MercadoPagoBillingProvider`.
- No mezclar objetos de Mercado Pago con el dominio.
- Validar firmas de webhooks.
- Procesar webhooks de forma idempotente.
- Persistir el evento antes de procesarlo.
- Responder rápido al webhook.
- Procesar efectos en worker si es necesario.
- Reintentar de forma segura.

## 13.2. Visibilidad

- La suscripción activa habilita la posibilidad de aparecer.
- No garantiza visibilidad si falta documentación.
- Si vence:
  - ocultar servicios.
  - conservar perfil, historial, rating y documentos.
  - permitir regularización.
- No borrar información por falta de pago.

## 13.3. Plan inicial

Si no hay definición comercial final:

- Implementar un solo plan mensual configurable desde administración.
- Dejar el modelo preparado para múltiples planes.
- No crear tres planes ficticios sin aprobación.
- Precios y moneda deben venir de base/configuración, no estar hardcodeados.

---

# 14. Flujo de contratación del MVP

## Precio fijo

1. Cliente elige servicio del prestador.
2. Selecciona modalidad.
3. Elige dirección si corresponde.
4. Selecciona fecha o solicita coordinación.
5. Agrega detalles privados.
6. Envía solicitud.
7. Prestador acepta o rechaza.
8. Si acepta, se crea contratación.
9. Ambas partes coordinan.
10. Prestador marca en progreso.
11. Prestador marca completado.
12. Cliente confirma o reporta problema.
13. Se habilita la calificación.

## A presupuestar

1. Cliente selecciona prestador y servicio.
2. Describe necesidad.
3. Adjunta archivos.
4. Prestador envía presupuesto.
5. Cliente acepta o rechaza.
6. Si acepta, se crea contratación.

No crear una publicación pública en ningún paso.

---

# 15. API

## 15.1. Convenciones

- Prefijo `/v1`.
- JSON.
- UUID.
- Fechas ISO 8601 UTC.
- Códigos de error estables.
- Paginación por cursor para listados grandes.
- Paginación por página aceptable en paneles administrativos iniciales.
- Idempotency-Key para operaciones sensibles.
- Request ID en todas las respuestas.
- OpenAPI actualizado.
- Cliente TypeScript generado automáticamente.
- No duplicar DTOs manualmente en frontend.

## 15.2. Recursos principales

```text
GET    /v1/catalog/categories
GET    /v1/catalog/services
GET    /v1/search/providers
GET    /v1/providers/{slug}
GET    /v1/providers/{slug}/services

GET    /v1/me
PATCH  /v1/me
GET    /v1/me/addresses
POST   /v1/me/addresses
PATCH  /v1/me/addresses/{id}
DELETE /v1/me/addresses/{id}

POST   /v1/provider/onboarding
GET    /v1/provider/profile
PATCH  /v1/provider/profile
GET    /v1/provider/services
POST   /v1/provider/services
PATCH  /v1/provider/services/{id}
POST   /v1/provider/services/{id}/pause

POST   /v1/provider/documents
GET    /v1/provider/documents
POST   /v1/provider/subscription/checkout
GET    /v1/provider/subscription

POST   /v1/service-requests
GET    /v1/service-requests/{id}
POST   /v1/service-requests/{id}/quote
POST   /v1/service-requests/{id}/accept
POST   /v1/service-requests/{id}/decline

GET    /v1/bookings
GET    /v1/bookings/{id}
POST   /v1/bookings/{id}/start
POST   /v1/bookings/{id}/complete
POST   /v1/bookings/{id}/cancel

POST   /v1/bookings/{id}/reviews

GET    /v1/admin/documents
POST   /v1/admin/documents/{id}/approve
POST   /v1/admin/documents/{id}/observe
POST   /v1/admin/documents/{id}/reject

POST   /v1/webhooks/mercado-pago
```

Ajustar endpoints según REST y casos de uso. No implementar endpoints sin autorización ni tests.

---

# 16. Rutas web

## Públicas

```text
/
/servicios
/categoria/[categorySlug]
/categoria/[categorySlug]/[subcategorySlug]
/servicio/[serviceSlug]
/buscar
/prestador/[providerSlug]
/como-funciona
/para-prestadores
/planes
/terminos
/privacidad
```

## Autenticación y onboarding

```text
/ingresar
/onboarding
/onboarding/rol
/onboarding/cliente
/onboarding/prestador
/onboarding/prestador/servicios
/onboarding/prestador/cobertura
/onboarding/prestador/documentos
/onboarding/prestador/suscripcion
```

## Cliente

```text
/cuenta
/cuenta/direcciones
/cuenta/contrataciones
/cuenta/contrataciones/[id]
/cuenta/favoritos
/cuenta/mensajes
/cuenta/configuracion
```

## Prestador

```text
/prestador/panel
/prestador/perfil
/prestador/servicios
/prestador/servicios/[id]
/prestador/disponibilidad
/prestador/cobertura
/prestador/documentos
/prestador/suscripcion
/prestador/solicitudes
/prestador/contrataciones
/prestador/mensajes
/prestador/opiniones
/prestador/configuracion
```

## Administración

```text
/admin
/admin/usuarios
/admin/prestadores
/admin/documentos
/admin/documentos/[id]
/admin/suscripciones
/admin/catalogo
/admin/reportes
/admin/auditoria
/admin/configuracion
```

---

# 17. Diseño visual

## 17.1. Marca

Nombre:

- `SIC`
- Subtítulo: `Soluciones Integrales Chaer`

No modificar el texto del logo.

Paleta inicial:

```css
--sic-burgundy-950: #3B0814;
--sic-burgundy-900: #561020;
--sic-burgundy-700: #7A1730;
--sic-burgundy-600: #8F1D3A;
--sic-burgundy-100: #F8EDEF;

--sic-gold-600: #B98524;
--sic-gold-500: #D6A03A;
--sic-gold-100: #FFF4D6;

--sic-white: #FFFFFF;
--sic-surface: #F8F8F6;
--sic-border: #E6E4E1;
--sic-text: #1F2937;
--sic-muted: #667085;
--sic-success: #16865B;
--sic-error: #C62828;
--sic-info: #2563EB;
```

Usar bordó como principal y dorado como acento.  
No usar dorado para texto pequeño sobre blanco si no cumple contraste.

## 17.2. Tipografía

- Manrope o alternativa aprobada.
- Pesos claros y consistentes.
- No cargar múltiples familias innecesarias.
- Interfaz en español rioplatense neutral.

## 17.3. Componentes

Crear design tokens y componentes:

- Button.
- Input.
- Select.
- Combobox.
- SearchBox.
- AddressPicker.
- Modal.
- Drawer.
- Card.
- ProviderCard.
- ServiceCard.
- CategoryCard.
- StatusBadge.
- VerificationBadge.
- Rating.
- EmptyState.
- Skeleton.
- Toast.
- Pagination.
- Map.
- DataTable.
- FileUploader.
- DateTimePicker.
- PriceDisplay.
- Sidebar.
- Header.
- Footer.

## 17.4. Accesibilidad

Objetivo WCAG 2.2 AA:

- Navegación por teclado.
- Foco visible.
- Etiquetas.
- Mensajes de error asociados.
- Contraste.
- Áreas táctiles.
- Texto alternativo.
- No depender únicamente del color.
- Soporte para reducción de movimiento.
- Formularios comprensibles.
- Mapas con alternativa en lista.

## 17.5. Responsive

Diseñar primero para móvil y luego:

- móvil.
- tablet.
- escritorio.
- escritorio ancho.

La búsqueda debe seguir siendo usable sin mapa.  
En móvil, mostrar lista y mapa mediante pestañas.

---

# 18. SEO y contenido público

- Server rendering para páginas públicas.
- Metadatos únicos.
- URLs legibles.
- Sitemap.
- Robots.
- Canonical.
- Open Graph.
- JSON-LD apropiado.
- No indexar paneles, cuentas ni documentos.
- Páginas de categoría con contenido real, no texto duplicado.
- Perfil público indexable solo si está visible.
- Si un perfil se pausa, devolver página informativa o `noindex` según estrategia.
- No exponer datos privados en HTML.

---

# 19. Seguridad

Aplicar defensa en profundidad:

- CSRF donde corresponda.
- CSP.
- CORS restrictivo.
- Rate limiting por IP, usuario y acción.
- Protección contra enumeración.
- Validación server-side.
- SQL parametrizado.
- Protección XSS.
- Sanitización de contenido enriquecido.
- Control de acceso por recurso.
- URLs firmadas.
- Escaneo de archivos.
- Límites de tamaño.
- Logs sin secretos ni domicilios completos.
- Cifrado TLS.
- Rotación de secretos.
- Webhooks firmados e idempotentes.
- Contraseñas no aplican al usuario final si solo hay Google, pero proteger cuentas administrativas.
- Sesiones revocables.
- Bloqueo de cuentas.
- Auditoría.
- Backups cifrados.
- Restauraciones probadas.
- Dependencias auditadas.
- Cabeceras de seguridad.
- Modo producción sin debug.
- Documentación OpenAPI protegida.

Crear un modelo de amenazas en `docs/security.md` incluyendo:

- robo de sesión.
- falsificación de identidad.
- prestador con matrícula ajena.
- documento malicioso.
- exposición de domicilio.
- webhook repetido.
- manipulación de suscripción.
- scraping.
- spam.
- opiniones falsas.
- escalada de privilegios.
- acceso administrativo indebido.

---

# 20. Privacidad

- Minimización de datos.
- Domicilio exacto solo para las partes cuando sea necesario.
- Ubicación pública aproximada.
- No mostrar coordenadas exactas.
- No reutilizar documentos para marketing.
- Permitir exportación y solicitud de baja.
- Retención documentada.
- Borrado lógico y anonimización cuando corresponda.
- Consentimientos separados para comunicaciones.
- No almacenar más datos de Google de los necesarios.
- Mantener políticas editables y versionadas.

No redactar afirmaciones legales definitivas sin revisión profesional.

---

# 21. Tareas en segundo plano

Usar Celery para:

- envío de correos.
- notificaciones.
- procesamiento de imágenes.
- escaneo de archivos.
- generación de miniaturas.
- verificación de vencimientos.
- recordatorios de suscripción.
- procesamiento de webhooks.
- recalcular métricas.
- limpieza de archivos temporales.

Reglas:

- Tareas idempotentes.
- Reintentos con backoff.
- Límite de reintentos.
- Dead-letter o registro de fallos.
- Correlation/request ID.
- No enviar información sensible en el nombre de la tarea.
- Monitorear cola y fallos.

---

# 22. Observabilidad

Implementar:

- Logs JSON estructurados.
- Request ID.
- User ID interno cuando sea seguro.
- Métricas:
  - latencia.
  - errores.
  - búsquedas.
  - cero resultados.
  - conversiones a solicitud.
  - documentos pendientes.
  - suscripciones activas.
  - webhooks fallidos.
  - tareas fallidas.
- Trazas.
- Healthchecks:
  - `/health/live`
  - `/health/ready`
- Alertas para:
  - errores elevados.
  - base sin conexión.
  - cola detenida.
  - almacenamiento inaccesible.
  - webhooks fallando.
  - backups fallidos.
  - certificados próximos a vencer.

No incluir PII innecesaria en telemetría.

---

# 23. Pruebas

## Backend

- Unitarias para reglas de dominio.
- Integración con PostgreSQL/PostGIS real.
- Tests de migraciones.
- Tests de permisos.
- Tests de idempotencia.
- Tests de webhooks.
- Tests de expiración documental.
- Tests de visibilidad.
- Tests de búsqueda geográfica.

Casos geográficos obligatorios:

- dentro del radio.
- fuera del radio.
- exactamente en el borde.
- servicio remoto.
- híbrido sin cobertura.
- dirección sin coordenadas.
- proveedor sin zona.
- documento vencido.
- suscripción vencida.

## Frontend

- Unitarias de utilidades.
- Componentes críticos.
- Formularios.
- Estados de carga/error/vacío.
- Accesibilidad automática.
- E2E con Playwright.

Flujos E2E mínimos:

1. Login Google simulado.
2. Cliente completa dirección.
3. Prestador completa onboarding.
4. Prestador habilita servicio.
5. Prestador carga matrícula.
6. Admin aprueba matrícula.
7. Prestador activa suscripción en sandbox.
8. Cliente busca servicio cercano.
9. Cliente envía solicitud.
10. Prestador acepta.
11. Servicio se completa.
12. Cliente califica.

Crear fixtures y fábricas.  
No depender de servicios externos reales en CI.

---

# 24. Entornos

## Desarrollo

Docker Compose con:

- web.
- api.
- worker.
- postgres-postgis.
- redis.
- minio.
- mailpit.
- clamav opcional.
- proxy opcional.

## Staging

- Dominio separado.
- Credenciales sandbox.
- Base separada.
- Bucket separado.
- Datos ficticios.
- Misma arquitectura que producción.

## Producción

- Contenedores separados.
- TLS.
- API interna no expuesta.
- Base con backups.
- Redis protegido.
- S3 privado.
- Secrets manager o variables seguras.
- Migraciones controladas.
- Rollback.
- Monitoreo.

No usar Kubernetes para el MVP.  
Preparar imágenes Docker portables.

---

# 25. Variables de entorno

Crear `.env.example` documentado:

```env
APP_ENV=
APP_URL=
API_INTERNAL_URL=

DATABASE_URL=
REDIS_URL=

AUTH_SECRET=
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=

INTERNAL_API_JWT_SECRET=

GOOGLE_MAPS_API_KEY=
GOOGLE_MAPS_COUNTRY_RESTRICTION=AR

MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_PUBLIC_KEY=
MERCADOPAGO_WEBHOOK_SECRET=
MERCADOPAGO_SUCCESS_URL=
MERCADOPAGO_FAILURE_URL=

S3_ENDPOINT=
S3_REGION=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET_PUBLIC=
S3_BUCKET_PRIVATE=

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=

SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
```

No todas deben ser obligatorias en la primera fase.  
Validarlas al iniciar según el entorno.

---

# 26. CI/CD

Pipeline mínimo:

1. Checkout.
2. Instalar dependencias con lockfiles.
3. Lint frontend.
4. Typecheck frontend.
5. Tests frontend.
6. Build frontend.
7. Lint backend.
8. Typecheck backend.
9. Tests backend.
10. Levantar PostgreSQL/PostGIS temporal.
11. Ejecutar migraciones.
12. Tests de integración.
13. Generar y verificar OpenAPI client.
14. Construir imágenes Docker.
15. Escaneo de dependencias e imágenes.
16. Publicar artefactos.
17. Deploy a staging con aprobación.
18. Smoke tests.
19. Producción mediante aprobación manual.

Nunca desplegar automáticamente a producción desde una rama no protegida.

---

# 27. Backups

- Backup diario de PostgreSQL.
- Retención configurable.
- Backup de documentos privados.
- Cifrado.
- Copia fuera del servidor principal.
- Prueba de restauración periódica.
- Documentar RPO y RTO.
- Antes de migraciones de alto impacto, crear backup verificado.
- No considerar un backup válido hasta probar restauración.

---

# 28. Fases de implementación

## Fase 0 — Descubrimiento y documentación

Entregables:

- Auditoría del repositorio.
- `README.md`.
- `AGENTS.md`.
- arquitectura.
- dominio.
- roadmap.
- modelo de amenazas inicial.
- decisiones abiertas.
- wireframes/rutas.
- inventario de assets.
- lista de variables.

Criterio de aceptación:

- No hay código funcional complejo todavía.
- Arquitectura aprobada.
- Alcance MVP congelado.
- Taxonomía y logo identificados.

## Fase 1 — Base del monorepo

Entregables:

- Next.js.
- FastAPI.
- PostgreSQL/PostGIS.
- Redis.
- Docker Compose.
- healthchecks.
- lint/typecheck/tests básicos.
- CI.
- migración inicial.
- OpenAPI client generado.

Criterio:

- `docker compose up` inicia todo.
- web llama a healthcheck de API.
- migraciones funcionan desde cero.
- CI verde.

## Fase 2 — Identidad, Google y roles

Entregables:

- Auth.js Google.
- sincronización de usuario.
- BFF.
- token interno.
- roles.
- onboarding de rol.
- protección de rutas.
- auditoría básica.

Criterio:

- usuario puede entrar.
- activar cliente, prestador o ambos.
- no puede acceder a rutas ajenas.
- cuentas suspendidas no operan.

## Fase 3 — Direcciones y geocodificación

Entregables:

- CRUD de direcciones.
- selector de mapa.
- geocodificación.
- PostGIS.
- privacidad.
- dirección por defecto.

Criterio:

- usuario guarda dirección válida.
- se persiste `Point`.
- nunca se muestra públicamente la dirección exacta.

## Fase 4 — Catálogo y administración

Entregables:

- categorías.
- subcategorías.
- servicios.
- seed idempotente.
- icon keys.
- panel CRUD controlado.
- desactivación sin borrado.

Criterio:

- taxonomía canónica cargada.
- slugs únicos.
- no hay duplicados.
- seed se puede ejecutar más de una vez.

## Fase 5 — Perfil y servicios del prestador

Entregables:

- onboarding.
- perfil.
- portfolio.
- selección de aptitudes.
- modalidades.
- precios.
- cobertura.
- disponibilidad.
- pausa.

Criterio:

- prestador configura varios servicios.
- cada uno tiene modalidad y cobertura propia.
- todavía no aparece si faltan requisitos.

## Fase 6 — Documentación y aprobación

Entregables:

- requisitos por servicio.
- upload privado.
- escaneo.
- panel de revisión.
- estados.
- auditoría.
- vencimientos.

Criterio:

- servicio regulado no se activa sin aprobación.
- documento privado no es público.
- aprobación activa el requisito, no todo el perfil indiscriminadamente.

## Fase 7 — Suscripciones

Entregables:

- plan configurable.
- Mercado Pago sandbox.
- checkout.
- webhooks.
- idempotencia.
- estado.
- visibilidad por pago.

Criterio:

- pago sandbox activa suscripción.
- webhook repetido no duplica efectos.
- vencimiento oculta servicios sin borrar datos.

## Fase 8 — Búsqueda y perfiles públicos

Entregables:

- búsqueda por catálogo.
- filtro cercano.
- remoto.
- híbrido.
- mapa/lista.
- filtros.
- ranking inicial.
- perfiles públicos.
- SEO.

Criterio:

- un plomero fuera de cobertura no aparece.
- un diseñador remoto puede aparecer sin distancia.
- prestador no visible no aparece aunque la URL exista públicamente.
- mapa y lista coinciden.

## Fase 9 — Solicitudes, presupuestos y contrataciones

Entregables:

- solicitud privada.
- adjuntos.
- presupuesto.
- aceptación/rechazo.
- contratación.
- agenda.
- estados.
- permisos.

Criterio:

- no existe publicación pública.
- solo cliente y prestador involucrados acceden.
- estados inválidos son rechazados.

## Fase 10 — Mensajería, notificaciones y opiniones

Entregables:

- conversación por solicitud.
- notificaciones.
- correos.
- opiniones verificadas.
- favoritos.

Criterio:

- no hay chat sin contexto válido.
- solo contratación completada permite opinión.
- rating se actualiza correctamente.

## Fase 11 — Paneles operativos

Entregables:

- dashboard cliente.
- dashboard prestador.
- dashboard administrador.
- métricas.
- soporte.
- reportes.
- moderación.

Criterio:

- cada rol ve solo lo necesario.
- acciones sensibles auditadas.
- estados vacíos y errores diseñados.

## Fase 12 — Hardening y lanzamiento

Entregables:

- auditoría de seguridad.
- pruebas de carga.
- accesibilidad.
- SEO.
- backups.
- restore test.
- observabilidad.
- staging.
- manual de operación.
- runbooks.
- política de incidentes.

Criterio:

- checklist de producción aprobado.
- cero secretos en repo.
- CI verde.
- migración y rollback ensayados.
- backups restaurables.
- flujos críticos E2E verdes.

---

# 29. Datos de demostración

Crear seed de demo solo para desarrollo:

- Clientes ficticios.
- Prestadores ficticios.
- Servicios presenciales.
- Servicios remotos.
- Proveedores dentro y fuera de radio.
- Documentos en todos los estados.
- Suscripciones en todos los estados.
- Solicitudes y contrataciones.
- Opiniones.

Marcar claramente que los datos son ficticios.  
Nunca copiar datos reales a desarrollo.

---

# 30. Criterios de calidad

## Código

- Tipado estricto.
- Funciones pequeñas.
- Nombres explícitos.
- Sin código duplicado evidente.
- Sin `any` injustificado.
- Sin excepciones silenciadas.
- Sin TODOs críticos sin ticket.
- Comentarios sobre el porqué, no sobre lo obvio.
- Dependencias justificadas.

## Base de datos

- Constraints.
- Foreign keys.
- índices.
- timestamps.
- estados controlados.
- migraciones reversibles cuando sea razonable.
- consultas explicadas para endpoints críticos.
- no N+1.

## UX

- carga.
- error.
- vacío.
- éxito.
- móvil.
- accesibilidad.
- confirmación para acciones destructivas.
- mensajes claros.
- precios y modalidades visibles.

## Seguridad

- deny by default.
- validación en servidor.
- permisos testeados.
- archivos privados.
- auditoría.
- rate limiting.
- idempotencia.

---

# 31. Definición de terminado

Una tarea no está terminada hasta que:

- Cumple el requerimiento.
- Tiene pruebas.
- Pasa lint.
- Pasa typecheck.
- Pasa build.
- La migración funciona.
- Los permisos están verificados.
- Se contemplan carga/error/vacío.
- Es responsive.
- Es accesible.
- Se actualizó documentación.
- Se informó qué cambió.
- Se informó qué no se hizo.
- No hay secretos.
- No hay regresiones conocidas.

---

# 32. Formato de respuesta del agente

Después de cada trabajo responder:

## Resumen

Qué se implementó.

## Archivos modificados

Lista breve.

## Decisiones

Decisiones técnicas tomadas y ADR asociado.

## Verificaciones

Comandos ejecutados y resultado.

## Riesgos o pendientes

Problemas, límites o decisiones necesarias.

## Próximo paso recomendado

Una sola fase o tarea concreta.

No afirmar que algo funciona si no fue ejecutado o probado.

---

# 33. Primera orden de ejecución

Al recibir este prompt:

1. No escribas todavía funcionalidades del marketplace.
2. Inspeccioná el workspace actual.
3. Informá:
   - estructura.
   - tecnologías existentes.
   - archivos relevantes.
   - conflictos con esta arquitectura.
   - assets disponibles.
   - estado de Git.
4. Creá o proponé:
   - `AGENTS.md`
   - `docs/architecture.md`
   - `docs/domain.md`
   - `docs/roadmap.md`
   - `docs/decisions/0001-modular-monolith.md`
   - `docs/open-questions.md`
5. Prepará un plan exacto para la Fase 1.
6. No instales dependencias ni borres archivos hasta mostrar el plan.
7. Pedí únicamente las decisiones de negocio imprescindibles.

---

# 34. Decisiones abiertas que deben confirmarse

Registrar en `docs/open-questions.md`:

1. Nombre de dominio definitivo.
2. País inicial: Argentina.
3. Provincia/localidades iniciales.
4. Plan mensual único o varios planes.
5. Precio final de la suscripción.
6. Período de prueba.
7. Si el prestador puede mostrar teléfono antes de una solicitud.
8. Si habrá comisión futura por contratación.
9. Política de cancelaciones.
10. Quién confirma que el servicio fue completado.
11. Política de moderación de opiniones.
12. Documentación exacta exigida por profesión y jurisdicción.
13. Radio máximo permitido.
14. Idiomas admitidos para servicios remotos.
15. Proveedor definitivo de correo.
16. Infraestructura inicial.
17. Política de retención de documentos.
18. Reglas de perfiles destacados.
19. Si habrá chat desde el MVP.
20. Textos legales revisados por profesional.

No bloquear la Fase 1 por preguntas comerciales que todavía no sean necesarias. Usar configuración y feature flags.

---

# 35. Principio rector

Construí SIC como una plataforma confiable, clara y operable:

> El catálogo pertenece a la plataforma.  
> El prestador habilita sus aptitudes.  
> El cliente encuentra y contrata una solución concreta.  
> La ubicación se usa solamente cuando la modalidad lo requiere.  
> La documentación profesional debe estar aprobada.  
> La suscripción habilita visibilidad, pero nunca reemplaza seguridad, reputación o cumplimiento.

