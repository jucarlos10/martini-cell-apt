# Conectar Martini Cell al host: pasos para Oscar

Estado 07-10-2026: Oscar integró el [PR #87](https://github.com/jucarlos10/martini-cell-apt/pull/87).
El frontend está publicado en
[Vercel](https://martini-cell-frontend.vercel.app/) y `/api/` se reescribe hacia
el backend Django en Railway. El PR registra una respuesta correcta de
`/api/health/` y un inicio de sesión desde el frontend publicado. Estas son
las pruebas documentadas por Oscar; el repositorio no muestra la configuración
privada de Railway, el volumen de fotografías ni los respaldos.

## Despliegue actual: Vercel y Railway

| Componente | Destino | Comprobación |
| --- | --- | --- |
| Vue | `frontend/` en Vercel | El dominio público carga la interfaz según el PR #87. |
| API Django | Railway | `frontend/vercel.json` reescribe `/api/*` al dominio Railway sin cambiar la URL del navegador. |
| PostgreSQL | Railway | Confirmar migraciones y respaldo/restauración desde el panel. |
| Fotos privadas | Volumen del servicio Django | Confirmar montaje y que `DJANGO_PRIVATE_MEDIA_ROOT` apunte dentro del volumen. |

El frontend mantiene rutas relativas `/api/`, por lo que la reescritura de
Vercel conserva el mismo origen visible para el navegador. El fallback a
`index.html` permite recargar rutas de Vue como `/panel`. El proxy de Vite
`API_PROXY_TARGET` solo se usa en desarrollo local.

### Verificaciones pendientes para Oscar

1. En el servicio Django de Railway, adjuntar y comprobar un volumen
   persistente para las fotos. Railway proporciona
   `RAILWAY_VOLUME_MOUNT_PATH` cuando existe un volumen; fijar
   `DJANGO_PRIVATE_MEDIA_ROOT` a esa ruta o a una subcarpeta. Ejecutar
   `python deploy/check_host.py` **en el contenedor en ejecución**, con las
   variables y usuario del servicio. El comprobador avisa si falta el volumen
   o si las fotos quedan fuera de él. No ejecutarlo como prueba del volumen en
   el paso previo al despliegue: Railway lo monta recién al iniciar el servicio.
2. Confirmar en Railway `DJANGO_DEBUG=false`, clave secreta y base de datos en
   variables privadas, migraciones aplicadas, estáticos del admin y el proceso
   Gunicorn. Configurar el healthcheck del servicio como `/api/health/`.
3. Verificar una orden de ensayo y una foto sin datos personales: cargarla,
   descargarla con sesión, confirmar que no se expone públicamente y repetir
   la consulta después de un nuevo despliegue. Probar respaldo y restauración
   de PostgreSQL y del volumen de fotos.
4. Repetir desde fuera del host estas consultas sin credenciales:

   ```bash
   curl -i https://martini-cell-frontend.vercel.app/api/health/
   curl -i https://martini-cell-frontend.vercel.app/api/auth/me/
   ```

   La primera debe devolver `200` y `{"status":"ok"}`. La segunda debe
   rechazar el acceso sin sesión (`401`), no devolver `index.html`. Revisar
   también `/login` y `/panel` después de recargar. La prueba de inicio de
   sesión se hace desde la interfaz y sin publicar credenciales.

La ruta `/admin/` no está incluida en la reescritura de Vercel; si se usa el
admin, probarlo en el dominio de Railway con sus archivos `/static/` y acceso
restringido. El dataset privado sigue un flujo separado en la
[guía de integración](integracion-dataset-para-oscar.md).

## Alternativa para un VPS con Nginx

Los pasos siguientes documentan una alternativa si se cambia de proveedor.
No son los comandos de instalación ya ejecutados en Vercel/Railway. Este
ejemplo usa un mismo dominio HTTPS para Vue y Django mediante Nginx.

### Componentes y rutas del VPS

| Componente | Ubicación | En el host |
| --- | --- | --- |
| Vue | `frontend/` | Compilar con `npm ci` y `npm run build`; publicar `dist/`. |
| Django API | `backend/` | Instalar `requirements-deploy.txt`; ejecutar Gunicorn con `config.wsgi:application`. |
| Base de datos | PostgreSQL | Crear base y usuario privados; ejecutar migraciones. |
| Fotografías privadas | `DJANGO_PRIVATE_MEDIA_ROOT` | Volumen persistente fuera de la raíz pública, con respaldo. |
| Estáticos de Django admin | `backend/staticfiles/` | Ejecutar `collectstatic` y servir `/static/`. |

El frontend solicita `/api/` en el mismo origen. El proxy de Vite de
`API_PROXY_TARGET` sirve **solo para desarrollo**: no funciona en `dist/`.
El host debe enviar `/api/` y `/admin/` a Django, servir `/static/` desde
`STATIC_ROOT` y devolver `index.html` para rutas de Vue como `/panel`.
[`nginx.martini-cell.example.conf`](../deploy/nginx.martini-cell.example.conf)
muestra una configuración para VPS; contiene nombres y rutas de ejemplo.

### Datos necesarios para esta alternativa

| Dato | Para qué se usa |
| --- | --- |
| Proveedor y tipo de servicio (VPS o plataforma administrada) | Elegir cómo ejecutar Gunicorn y configurar el proxy. |
| Dominio o subdominio y acceso para DNS/TLS | Publicar HTTPS y fijar `DJANGO_ALLOWED_HOSTS`. |
| Acceso a PostgreSQL: host, puerto, base y usuario | Configurar las variables `DB_*`; la contraseña queda en el gestor de secretos del host. |
| Volumen persistente y copias de seguridad | Guardar fotos privadas y respaldarlas junto con PostgreSQL. |
| Forma de administrar procesos y certificados | Mantener Gunicorn activo, renovar TLS y revisar registros. |

No escribir credenciales ni datos de clientes en GitHub. El archivo local
`backend/.env` se ignora por Git. El directorio `private_data/` del dataset
también se ignora; **no se copia al host** solo por publicar la aplicación.

### Secuencia de puesta en marcha

1. En el host, obtener el código desde `main`. Preparar Python 3.12, Node 20 y
   PostgreSQL. Configurar el entorno de Django con una clave secreta nueva,
   `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS=martini.example.com`, `DB_NAME`,
   `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT`. Sustituir el dominio de
   ejemplo por el real. Definir `DJANGO_PRIVATE_MEDIA_ROOT` como ruta absoluta
   de un volumen privado y persistente; no ubicarlo bajo `frontend/dist` ni
   `backend/staticfiles`. Si PostgreSQL es remoto, configurar `DB_SSLMODE` y,
   cuando corresponda, `DB_SSLROOTCERT` según el certificado del proveedor.
   Para un servidor con certificado verificable, preferir `verify-full`.
   Bajo el mismo origen HTTPS, dejar `DJANGO_CORS_ALLOWED_ORIGINS` vacío.
   En producción se usa SMTP en vez de escribir correos en los registros del
   servidor. La aplicación no envía correos actualmente; si se habilita esa
   función, configurar `DJANGO_SMTP_HOST`, `DJANGO_SMTP_PORT`,
   `DJANGO_SMTP_USERNAME`, `DJANGO_SMTP_PASSWORD` y `DJANGO_SMTP_USE_TLS` con
   un servicio real. Sin ellos, el valor local `localhost:25` no garantiza la
   entrega.
2. Instalar dependencias en un entorno virtual y preparar la base y los
   estáticos desde la raíz del repositorio:

   ```bash
   python3.12 -m venv .venv
   .venv/bin/python -m pip install -r backend/requirements-deploy.txt
   .venv/bin/python backend/manage.py migrate --noinput
   .venv/bin/python backend/manage.py collectstatic --noinput
   .venv/bin/python backend/manage.py check --deploy
   .venv/bin/python deploy/check_host.py
   ```

   Ejecutar estos comandos **con el mismo usuario y las mismas variables de
   entorno que Gunicorn**. Crear previamente el volumen privado; el proceso
   debe poder escribir allí. La última comprobación lee PostgreSQL, detecta
   migraciones pendientes, verifica los archivos estáticos y prueba escritura
   temporal en la carpeta privada; no modifica datos de órdenes ni ejecuta
   migraciones. Si falla, corregir los mensajes antes de iniciar el sitio.
   Su persistencia y respaldos se confirman en el panel del proveedor: la
   comprobación local no puede demostrarlo.

3. Compilar Vue desde `frontend/` con `npm ci` y `npm run build`. Configurar
   el proxy del host; si es un VPS con Nginx, obtener el certificado TLS,
   adaptar el ejemplo de `deploy/` y comprobarlo con `nginx -t` antes de recargar.
4. Después de confirmar que el proxy **sobrescribe** cualquier
   `X-Forwarded-Proto` enviado por clientes y que Gunicorn solo recibe tráfico
   del proxy, usar `DJANGO_TRUST_X_FORWARDED_PROTO=true`. Activar
   `DJANGO_SECURE_SSL_REDIRECT=true` al probar HTTPS sin bucles de redirección.
   Iniciar `DJANGO_SECURE_HSTS_SECONDS=3600` solo cuando el sitio funcione de
   forma estable por HTTPS; revisarlo antes de aumentar la duración. Las cookies
   de Django admin y CSRF ya son seguras cuando `DEBUG=false`.
   `check --deploy` puede advertir sobre HSTS para subdominios y precarga.
   Resolverlas solo después de confirmar que **todos** los subdominios usarán
   HTTPS y que se desea incluir el dominio en la lista de precarga.
5. Ejecutar Gunicorn desde `backend/` mediante el administrador de procesos
   del host. En un VPS con Nginx delante, la orden de referencia es:

   ```bash
   gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --access-logfile - --error-logfile -
   ```

   La plataforma administrada puede exigir `0.0.0.0:$PORT` dentro de su red
   privada. Restringir el acceso público al puerto de Gunicorn. Para un VPS
   con systemd, adaptar
   [`martini-cell.service.example`](../deploy/martini-cell.service.example) al
   usuario `martini`, la ruta `/srv/martini-cell` y el archivo `.env` privados.
   Colocar la unidad en `/etc/systemd/system/martini-cell.service`, ejecutar
   `systemctl daemon-reload`, `systemctl enable --now martini-cell` y revisar
   `systemctl status martini-cell` y `journalctl -u martini-cell`. El ejemplo
   de Nginx usa el mismo puerto local `127.0.0.1:8000`.

### Pruebas de conexión del VPS

Desde el host, comprobar Gunicorn con el dominio real en `Host` y el encabezado
HTTPS que inyectará el proxy (sustituir el dominio de ejemplo):

```bash
curl -H 'Host: martini.example.com' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/api/health/
```

Debe devolver `{"status":"ok"}`. Luego desde fuera,
`https://DOMINIO/api/health/` debe devolver el mismo JSON. La ruta verifica
**el proceso y el proxy**, no la conectividad de PostgreSQL.

Comprobar además:

- `https://DOMINIO/login` y `https://DOMINIO/panel` cargan Vue incluso después
  de recargar la página;
- el inicio de sesión usa `/api/auth/login/` y devuelve un resultado esperado;
- una orden de prueba se puede crear y consultar desde la interfaz;
- una foto de ensayo sin datos personales se descarga solo con sesión;
- `/admin/` carga sus recursos de `/static/`, sin exponer el volumen privado;
- una copia de seguridad y su restauración de prueba funcionan para la base y
  para las evidencias privadas.

Ante un `502`, revisar Gunicorn y la ruta de proxy. Si la ruta `/api/health/`
devuelve HTML, el host está enviando la API al fallback de Vue. Si `/panel`
da `404` al recargar, falta el fallback `index.html`. Si hay redirecciones
HTTPS repetidas, revisar el encabezado del proxy y las variables de HTTPS.

La carga de órdenes históricas y del dataset tiene otro flujo; la
[guía de integración del dataset](integracion-dataset-para-oscar.md) explica
la validación privada de casos para HU-17. Publicar el sitio no convierte
candidatos comerciales o de chat en órdenes reales.

Referencias: [volúmenes de Railway](https://docs.railway.com/volumes),
[variables de Railway](https://docs.railway.com/variables/reference),
[reescrituras de Vercel](https://vercel.com/docs/routing/rewrites),
[lista de despliegue de Django](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/),
[ejecución de Gunicorn](https://gunicorn.org/run/) y
[TLS de PostgreSQL](https://www.postgresql.org/docs/current/libpq-ssl.html).
