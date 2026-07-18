# ADR 0001: Monolito modular con BFF

- Estado: aceptada
- Fecha: 2026-07-18

## Contexto

SIC combina SEO público, autenticación web, reglas transaccionales, geolocalización, documentación privada, suscripciones y tareas en segundo plano. El MVP también debe poder operarse desde un host Windows propio.

## Decisión

Usar Next.js App Router como web/BFF, FastAPI como API privada y un monolito modular para el dominio. PostgreSQL/PostGIS conserva datos transaccionales y geográficos; Redis atiende caché/colas; Celery ejecuta trabajos; S3 compatible almacena archivos. Los componentes se despliegan juntos mediante Compose y son supervisados por el host Windows.

## Consecuencias

- Una sola frontera de dominio y transacciones claras.
- Menor carga operativa que microservicios.
- OpenAPI evita duplicar DTOs.
- El BFF reduce la exposición de la API y centraliza sesión.
- Los módulos necesitan límites explícitos para evitar un monolito desordenado.
- El empaquetado `.exe` supervisa la suite; no implica incrustar todos los servicios en un único proceso.

## Alternativas descartadas

- Microservicios: complejidad operativa prematura.
- Frontend hablando directamente con FastAPI: expone más superficie y duplica manejo de sesión.
- Base sin PostGIS: insuficiente para cobertura y distancias confiables.
- Cloudflare Quick Tunnel: no brinda el hostname estable requerido.
