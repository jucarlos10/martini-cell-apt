# TEC-02 — Integración del frontend Vue con la API Django

## 1. Objetivo

Completar y verificar la integración existente entre el frontend Vue y el backend Django REST de Martini Cell, utilizando los registros de PostgreSQL en lugar de datos simulados.

TEC-02 no reconstruye los módulos previamente integrados. Se enfoca en completar las pantallas que todavía utilizaban datos de demostración, configurar la conexión local y registrar la evidencia de funcionamiento.

## 2. Integración existente

Antes de los cambios de TEC-02, el proyecto ya contaba con:

- Inicio de sesión mediante JWT.
- Consulta del usuario autenticado y su rol.
- Renovación del token de acceso mediante refresh token.
- Cierre de sesión lógico mediante eliminación de los tokens almacenados en el navegador.
- Registro, búsqueda y actualización de clientes.
- Registro y consulta de equipos.
- Creación y consulta de órdenes de servicio.
- Gestión de estados, informes técnicos y garantías desde el detalle de una orden.
- Consulta pública del estado de una orden mediante su código de seguimiento.

Estas funcionalidades se conservaron. TEC-02 no reemplaza su implementación.

## 3. Cambios realizados

### 3.1. Listado general de garantías

La pantalla `/garantias` utilizaba anteriormente los registros de demostración de `mockStore.js`.

Se incorporó un endpoint de solo lectura:

```http
GET /api/orders/warranties/
```

Este endpoint:

- Consulta las garantías registradas en PostgreSQL, independientemente de la orden a la que pertenezcan.
- Reutiliza el modelo y el serializador de garantías existentes.
- Incluye el código de seguimiento de cada orden.
- Devuelve el estado de vigencia, las fechas, las condiciones, el repuesto y el proveedor histórico cuando corresponde.
- Permite consultar a los roles `ADMIN` y `TECH`.
- Rechaza el acceso anónimo y el del rol `HELPER`.
- No crea ni modifica garantías o registros de su historial.

Se actualizó `frontend/src/views/WarrantiesView.vue` para consultar este endpoint mediante `authenticatedFetch`.

La pantalla ahora incluye estados de carga, mensajes de error, opción de reintentar, botón de actualización y enlaces al detalle de cada orden.

La gestión de garantías dentro de `OrderDetailView.vue` permanece sin cambios.

### 3.2. Panel principal

Se actualizó `frontend/src/views/DashboardView.vue` para utilizar:

```http
GET /api/orders/
```

El panel calcula sus indicadores a partir de las órdenes devueltas por Django y presenta las cinco órdenes actualizadas más recientemente.

Se eliminó la dependencia de `mockStore.js` en esta pantalla y el aviso de datos de demostración.

La columna «Registrado por» utiliza el campo `created_by_username` que entrega la API.

También se incorporaron estados de carga, error, reintento y ausencia de órdenes.

### 3.3. Configuración de Vite

Se actualizó `frontend/vite.config.js` para permitir configurar el destino del proxy mediante la variable de entorno:

```text
API_PROXY_TARGET
```

Cuando no se define, conserva el valor local predeterminado:

```text
http://127.0.0.1:8000
```

Las solicitudes del frontend a rutas `/api/` se redirigen al backend mediante el proxy del servidor de desarrollo de Vite.

Esta configuración corresponde al entorno de desarrollo local. No configura por sí sola el proxy de un despliegue de producción.

## 4. Ejecución local

### 4.1. Backend

Abrir una terminal PowerShell en la carpeta `backend` y activar el entorno virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Con PostgreSQL disponible y la configuración local de Django preparada, iniciar el servidor:

```powershell
python manage.py runserver 127.0.0.1:8000
```

### 4.2. Frontend

Abrir una segunda terminal en la carpeta `frontend` y ejecutar:

```powershell
npm run dev
```

Abrir en el navegador la dirección local indicada por Vite, normalmente:

```text
http://localhost:5173/
```

Si el puerto 5173 está ocupado, Vite puede indicar otro puerto, por ejemplo 5174.

### 4.3. Configuración opcional del proxy

Para utilizar una dirección diferente del backend, se puede crear un archivo local `frontend/.env` con una variable como:

```dotenv
API_PROXY_TARGET=http://127.0.0.1:8000
```

El valor anterior corresponde a la configuración local predeterminada; no es obligatorio crear el archivo para trabajar con ella.

El archivo `.env` está excluido del repositorio mediante `.gitignore`. No deben incorporarse contraseñas, claves ni otros secretos a Git.

Después de cambiar la configuración de entorno, reiniciar el servidor de desarrollo de Vite.

## 5. Evidencia de verificación

### 5.1. Endpoint de garantías

Se comprobó que Django reconoce la nueva ruta:

```text
/api/orders/warranties/
```

Se incorporó `backend/orders/test_warranty_summary.py` con nueve pruebas automatizadas.

Resultado de su ejecución individual:

```text
Found 9 test(s).
System check identified no issues (0 silenced).

Ran 9 tests in 0.248s

OK
Preserving test database for alias 'default' ('test_martini_cell')...
```

Las pruebas verifican los datos devueltos, los permisos, el carácter de solo lectura, la conservación del proveedor histórico y la ausencia de modificaciones durante la consulta.

### 5.2. Compilación del frontend

Después de actualizar Garantías, Panel y la configuración de Vite, se ejecutó:

```powershell
npm --prefix ..\frontend run build
```

La última compilación terminó correctamente:

```text
vite v5.4.8 building for production...
✓ 44 modules transformed.
✓ built in 1.21s
```

### 5.3. Comprobación visual

Se verificó en el navegador que:

- `/garantias` muestra las garantías registradas en el backend, en lugar de las dos filas anteriores de demostración.
- La pantalla presenta una garantía del servicio y una garantía de repuesto asociadas a la misma orden de desarrollo.
- `/panel` muestra cuatro órdenes registradas en la base de desarrollo, sus códigos de seguimiento, equipos y estados.
- El indicador de órdenes abiertas refleja esas cuatro órdenes de desarrollo.
- Desapareció el aviso de datos de demostración del panel.

Estos registros corresponden al entorno de desarrollo y prueba. No representan datos históricos operacionales reales del negocio.

## 6. Resultado de la suite completa del backend

TEC-01 finalizó previamente con 182 pruebas exitosas.

TEC-02 incorporó nueve pruebas adicionales para la consulta general de garantías.

Se ejecutó la suite completa desde `backend`:

```powershell
python manage.py test --keepdb --verbosity 2
```

Resultado confirmado:

```text
Found 191 test(s).
Using existing test database for alias 'default' ('test_martini_cell')...
System check identified no issues (0 silenced).

----------------------------------------------------------------------
Ran 191 tests in 44.051s

OK
Preserving test database for alias 'default' ('test_martini_cell')...
```

| Indicador | Resultado |
|---|---:|
| Pruebas anteriores | 182 |
| Pruebas incorporadas en TEC-02 | 9 |
| Total de pruebas ejecutadas | 191 |
| Errores o fallos reportados | 0 |
| Resultado final | `OK` |

La base de pruebas `test_martini_cell` se mantuvo separada de la base de desarrollo `martini_cell`.

## 7. Alcance del cierre de sesión

El frontend implementa cierre de sesión lógico eliminando los tokens JWT y la información del usuario almacenados en `sessionStorage`.

Esto no equivale a revocar un token vigente en el servidor. No se declara implementada una lista de bloqueo de JWT ni un endpoint de revocación.

## 8. Verificaciones antes del cierre de TEC-02

### Comprobaciones realizadas

- El nuevo endpoint de garantías superó sus nueve pruebas automatizadas.
- La suite completa del backend finalizó con 191 pruebas exitosas.
- El frontend compiló correctamente después de los cambios.
- Se comprobó visualmente que Panel y Garantías presentan registros del backend.
- Se conservaron las funcionalidades existentes de autenticación, clientes, equipos, órdenes y garantías por orden.

### Comprobaciones pendientes antes de fusionar la PR

- Revisar los archivos modificados mediante Git.
- Confirmar que no se incluyen secretos ni archivos locales de entorno.
- Verificar que `.gitignore` no excluya `README.md`.
- Incorporar en la PR la evidencia de las pruebas y de la compilación.
- Dejar constancia del recorrido de integración entre acceso, cliente, equipo y orden. La conexión de estos módulos ya estaba implementada; no se deben duplicar registros de desarrollo únicamente para repetir la comprobación.

## 9. Resultado

TEC-02 conserva la integración existente y sustituye los datos simulados de las pantallas generales de Garantías y Panel por consultas al backend Django.

Se verificaron nueve pruebas nuevas, una suite completa de 191 pruebas exitosas, la compilación del frontend y el funcionamiento visual de ambas pantallas con registros del entorno de desarrollo.

Los cambios quedan preparados para la revisión final de Git y la creación de la Pull Request.