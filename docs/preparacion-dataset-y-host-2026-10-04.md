# Preparación de datos y conexión al host

Fecha de revisión: 04-10-2026.

## Estado verificable

| Fuente | Encontrado | Uso actual |
| --- | ---: | --- |
| Movimientos comerciales con motivo técnico y modelo | 160 filas candidatas | Revisión manual; no equivalen a 160 órdenes. |
| Fotografías del taller | 14 archivos, 13 únicos | Cinco muestran una escena técnica, pero ninguna tiene una orden comprobada. |
| Audios accesibles para este trabajo | 0 | No hay transcripciones incorporadas. |
| Casos reales validados para estimación de tiempo | 0 | No entrenar ni importar como dataset final. |

La planilla privada de preparación conserva para cada movimiento la hoja, celda y fecha del bloque comercial. Esa fecha **no acredita** la recepción ni la entrega del equipo. Los diez códigos MC-001 a MC-010 de la plantilla anterior siguen sin datos de caso: son espacios reservados. La planilla de inventario describe repuestos; tampoco identifica reparaciones individuales.

Las fotos incluyen herramientas, equipos abiertos y contexto del local. Hay una duplicación exacta. Algunas muestran rostros, etiquetas, identificadores o información en pantalla. Antes de usar una foto de reparación se necesita asociarla a una orden real y preparar una copia anonimizada; el archivo original no se coloca en Git ni se expone como recurso público.

## De candidato a caso confirmado

1. Comprobar con el registro de Martini Cell si un movimiento corresponde a un servicio único, un pago parcial o una venta. Conservar el ID provisional y la celda de origen; no convertirlo en código de orden.
2. Asociar la orden real y registrar por separado la falla informada, el diagnóstico técnico, el trabajo realizado y el resultado. Una descripción de cobro como “pantalla” no demuestra por sí misma ni el diagnóstico ni la reparación.
3. Vincular audios y fotos por ID de caso solo cuando exista una relación comprobada. Guardar transcripción literal revisada, fuente y cualquier incertidumbre; no deducir tiempos ni resultados de una imagen.
4. Registrar minutos de trabajo técnico y minutos de espera por separado. Confirmar inicio y fin de la intervención y la finalización del servicio.
5. Quitar identificadores personales del texto y de las copias de imágenes, revisar el resultado y registrar la validación de Marcos. El uso para ML requiere un caso real, finalizado, consistente y anonimizado. Para HU-17, el conjunto de entrenamiento excluye fotos y códigos de seguimiento aunque puedan conservarse como evidencias privadas del servicio.

La planilla de preparación mantiene `Apto ML = No` mientras faltan datos. Su cálculo requiere una orden identificada, falla, diagnóstico, trabajo, resultado, tiempo técnico positivo, tiempo de espera numérico, anonimización y estado `Validado`. Pasar el filtro de la planilla no sustituye la revisión de procedencia y finalización descrita en [HU-17](evaluacion-hu17-estimacion-tiempo.md).

## Correspondencia con el sistema

| Dato confirmado | Destino del MVP | Condición |
| --- | --- | --- |
| Cliente y equipo | `Client` y `Equipment` | Registrar en los flujos internos, con permisos. |
| Orden, falla y observaciones | `ServiceOrder` | Requiere cliente y equipo válidos; el sistema genera el código de seguimiento. |
| Diagnóstico, reparación y resultado | `OrderTechnicalReport` | Confirmar con un técnico. |
| Etapas y tiempos | `OrderStatusHistory` y cálculo de HU-11 | Necesita historial real; una fecha contable no lo reemplaza. |
| Fotos vinculadas | `OrderEvidence` | Subir copia revisada al almacenamiento privado; acceso autenticado. |

`ServiceOrder.received_at` se asigna automáticamente al crear una orden. Por ello, el registro comercial histórico no puede cargarse como una orden pasada mediante el formulario normal sin perder el significado de su fecha. Cualquier importación histórica requiere un proceso específico, revisión de duplicados y una decisión sobre fechas. No ejecutar cargas automáticas desde la planilla de candidatos.

## Preparación técnica del host para Oscar

El repositorio ya tiene Django, PostgreSQL, frontend Vue/Vite y rutas `/api/`. Esta revisión incorpora `STATIC_ROOT`, variables para los orígenes permitidos y una ruta configurable para fotos privadas. El destino del host, dominio, volumen persistente y método de despliegue aún no están definidos en el repositorio.

1. Definir el dominio y cómo el servidor enviará `/api/` al backend. El frontend usa rutas `/api/` relativas; servirlo bajo el mismo origen simplifica la conexión. Configurar la ruta de retorno de Vue para las páginas internas.
2. Configurar PostgreSQL y secretos fuera de Git: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` y un `DJANGO_SECRET_KEY` propio del host. Fijar `DJANGO_DEBUG=false` y `DJANGO_ALLOWED_HOSTS` a los nombres reales del sitio. Usar `DJANGO_CORS_ALLOWED_ORIGINS` y `DJANGO_CSRF_TRUSTED_ORIGINS` solo con los orígenes HTTPS que correspondan si el frontend está separado.
3. Dar a `DJANGO_PRIVATE_MEDIA_ROOT` una ruta absoluta en almacenamiento privado y persistente, con respaldo. No servir ese directorio directamente desde el servidor web. Las descargas existentes pasan por la API autenticada.
4. Instalar las dependencias, ejecutar `python manage.py migrate`, `python manage.py collectstatic --noinput` y `python manage.py check --deploy` con la configuración real. Servir `STATIC_ROOT` para los recursos de Django; usar un servidor WSGI/ASGI de producción, no `runserver`.
5. Ejecutar `npm ci` y `npm run build` en `frontend/`, servir `dist/` como aplicación estática y comprobar las rutas de Vue. Probar inicio de sesión, creación/consulta de orden, una foto anonimizada de ensayo y su descarga con sesión. Verificar copias de seguridad de PostgreSQL y de las evidencias privadas.

Esto es preparación y criterios de prueba. No hay URL, credenciales ni conexión al host configuradas todavía, y las pruebas de CI no sustituyen una prueba sobre el destino real.
