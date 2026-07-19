# ADR 0004 — Proyección pública de búsqueda

## Estado

Aceptada para Fase 8.

## Contexto

La búsqueda combina catálogo, ofertas, perfil, cuenta, modalidad, cobertura PostGIS, disponibilidad, documentación y suscripción. Resolver esa lectura mediante llamadas por registro mantendría los límites de escritura, pero produciría una cantidad de consultas incompatible con una página de resultados.

## Decisión

El módulo `search` posee una proyección de lectura sin escritura que une los datos mínimos necesarios para obtener candidatos. Esa proyección no decide visibilidad: cada candidato pasa obligatoriamente por `ProviderVisibilityService`, usando lectores de documentación y suscripción de sus módulos propietarios.

`ST_DWithin` elimina coberturas que no contienen el punto del cliente antes de calcular `ST_Distance`. La API limita el radio de búsqueda a 100 km. La distancia pública se redondea a 100 metros y los puntos del mapa a dos decimales; los perfiles públicos nunca incluyen coordenadas ni direcciones.

## Consecuencias

- Lista y mapa consumen el mismo conjunto de resultados.
- Un perfil invisible responde `404`, incluso conociendo su slug.
- La proyección puede optimizarse sin trasladar reglas de negocio a SQL.
- Las escrituras siguen pasando por los módulos propietarios.
