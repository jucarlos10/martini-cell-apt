# Conectar Martini Cell al host: pasos para Oscar

Estado: el código está preparado para probar un despliegue, pero el repositorio
no contiene un proveedor, servidor, dominio ni credenciales. Este ejemplo usa
**un mismo dominio HTTPS** para Vue y Django. Si el host es un servicio
administrado, conservar el esquema de rutas y adaptar los comandos al panel del
proveedor.

## Qué hay en el proyecto

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

## Datos que Oscar debe obtener del host

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

## Secuencia de puesta en marcha

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
2. Instalar dependencias y preparar la base y los estáticos:

   ```bash
   python -m pip install -r backend/requirements-deploy.txt
   cd backend
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py check --deploy
   ```

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
5. Ejecutar Gunicorn desde `backend/` mediante el administrador de procesos
   del host. En un VPS con Nginx delante, la orden de referencia es:

   ```bash
   gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --access-logfile - --error-logfile -
   ```

   La plataforma administrada puede exigir `0.0.0.0:$PORT` dentro de su red
   privada. Restringir el acceso público al puerto de Gunicorn.

## Pruebas de conexión

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

Referencias: [lista de despliegue de Django](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/),
[ejecución de Gunicorn](https://gunicorn.org/run/) y
[TLS de PostgreSQL](https://www.postgresql.org/docs/current/libpq-ssl.html).
