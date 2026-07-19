# Despliegue

## Desarrollo

Docker Compose ejecuta web, API, worker/beat, PostGIS, Redis, MinIO, ClamAV y Mailpit. ClamAV mantiene sus firmas en un volumen y debe estar saludable antes de aceptar uploads; su puerto no se publica al host. MinIO expone API y consola únicamente en loopback durante desarrollo y usa credenciales externas en producción.

ClamAV requiere memoria suficiente para cargar las firmas; el host productivo debe reservar recursos y verificar el healthcheck antes de poner la suite Online. `S3_PRESIGN_ENDPOINT` debe apuntar a una URL alcanzable por el navegador sin convertir el bucket en público.

Mailpit recibe correo transaccional en desarrollo mediante `SMTP_HOST=mailpit`, `SMTP_PORT=1025` y `EMAIL_FROM`. En staging o producción se reemplaza por un proveedor SMTP aprobado y TLS configurable; el worker procesa la bandeja cada minuto y registra únicamente el tipo de error, sin contenido ni credenciales.

## Staging

Dominio, base, bucket y credenciales sandbox separados. Misma topología que producción y datos exclusivamente ficticios.

Mercado Pago sandbox requiere `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_WEBHOOK_SECRET` y `MERCADOPAGO_SUCCESS_URL`. La URL HTTPS de prueba debe apuntar a `https://sic.thecottonclub.com.ar/api/webhooks/mercado-pago` sólo cuando exista autorización para publicar el túnel. El tópico mínimo es `subscription_preapproval`; para cuotas recurrentes se agrega `subscription_authorized_payment`. Las credenciales de prueba y productivas nunca se mezclan.

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
