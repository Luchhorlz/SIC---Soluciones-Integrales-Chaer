# Seguridad

## Modelo de amenazas inicial

- Robo de sesión: cookies seguras, sesiones revocables, CSP y rotación de secretos.
- Suplantación o matrícula ajena: identidad vinculada, archivos privados, revisión humana e historial inmutable.
- Documento malicioso: lista MIME, inspección real, límites, hash, antivirus y nombres UUID.
- Exposición de domicilio: minimización, acceso por recurso y logs sin dirección exacta.
- Webhook repetido/manipulado: firma, clave externa única, persistencia previa e idempotencia.
- Manipulación de suscripción: adaptador aislado y estado derivado de eventos verificados.
- Scraping/spam: rate limits por IP/usuario/acción y protección contra enumeración.
- Opiniones falsas: contratación completada y una opinión por booking.
- Escalada de privilegios: deny by default, RBAC+ABAC, pruebas de permisos y auditoría.
- Acceso administrativo indebido: mínimos privilegios, trazabilidad y sesiones reforzadas.

## Controles base

Validación server-side, SQL parametrizado, CORS restrictivo, CSRF donde aplique, CSP, TLS, URLs firmadas, buckets privados, secretos fuera de Git, logs sin PII innecesaria, webhooks idempotentes, backups cifrados y restauraciones probadas.

## Host Windows

La API de control escucha únicamente en loopback, requiere un token local protegido y no expone secretos en la UI ni logs. Online/Offline controla procesos de forma explícita. Las credenciales del Named Tunnel quedan fuera del repositorio y con permisos restrictivos.

Este documento es un modelo técnico inicial, no una afirmación legal definitiva.
