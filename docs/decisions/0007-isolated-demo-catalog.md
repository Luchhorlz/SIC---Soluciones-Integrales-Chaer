# ADR 0007 — Catálogo demostrativo aislado

## Estado

Aceptada como preparación de previsualización antes de Fase 11.

## Contexto

Google OAuth y PostgreSQL/PostGIS pueden no estar disponibles durante la revisión visual. SIC necesita que cualquier categoría, búsqueda y servicio muestre resultados útiles sin confundir datos ficticios con profesionales reales ni dejar residuos difíciles de retirar.

## Decisión

- Generar exactamente tres identidades profesionales distintas por cada uno de los 1.392 servicios canónicos: 4.176 perfiles y ofertas.
- Guardar la configuración versionada en `seeds/demo-data.json` y exigir por prueba que su copia web sea idéntica.
- Marcar usuarios y perfiles persistidos con `is_demo`; usar identificadores estables, correos `.invalid` y contenido explícitamente ficticio.
- Permitir el atajo de documentación y suscripción únicamente con `DEMO_MODE=true`, sin eludir el evaluador central de visibilidad.
- Ofrecer tres cuentas temporales de rol fijo mediante Credentials de Auth.js, activas sólo fuera de producción.
- Generar el mismo catálogo de forma determinista en Next.js cuando la API no devuelve resultados, manteniendo todas las llamadas del navegador dentro del BFF.
- Proveer un comando idempotente de carga y otro de eliminación completa de relaciones demo.
- Rechazar cualquier administración del dataset con `APP_ENV=production`.

## Consecuencias

La previsualización sigue siendo navegable sin dependencias locales y cada servicio conserva tres resultados verificables. Los datos demo no se mezclan silenciosamente con producción y pueden retirarse en bloque. Hay dos representaciones del archivo de configuración por restricciones del empaquetado web, por lo que CI comprueba su igualdad exacta.
