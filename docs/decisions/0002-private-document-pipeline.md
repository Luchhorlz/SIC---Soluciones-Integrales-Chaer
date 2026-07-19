# ADR 0002: Pipeline privado de documentación profesional

- Estado: aceptada
- Fecha: 2026-07-18

## Contexto

SIC debe recibir matrículas y certificados sensibles, verificar archivos maliciosos, permitir revisión humana y ocultar servicios cuando un requisito vence. Guardar binarios en PostgreSQL o publicar enlaces permanentes aumenta el impacto de una filtración y dificulta la operación.

## Decisión

Guardar el contenido en un bucket S3 compatible privado y conservar en PostgreSQL únicamente metadatos, SHA-256, estado y clave de objeto. La API valida contenido y tamaño, crea una clave UUID y consulta ClamAV mediante `INSTREAM`. Una revisión agrega eventos inmutables; nunca modifica registros históricos. Las descargas usan URLs firmadas de 60 segundos y autorización previa por propietario o rol revisor.

El escaneo se ejecuta durante el upload para ofrecer un resultado determinista. Si ClamAV no responde, el documento queda `SCANNING`, no puede descargarse ni revisarse y admite un reintento protegido. Celery beat vence aprobaciones caducadas y recalcula el estado documental de los servicios afectados.

## Consecuencias

- Los documentos no forman parte del repositorio, la base ni rutas públicas.
- MinIO y ClamAV son dependencias de disponibilidad para nuevos uploads, no para navegar estados ya persistidos.
- Un documento infectado se elimina del bucket y conserva solo la evidencia de rechazo.
- Los requisitos legales permanecen configurables y comienzan vacíos para no inventar reglas comerciales o jurisdiccionales.
