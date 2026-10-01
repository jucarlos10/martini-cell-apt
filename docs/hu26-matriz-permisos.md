HU-26 — Matriz de permisos por perfil
1. Estado del documento
Estado: propuesta técnica implementada y validada técnicamente. El responsable del proyecto comunicó el 30-09-2026 la conformidad general de Marcos para avanzar sin otra ronda formal; quedan comprobaciones puntuales de datos por perfil y el recorrido funcional antes de cerrar HU-26.
Esta matriz define el comportamiento esperado para los perfiles `ADMIN`, `TECH` y `HELPER` en la plataforma Martini Cell. La autorización debe aplicarse en el backend. Ocultar botones o secciones en Vue es solo una medida de apoyo visual y no reemplaza la validación de permisos de la API.
La definición considera la administración de usuarios existente, las reglas transversales de TEC-03, el flujo de garantías de HU-23 y la futura trazabilidad de cambios sensibles de HU-27.
2. Perfiles
`ADMIN`: administración general del sistema. Puede ejecutar acciones administrativas y destructivas cuando el dominio lo permite.
`TECH`: operación técnica. Puede gestionar información técnica y operacional necesaria para realizar reparaciones, pero no administra usuarios ni toma decisiones administrativas reservadas.
`HELPER`: recepción y apoyo operacional. Puede consultar y registrar información necesaria para ingresar clientes, equipos y órdenes, pero no modificar registros existentes ni acceder a información financiera o administrativa restringida.
3. Matriz general de permisos
Recurso o acción	ADMIN	TECH	HELPER	Observación
Acceder a módulos internos con sesión	Sí	Sí	Sí	Los usuarios sin sesión no pueden ejecutar acciones internas.
Administrar usuarios y roles	Sí	No	No	Gestión reservada a `ADMIN`.
Consultar clientes	Sí	Sí	Sí	Incluye datos necesarios para recepción.
Crear clientes	Sí	Sí	Sí	`HELPER` puede registrar clientes nuevos.
Modificar clientes existentes	Sí	Sí	No	La API debe devolver acceso denegado a `HELPER`.
Eliminar clientes	Sí	No	No	Además se mantienen las restricciones de integridad e historial.
Ver historial de modificaciones de clientes	Sí	Sí	No	Se considera historial interno.
Consultar equipos	Sí	Sí	Sí	Disponible para recepción y operación.
Crear equipos	Sí	Sí	Sí	`HELPER` puede registrar un equipo nuevo para un cliente.
Modificar equipos existentes	Sí	Sí	No	`HELPER` queda en modo consulta/registro.
Eliminar equipos	Sí	No	No	Sujeto a restricciones por órdenes relacionadas.
Ver hoja de vida de un equipo	Sí	Sí	Sí	Permite revisar sus órdenes anteriores.
Consultar órdenes de servicio	Sí	Sí	Sí	Información operacional visible para perfiles autenticados.
Crear órdenes de servicio	Sí	Sí	Sí	`HELPER` puede realizar la recepción.
Modificar datos generales de una orden	Sí	Sí	No	Alcance sujeto a HU-27 para campos sensibles y trazabilidad.
Eliminar órdenes	No	No	No	No existe operación de eliminación general de órdenes en el flujo actual.
Cambiar estado de una orden	Sí	Sí	No	La API valida el rol.
Consultar historial de estados	Sí	Sí	Sí	Trazabilidad operacional de la orden.
Consultar tiempos de la orden	Sí	Sí	Sí	Información operacional.
Consultar evidencias de una orden	Sí	Sí	Sí	Acceso interno autenticado.
Subir evidencias a una orden	Sí	Sí	Sí	Se mantiene como apoyo al flujo de recepción y reparación.
Descargar evidencias de una orden	Sí	Sí	Sí	Acceso interno autenticado.
Consultar informe técnico	Sí	Sí	Sí	`HELPER` puede leer el resultado técnico.
Crear o modificar informe técnico	Sí	Sí	No	Acción técnica restringida.
Ver historial de revisiones del informe técnico	Sí	Sí	No	Se considera historial técnico interno.
Consultar catálogo de repuestos	Sí	Sí	Sí	`HELPER` accede en modo consulta.
Ver costo unitario/subtotal de repuestos	Sí	Sí	No	El backend omite estos importes para `HELPER`.
Crear o modificar repuestos/proveedores	Sí	Sí	No	Gestión de inventario para `ADMIN` y `TECH`.
Eliminar repuestos/proveedores	Sí	No	No	Eliminación reservada a `ADMIN` y sujeta a integridad histórica.
Registrar uso de repuesto en una orden	Sí	Sí	No	Acción técnica.
Corregir uso de repuesto	Sí	Sí	No	Corrección trazable.
Anular uso de repuesto	Sí	Sí	No	Anulación trazable; no elimina el registro histórico.
Ver resumen financiero/costos de una orden	Sí	Sí	No	Información financiera restringida.
Modificar datos financieros de una orden	Sí	No	No	Edición reservada a `ADMIN`.
Consultar garantías	Sí	Sí	No	`HELPER` no accede al módulo de garantías.
Crear/modificar antecedentes de garantía	Sí	Sí	No	Gestión técnica/administrativa.
Preparar propuesta técnica de solicitud de garantía	No como flujo normal	Sí	No	`TECH` propone y puede corregir/re-enviar.
Autorizar/rechazar resolución final de garantía	Sí	No	No	La decisión final corresponde exclusivamente a `ADMIN`.
Devolver propuesta de garantía para corrección	Sí	No	No	`ADMIN` puede solicitar correcciones al técnico.
Resolver directamente solicitud de garantía	Sí	No	No	Permitido a `ADMIN` desde estados válidos del flujo.
Consultar indicadores operacionales	Sí	Sí	No	Módulo restringido a perfiles técnicos/administrativos.
Consultar índice de viabilidad	Sí	Sí	No	Resultado interno de apoyo a la decisión técnica.
Gestionar datos del índice de viabilidad	Sí	Sí	No	No disponible para `HELPER`.
Consulta pública por código de seguimiento	Sí, sin sesión	Sí, sin sesión	Sí, sin sesión	La respuesta pública es mínima y no expone datos personales, financieros ni internos.
4. Datos personales y financieros
4.1. Datos de clientes
La propuesta actual permite que `ADMIN`, `TECH` y `HELPER` consulten los datos de identificación y contacto necesarios para el proceso de recepción, incluyendo RUT, nombre, teléfono y correo cuando exista.
Esta decisión se justifica funcionalmente porque `HELPER` puede registrar clientes, equipos y órdenes. La conformidad general comunicada permite trabajar con esta matriz como línea de base; el alcance exacto de RUT y contacto para recepción requiere una comprobación puntual, sin ampliar acceso mientras tanto.
El historial interno de modificaciones de clientes no se muestra a `HELPER`.
4.2. Información financiera
`HELPER` no debe recibir costos unitarios, subtotales de repuestos, costos de la orden, precios ni márgenes.
`TECH` puede consultar la información financiera de la orden cuando el flujo lo requiera, pero no modificarla.
La modificación de los datos financieros queda reservada a `ADMIN`.
4.3. Consulta pública
La consulta pública por código de seguimiento no requiere una sesión interna, pero su respuesta debe limitarse a los datos necesarios para informar el avance de la reparación.
No debe exponer RUT, teléfono, correo, costos, márgenes, diagnósticos internos, historial administrativo ni información de usuarios del sistema.
5. Reglas específicas de garantías
El flujo de solicitudes de garantía mantiene una separación entre propuesta técnica y decisión administrativa:
`TECH` prepara y envía una propuesta técnica.
`ADMIN` puede autorizarla, rechazarla o devolverla para corrección.
`TECH` puede corregir y reenviar una propuesta devuelta.
`ADMIN` también puede resolver directamente una solicitud desde los estados admitidos por el flujo.
La resolución final solo puede ser tomada por `ADMIN`.
`HELPER` no accede a la gestión de garantías.
Estas reglas no deben relajarse por cambios de interfaz. La API debe impedir que un perfil no autorizado invoque directamente las acciones administrativas.
6. Relación con HU-27
HU-26 determina quién puede ejecutar una modificación sobre una orden.
HU-27 debe determinar con mayor detalle:
qué campos de la orden pueden modificarse después de su creación;
qué campos pasan a ser inmutables según el estado;
qué cambios requieren motivo;
cómo registrar valor anterior, valor nuevo, fecha y responsable;
cómo conservar la trazabilidad de los cambios sensibles.
Por este motivo, autorizar a `ADMIN` o `TECH` para modificar una orden en HU-26 no significa que todos los campos deban permanecer editables en cualquier estado.
7. Aplicación técnica
La seguridad debe cumplirse en dos capas:
Backend
Requiere autenticación para los endpoints internos.
Valida el rol antes de ejecutar cada acción.
Devuelve acceso denegado cuando el perfil no está autorizado.
Filtra datos sensibles cuando el perfil puede consultar un recurso pero no debe recibir todos sus campos.
Frontend
Oculta o deshabilita acciones que el perfil no puede ejecutar.
Evita realizar solicitudes conocidas como no autorizadas.
No se considera una barrera de seguridad por sí sola.
Una llamada directa a la API debe obtener el mismo resultado de autorización que la interfaz.
8. Cambios implementados en la rama HU-26
En la rama `feature/hu26-autorizacion-perfiles` se implementó:
permiso reutilizable para operaciones de registros operacionales;
`HELPER` puede consultar y crear clientes, equipos y órdenes;
`HELPER` no puede modificar esos registros existentes;
historial de modificaciones de clientes restringido a `ADMIN` y `TECH`;
historial de revisiones del informe técnico restringido a `ADMIN` y `TECH`;
frontend adaptado para no mostrar ni solicitar esos historiales a `HELPER`;
acceso de `HELPER` al catálogo de repuestos en modo consulta;
costos y acciones de gestión de repuestos continúan ocultos para `HELPER`;
Garantías e Indicadores continúan restringidos a `ADMIN` y `TECH`;
gestión de usuarios continúa reservada a `ADMIN`.
9. Evidencia de validación técnica
9.1. Comprobación de Django
```text
python manage.py check
System check identified no issues (0 silenced).
```
9.2. Pruebas específicas y por módulos
```text
python manage.py test customers devices
Found 64 test(s).
Ran 64 tests
OK
```
```text
python manage.py test orders
Found 180 test(s).
Ran 180 tests
OK
```
```text
python manage.py test accounts.test_hu26_permissions
Found 11 test(s).
Ran 11 tests
OK
```
```text
python manage.py test inventory
Found 50 test(s).
Ran 50 tests
OK
```
9.3. Suite completa del backend
Se ejecutó la suite completa después de integrar los cambios de HU-26:
```text
python manage.py test
Found 343 test(s).
System check identified no issues (0 silenced).

Ran 343 tests in 73.929s

OK
```
9.4. Verificación de migraciones
```text
python manage.py makemigrations --check --dry-run
No changes detected
```
9.5. Compilación del frontend
```text
npm --prefix ..\frontend run build

vite v5.4.8 building for production...
✓ 44 modules transformed.
✓ built in 1.36s
```
9.6. Revisión del diff
```text
git diff --check
```
El comando no reportó errores de espacios ni formato en el diff.
10. Validación funcional y casos puntuales
La conformidad general comunicada el 30-09-2026 permite avanzar. Antes de marcar HU-26 como finalizada se debe comprobar con casos reales especialmente:
acceso de `HELPER` a RUT y datos de contacto del cliente;
acceso de `HELPER` a la hoja de vida del equipo y evidencias;
acceso de `HELPER` al catálogo de repuestos sin costos;
alcance de la información financiera visible para `TECH`;
separación entre propuesta técnica y decisión administrativa de garantías;
coordinación de modificaciones sensibles de órdenes con HU-27.
La conformidad general fue comunicada por el responsable del proyecto; no se registró una validación individual de cada fila ni una prueba manual integral. Los ajustes puntuales se deben anotar con su decisión, fecha y evidencia, y coordinar con HU-27.
