# Despliegue

## Desarrollo

Docker Compose ejecutará web, API, worker, PostGIS, Redis, MinIO y Mailpit. La Fase 1 definirá versiones y comandos reproducibles.

## Staging

Dominio, base, bucket y credenciales sandbox separados. Misma topología que producción y datos exclusivamente ficticios.

## Producción prevista

- Equipo Windows administrado por el propietario.
- Suite local supervisada mediante `SIC Server.exe`/Systray.
- Reverse proxy y contenedores con reinicio controlado.
- Cloudflare Named Tunnel para `sic.thecottonclub.com.ar`; API y bases no se publican directamente.
- Backups diarios cifrados con copia externa y restauración ensayada.
- Migraciones, rollback y publicación requieren aprobación manual.

## Online/Offline

Online comprueba salud local, inicia el túnel y valida el hostname con una solicitud HTTP real. Offline detiene el túnel de forma segura. El estado debe distinguir `Offline`, `Iniciando`, `Online`, `Degradado` y `Error`, mostrando qué componente falla.

No se ejecutó ni autorizó todavía ningún cambio de DNS, Cloudflare o producción.
