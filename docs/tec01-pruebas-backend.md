\# TEC-01 — Pruebas automatizadas del backend



\## 1. Objetivo



Incorporar pruebas automatizadas para verificar las funcionalidades del backend correspondientes a HU-01 a HU-07 de Martini Cell.



La suite contempla escenarios positivos y negativos relacionados con autenticación, administración de usuarios, clientes, equipos y órdenes de servicio. Su propósito es detectar regresiones antes de integrar nuevas funcionalidades.



\## 2. Archivos incorporados



| Archivo | Pruebas nuevas | Alcance |

|---|---:|---|

| `backend/accounts/tests.py` | 15 | Autenticación JWT y administración de usuarios |

| `backend/customers/tests.py` | 22 | Registro, búsqueda, actualización y validación de clientes |

| `backend/devices/tests.py` | 25 | Registro, identificadores e historial de equipos |

| `backend/orders/test\_tec01\_orders.py` | 25 | Creación, consulta y validaciones de órdenes |

| \*\*Total\*\* | \*\*87\*\* | |



El archivo existente `backend/orders/tests.py` se conserva sin reemplazar sus pruebas de estados e informes técnicos.



\## 3. Funcionalidades verificadas



\### 3.1. Autenticación y usuarios



\- Inicio de sesión JWT con credenciales válidas.

\- Rechazo de contraseñas incorrectas y cuentas inactivas.

\- Renovación del token de acceso mediante un token de actualización válido.

\- Rechazo de tokens inválidos y del uso de un token de actualización como token de acceso.

\- Consulta del usuario autenticado mediante `/api/auth/me/`.

\- Restricción del acceso anónimo.

\- Consulta, creación y actualización de usuarios por un administrador.

\- Almacenamiento de contraseñas mediante hash.

\- Rechazo de operaciones administrativas para roles no autorizados.



Se mantienen también las pruebas existentes que protegen la última cuenta administradora activa y otras restricciones de administración.



\### 3.2. Clientes



\- Registro de clientes y asignación del usuario responsable.

\- Consulta, búsqueda y actualización.

\- Búsqueda por nombre, teléfono, correo electrónico y RUT.

\- Normalización del RUT, incluidos separadores y dígito verificador `K`.

\- Rechazo de RUT inválidos o duplicados.

\- Validación de campos obligatorios.

\- Registro del historial de cambios y del usuario que los realizó.

\- Prevención de modificaciones no autorizadas.



\### 3.3. Equipos



\- Registro, listado, consulta y actualización de equipos.

\- Asociación de un equipo con un cliente existente.

\- Rechazo de clientes inexistentes y tipos de equipo inválidos.

\- Normalización de IMEI y número de serie.

\- Rechazo de IMEI y números de serie duplicados, incluso si se ingresan con distinto formato.

\- Tratamiento de identificadores opcionales vacíos como valores nulos.

\- Registro del usuario responsable de las modificaciones.

\- Consulta del historial técnico asociado al equipo.

\- Verificación de que el historial no incluya órdenes de otros equipos.

\- Restricción del acceso anónimo.



\### 3.4. Órdenes de servicio



\- Creación de órdenes asociadas a un cliente y su equipo.

\- Generación automática de un código de seguimiento único.

\- Asignación del estado inicial `RECEIVED`.

\- Creación del primer registro del historial de estados.

\- Rechazo de relaciones inválidas entre cliente y equipo.

\- Validación de campos obligatorios e identificadores inexistentes.

\- Consulta y actualización de la información permitida.

\- Protección del código de seguimiento y del estado frente a modificaciones por el endpoint general.

\- Consulta del historial de estados y del usuario responsable de cada cambio.

\- Restricción del acceso anónimo.



Estas pruebas complementan las pruebas existentes de transiciones de estados, informes técnicos y otras funcionalidades del backend.



\## 4. Ejecución de la suite



Desde la carpeta `backend`, con el entorno virtual activado, ejecutar:



```powershell

python manage.py test --keepdb --verbosity 2

```



Este comando descubre y ejecuta la suite completa del backend.



La opción `--keepdb` permite reutilizar y conservar la base de pruebas `test\_martini\_cell`. Django ejecuta las pruebas de forma aislada, sin utilizar la base de desarrollo `martini\_cell`.



\## 5. Evidencia de ejecución



Resultado de la ejecución completa de TEC-01:



```text

Found 182 test(s).

Using existing test database for alias 'default' ('test\_martini\_cell')...

System check identified no issues (0 silenced).



\----------------------------------------------------------------------

Ran 182 tests in 41.380s



OK

Preserving test database for alias 'default' ('test\_martini\_cell')...

```



| Indicador | Resultado |

|---|---:|

| Pruebas existentes antes de TEC-01 | 95 |

| Pruebas incorporadas en TEC-01 | 87 |

| Total de pruebas ejecutadas | 182 |

| Errores o fallos reportados | 0 |

| Resultado final | `OK` |



Se ejecutaron también los cuatro módulos nuevos de manera individual antes de realizar la validación completa.



\## 6. Datos utilizados



Las pruebas crean usuarios, clientes, equipos y órdenes ficticias dentro del entorno de pruebas de Django.



No se utilizan datos personales reales ni se requiere modificar los registros de la base de desarrollo para ejecutar la suite.



Los datos presentes actualmente en la base de desarrollo corresponden a registros de desarrollo y prueba; no deben interpretarse como un historial operativo real del negocio.



\## 7. Alcance y limitaciones



\### Cierre de sesión lógico



Las pruebas incorporadas validan la autenticación y renovación de tokens JWT, pero no prueban una revocación de tokens en el servidor.



El backend no dispone de un endpoint específico de cierre de sesión ni de una lista de bloqueo de tokens configurada. Por lo tanto, descartar los tokens del lado del cliente constituye un cierre de sesión lógico, pero no invalida automáticamente un token que todavía se encuentre vigente.



No se declara la revocación de JWT como funcionalidad verificada en TEC-01. La comprobación del flujo de cierre de sesión entre frontend y backend queda para las pruebas de integración correspondientes.



\### Cobertura



El resultado `OK` confirma que las 182 pruebas ejecutadas finalizaron correctamente. No representa una medición del porcentaje de cobertura de código ni sustituye pruebas de integración frontend–backend, seguridad o aceptación con usuarios.



Las verificaciones adicionales de permisos y auditoría corresponden al trabajo de TEC-03.



\## 8. Conclusión



TEC-01 incorpora 87 pruebas automatizadas sin eliminar las existentes. La ejecución conjunta de 182 pruebas finalizó correctamente y proporciona una base de regresión para continuar el desarrollo del backend de Martini Cell.