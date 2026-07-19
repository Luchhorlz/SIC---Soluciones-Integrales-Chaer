# Dominio

## Actores

Una cuenta puede tener roles `CLIENT` y `PROVIDER` simultáneamente. Los roles operativos son `ADMIN`, `DOCUMENT_REVIEWER` y `SUPPORT`.

## Agregados principales

- Usuario y roles: identidad Google, datos básicos, estado y autorización.
- Direcciones: varias por cliente, coordenadas PostGIS y privacidad estricta.
- Catálogo: categorías, subcategorías y servicios canónicos administrados por SIC.
- Prestador: perfil, servicios habilitados, modalidad, precio, área y disponibilidad.
- Documentación: requisitos por servicio, archivos privados, revisiones inmutables y vencimientos.
- Suscripción: plan, estado externo normalizado y eventos idempotentes.
- Solicitud/presupuesto/contratación: flujo privado entre cliente y prestador.
- Mensajería: siempre vinculada a una solicitud o contratación válida.
- Opinión: una por contratación completada.
- Auditoría: acciones sensibles, actor, contexto y cambios resumidos.

## Modalidades

`AT_CLIENT_ADDRESS`, `REMOTE`, `HYBRID`, `AT_PROVIDER_LOCATION` y `PICKUP_DELIVERY`. La modalidad se configura por servicio del prestador, no solo por perfil.

## Visibilidad

`ProviderVisibilityService` deriva la visibilidad. Exige usuario activo, perfil aprobado y no pausado, suscripción válida, servicio activo, modalidad, cobertura cuando corresponda, documentación aprobada/vigente y ausencia de bloqueo administrativo.

El perfil del prestador puede contener hasta 12 casos descriptivos de portfolio. En Fase 5 no acepta URLs externas ni archivos simulados; las imágenes se incorporarán mediante el módulo de medios con almacenamiento controlado.

La disponibilidad semanal pertenece a cada servicio. Los períodos no disponibles —vacaciones u otros bloqueos privados— pertenecen al perfil y se guardan como excepciones con zona horaria explícita de Argentina.

Los diagnósticos internos incluyen `VISIBLE`, `NO_ACTIVE_SUBSCRIPTION`, `PROFILE_NOT_APPROVED`, `SERVICE_PAUSED`, `DOCUMENT_PENDING`, `DOCUMENT_EXPIRED`, `NO_SERVICE_AREA` y `ADMIN_SUSPENDED`.

## Suscripción mensual

`subscription_plans` conserva nombre, código, precio, moneda, frecuencia y beneficios configurables; el MVP admite un solo plan activo sin impedir futuros planes. `provider_subscriptions` guarda la relación interna y normaliza `PENDING`, `AUTHORIZED`, `ACTIVE`, `PAST_DUE`, `PAUSED`, `CANCELLED`, `EXPIRED` y `ERROR`. Los objetos y nombres de estado de Mercado Pago no se filtran al resto del dominio.

`billing_events` se inserta antes de aplicar efectos y tiene unicidad por evento externo. No almacena el cuerpo ni correo del pagador: conserva hash SHA-256, referencia privada, tipo, resultado y error saneado. Una suscripción `ACTIVE` o `AUTHORIZED` satisface únicamente el requisito financiero de visibilidad; los demás estados producen `NO_ACTIVE_SUBSCRIPTION`.

## Documentación profesional

`service_document_requirements` vincula un código documental estable a un servicio canónico. Un documento aprobado puede satisfacer el mismo tipo requerido por más de un servicio del prestador, pero no habilita tipos ni servicios diferentes. La ausencia de requisitos activos significa que el servicio no necesita documentación profesional.

El flujo válido es `SCANNING → PENDING → IN_REVIEW → APPROVED|OBSERVED|REJECTED`; un aprobado puede pasar a `SUSPENDED` o `EXPIRED`. Cada decisión humana y vencimiento automático agrega un `document_review` con estado anterior, nuevo estado y referencia de auditoría. Los reemplazos se cargan como documentos nuevos para preservar los envíos anteriores.

## Contratación MVP

Para precio fijo o presupuesto, el cliente elige un servicio concreto y envía datos privados. El prestador acepta, rechaza o cotiza. Al aceptar se crea una contratación; el prestador inicia/completa y el cliente confirma o reporta. Solo entonces se habilita una opinión.

El pago del trabajo ocurre fuera de SIC en el MVP. Mercado Pago se usa únicamente para la suscripción mensual del prestador.

## Invariantes

- No existen solicitudes públicas ni feed social.
- La suscripción nunca omite documentación o bloqueos.
- Una opinión requiere contratación completada.
- La dirección exacta no es pública.
- Los documentos profesionales no tienen URL pública permanente.
- El historial documental, financiero y de auditoría no se sobrescribe.
- Los elementos usados del catálogo se desactivan; no se borran.
- La taxonomía canónica contiene 29 categorías, 140 subcategorías y 1.392 servicios. La sección 30 de la lista aprobada define filtros transversales y no se importa como oficio.
- Hasta que una fase comercial apruebe modalidades específicas, el seed habilita `presupuesto` y deja desactivados `precio fijo` y `urgente`; el administrador puede ajustarlos explícitamente.
