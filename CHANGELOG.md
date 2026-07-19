# Changelog

## Unreleased

- Iniciada la Fase 0 documental de SIC.
- Registradas arquitectura, dominio, roadmap, seguridad, despliegue, referencias visuales y decisiones abiertas.
- Preparado el plan verificable para la Fase 1.
- Creada la primera portada responsive de SIC con Next.js y BFF de diagnóstico.
- Agregada la API FastAPI con healthchecks, request ID y pruebas.
- Preparada infraestructura Compose, migración PostGIS, worker, CI y scripts locales de Windows.
- Incorporada la estructura oficial Auth.js para Google, una pantalla de ingreso y el onboarding responsive de roles.
- Agregadas páginas preliminares de términos y privacidad sin presentarlas como asesoramiento legal final.
- Agregado el modelo PostgreSQL de usuarios y roles, migración, validación de token interno y caso de uso de selección de roles.
- Conectada la sincronización Google BFF/API con tokens de 60 segundos y ligado de identidad.
- Convertido el selector de roles en un formulario interactivo con guardado protegido y agregado el panel inicial del cliente.
- Agregado el dominio privado de direcciones, CRUD protegido, coordenadas PostGIS e índice GiST.
- Incorporada la pantalla responsive de direcciones, formulario y estado privado sin geocodificación ficticia.
- Conectada la capa BFF de Google Places New con Autocomplete, Place Details, cuota local y comprobantes de selección firmados.
- Agregado el corrector de pin con Maps Static firmado, proxy privado y límite de 500 metros respecto de la dirección validada.
- Incorporada la taxonomía canónica aprobada con 29 categorías, 140 subcategorías y 1.392 servicios, documentación íntegra y generador reproducible.
- Agregados modelos, migración, endpoints públicos, administración `ADMIN`, panel responsive y desactivación del catálogo sin borrado.
- Automatizados la exportación OpenAPI, los tipos TypeScript, PostgreSQL/PostGIS en CI y la ejecución doble del seed idempotente.
- Agregada la Fase 5 con onboarding y panel responsive del prestador, perfil, portfolio descriptivo y pausa global.
- Incorporada la configuración de múltiples servicios canónicos con precios permitidos, modalidades, cobertura PostGIS, agenda semanal y períodos no disponibles.
- Centralizada la visibilidad en `ProviderVisibilityService`, con diagnósticos internos y publicación denegada hasta documentación y suscripción válidas.
