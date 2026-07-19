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

## Identidad Google

Auth.js maneja el flujo OAuth del lado servidor con sesión JWT. Solo se acepta el proveedor Google y un perfil con correo verificado. Las credenciales y `AUTH_SECRET` permanecen fuera de Git. Los redirect URI autorizados previstos son `http://localhost:3000/api/auth/callback/google` para desarrollo y `https://sic.thecottonclub.com.ar/api/auth/callback/google` para producción.

La primera autenticación sincroniza el perfil mediante un JWT interno de 60 segundos con audiencia `sic-api`, propósito `identity-sync` y sujeto ligado al identificador inmutable de Google. FastAPI rechaza si el cuerpo no coincide con ese sujeto. Después de la sincronización, la sesión usa exclusivamente el UUID interno de SIC para operaciones del usuario. `INTERNAL_API_JWT_SECRET` debe ser distinto de `AUTH_SECRET` y tener al menos 32 caracteres.

Cada sesión recibe además un identificador aleatorio propio, incluido en los tokens internos para correlación y auditoría sin registrar la cookie ni el token de sesión.

## Direcciones privadas

Las direcciones pertenecen siempre al UUID interno autenticado y los endpoints se publican únicamente bajo `/v1/me/addresses`; el cliente no puede consultar ni modificar recursos de otro usuario. El punto geográfico se almacena como `geography(POINT, 4326)` para futuras consultas de cobertura, pero el domicilio exacto no forma parte de perfiles públicos, resultados de búsqueda ni logs de aplicación.

La interfaz no permite persistir coordenadas escritas o simuladas: exige una selección verificable de Google Places antes de enviar `place_id`, latitud y longitud. Sin credencial y sesión reales, el formulario permanece deshabilitado de forma explícita.

Autocomplete y Place Details se ejecutan en el BFF, requieren sesión y tienen una cuota local defensiva. La respuesta normalizada se firma por diez minutos con audiencia propia y queda ligada al UUID y al identificador de sesión; la acción de guardado usa exclusivamente esos datos firmados. La clave web-service no llega al JavaScript ni se registra junto con las consultas.

El mapa estático también se solicita y firma del lado servidor. El navegador recibe únicamente una imagen privada sin caché y puede corregir el pin hasta 500 metros del punto original; el ancla inmutable viaja dentro del comprobante firmado para impedir desplazamientos acumulativos.

La clave debe restringirse por API a Places API (New) y Maps Static API y, al operar desde el servidor propio, también por IP de salida. El secreto de firma de URLs es independiente y nunca se expone al cliente.

## Administración del catálogo

Los endpoints de escritura y la pantalla `/admin/catalogo` aplican deny by default y exigen el rol persistido `ADMIN`; el onboarding no puede autoconcederlo. La desactivación reemplaza al borrado para conservar referencias históricas. La API valida códigos, slugs, relaciones y al menos una modalidad de precio (`precio fijo` o `presupuesto`) para cada servicio.

## Perfil y oferta del prestador

La API exige rol `PROVIDER` y usa exclusivamente el UUID del token para consultar o modificar perfil, portfolio, servicios, cobertura y agenda; no acepta un `provider_id` enviado por el navegador. Los centros geográficos se copian desde una dirección validada perteneciente al mismo usuario y nunca se exponen como domicilio exacto público.

`ProviderVisibilityService` aplica deny by default. Un perfil incompleto, pausado, pendiente de revisión, sin suscripción, con documentación pendiente, sin modalidad o sin cobertura requerida devuelve un diagnóstico interno y no es publicable. La Fase 5 no contiene rutas públicas de prestadores.

## Documentos profesionales privados

Las cargas atraviesan el BFF autenticado y la API deriva el prestador del UUID del token. Se admiten únicamente PDF, PNG y JPEG cuyo contenido coincide con la firma declarada, con límite configurable de 10 MB y hash SHA-256 único por propietario. El objeto usa una clave UUID bajo `documents/{user_id}/`, permanece en bucket privado y no se registra su contenido ni el domicilio en logs.

ClamAV analiza el contenido mediante `INSTREAM`. Un resultado infectado elimina el objeto y rechaza el documento; si el scanner no está disponible se conserva el estado `SCANNING` sin permitir descarga ni revisión y un revisor puede reintentar. Solo archivos `CLEAN` reciben URLs S3 firmadas de corta duración. Prestadores descargan únicamente sus archivos; `ADMIN` y `DOCUMENT_REVIEWER` acceden a la cola y cada decisión genera auditoría inmutable.

## Host Windows

La API de control escucha únicamente en loopback, requiere un token local protegido y no expone secretos en la UI ni logs. Online/Offline controla procesos de forma explícita. Las credenciales del Named Tunnel quedan fuera del repositorio y con permisos restrictivos.

Este documento es un modelo técnico inicial, no una afirmación legal definitiva.
