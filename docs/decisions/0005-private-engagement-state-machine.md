# ADR 0005 — Contratación privada y agenda consistente

## Estado

Aceptada para Fase 9.

## Contexto

Solicitudes, presupuestos y turnos reúnen datos privados y acciones concurrentes de dos actores. Una comprobación sólo en la interfaz permitiría saltos de estado, acceso cruzado o doble reserva. Copiar domicilios sin protección ampliaría el impacto de una filtración de base de datos.

## Decisión

El módulo `engagements` expone rutas separadas para `CLIENT` y `PROVIDER`, deriva ambos actores del token interno y limita cada lectura al cliente propietario o al perfil prestador destinatario. No existe listado público de pedidos.

Las solicitudes y reservas cambian mediante máquinas de estado explícitas. La conversión a reserva bloquea la solicitud y el presupuesto dentro de la transacción. PostgreSQL aplica una exclusión GiST por prestador y rango `tstzrange` para estados `CONFIRMED` e `IN_PROGRESS`, de modo que también resiste aceptaciones simultáneas.

Las modalidades con domicilio validan una dirección propiedad del cliente y la cobertura de la oferta. Al confirmar se guarda sólo la instantánea operativa cifrada con AES-256-GCM; identificadores de Places y coordenadas no forman parte de esa instantánea. Los adjuntos reutilizan el almacenamiento privado y el análisis antivirus.

## Consecuencias

- Una solicitud no puede publicarse ni consultarse conociendo su UUID.
- Los cambios fuera de orden reciben conflicto y no alteran el historial.
- Dos intervalos adyacentes son válidos; dos intervalos confirmados superpuestos para el mismo prestador no lo son.
- La clave de cifrado debe configurarse antes de confirmar servicios con domicilio, respaldarse de forma segura y rotarse mediante un procedimiento futuro versionado.
