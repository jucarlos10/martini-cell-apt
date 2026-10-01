# Martini Cell: guía de cambios y estado del tablero

Fecha de corte: 30 de septiembre de 2026 (Chile). Repositorio: [martini-cell-apt](https://github.com/jucarlos10/martini-cell-apt). Tablero: [martini cell kanban](https://github.com/users/jucarlos10/projects/1).

## Para leer en cinco minutos

Entre el 22 y el 30 de septiembre se integraron las funciones principales del MVP: usuarios, clientes, equipos, órdenes, inventario, costos, garantías e indicadores. Después se separaron las historias de garantías y repuestos para comprobar reglas concretas. Oscar desarrolló los flujos HU-21 a HU-26; las revisiones siguientes reforzaron privacidad de fotografías, trazabilidad, costos por perfil e integridad entre repuestos anulados y garantías. Estas correcciones complementan su trabajo y no implican que el conjunto de sus cambios se haya rechazado.

El responsable del proyecto comunicó el 30 de septiembre que Marcos dio su conformidad general para avanzar sin otra ronda formal de validación. Esa comunicación permitió cerrar HU-18 y HU-19, que ya estaban en «Validación con Marcos». No equivale a afirmar que se ejecutó una prueba manual de cada pantalla ni que Marcos decidió expresamente todos los casos particulares descritos abajo.

Los cambios llegaron a `main` mediante PR con pruebas automáticas de backend y compilación del frontend en GitHub Actions. No consta aquí una prueba presencial completa del negocio ni una puesta en producción. «En pruebas» identifica trabajo integrado cuya comprobación funcional o de casos límite aún sigue abierta.

## Cómo se llegó a este punto

| Etapa | Movimiento | Razón y resultado |
| --- | --- | --- |
| 22–24 sep. | [PR #20](https://github.com/jucarlos10/martini-cell-apt/pull/20), [#21](https://github.com/jucarlos10/martini-cell-apt/pull/21), [#25](https://github.com/jucarlos10/martini-cell-apt/pull/25)–[#34](https://github.com/jucarlos10/martini-cell-apt/pull/34) | Base de autenticación y usuarios, clientes, equipos y órdenes; estados, tiempos, consulta por código, interfaz conectada e inventario. Se construyó el recorrido operacional inicial. |
| 25 sep. | [PR #35](https://github.com/jucarlos10/martini-cell-apt/pull/35)–[#40](https://github.com/jucarlos10/martini-cell-apt/pull/40) | Costos y márgenes; garantías con historial; indicadores y viabilidad; pruebas de regresión e integración de Vue con Django. Se agregó observabilidad al flujo principal. |
| 25–26 sep. | [PR #41](https://github.com/jucarlos10/martini-cell-apt/pull/41)–[#45](https://github.com/jucarlos10/martini-cell-apt/pull/45) | Archivado/eliminación segura de usuarios, clientes, equipos, repuestos y proveedores; filtros de órdenes por fecha; configuración de entorno. Se protegieron referencias históricas y se facilitó la operación. |
| 26–29 sep. | [PR #56](https://github.com/jucarlos10/martini-cell-apt/pull/56), [#57](https://github.com/jucarlos10/martini-cell-apt/pull/57), [#64](https://github.com/jucarlos10/martini-cell-apt/pull/64)–[#66](https://github.com/jucarlos10/martini-cell-apt/pull/66) | CI para pruebas Django y compilación Vue; búsqueda de garantías; auditoría atómica de cambios de clientes; README actualizado. Cada PR nuevo se comprueba antes de integrarse. |
| 30 sep. | [PR #67](https://github.com/jucarlos10/martini-cell-apt/pull/67)–[#78](https://github.com/jucarlos10/martini-cell-apt/pull/78) | Desarrollo y revisión específica de garantías, solicitudes, repuestos y permisos. El detalle está en la tabla siguiente. |

La tabla resume cambios de código integrados; el historial de commits y cada PR contienen el diff exacto y sus autores.

## Cambios recientes explicados para el equipo

| Historia y PR | Qué cambió | Por qué se hizo y qué se comprobó |
| --- | --- | --- |
| HU-21, [#67](https://github.com/jucarlos10/martini-cell-apt/pull/67), Oscar | Eliminación de una garantía creada por error, con confirmación en interfaz, evento `DELETED` y bloqueo si ya tiene solicitudes. | La garantía debe desaparecer sin eliminar orden ni repuesto. Se detectó después que las revisiones persistían, pero no se podían consultar por el ID borrado: ver corrección de auditoría más abajo. |
| HU-22, [#68](https://github.com/jucarlos10/martini-cell-apt/pull/68), Oscar | Solicitudes de garantía asociadas a la orden y a una cobertura, con reglas de vigencia, duplicados e historial. | Registrar un reclamo sin alterar la cobertura. Quedó en pruebas para recorrer el flujo completo con datos representativos. |
| HU-23, [#69](https://github.com/jucarlos10/martini-cell-apt/pull/69) y [#70](https://github.com/jucarlos10/martini-cell-apt/pull/70), Oscar | Backend y pantalla para propuesta de TECH, devolución y resolución final de ADMIN. | Separar la propuesta técnica de la autorización administrativa y conservar cada paso. Quedó en pruebas del recorrido completo. |
| HU-24, [#72](https://github.com/jucarlos10/martini-cell-apt/pull/72), Oscar | Corrección de cantidad o nota de un uso de repuesto; la cantidad ajusta stock y costo con auditoría. | Permitir corregir errores sin alterar antecedentes; se adoptó el límite conservador de no cambiar repuesto, proveedor o costo mediante este flujo y de impedir cambios de cantidad con garantía, o cambios tras entrega/cierre. Los demás casos requieren tratamiento concreto. |
| HU-22, [#71](https://github.com/jucarlos10/martini-cell-apt/pull/71) y [#74](https://github.com/jucarlos10/martini-cell-apt/pull/74), revisión | Fotografías de reclamos servidas por una ruta privada y descargadas con extensión correcta. | Evitar exposición pública por URL directa y permitir abrir el archivo con su formato real. La PR #71 incluyó un ajuste de prueba para PostgreSQL. |
| HU-24, [#73](https://github.com/jucarlos10/martini-cell-apt/pull/73), revisión | Conservación del nombre/identidad del actor en la auditoría de correcciones. | El registro debe seguir siendo atribuible incluso cuando una cuenta se archive o elimine. |
| HU-26, [#75](https://github.com/jucarlos10/martini-cell-apt/pull/75), revisión | La API omite costos unitarios y subtotales de repuestos para HELPER; la interfaz también los oculta. | Ocultar importes solo en pantalla no protegía una llamada directa a la API. ADMIN y TECH mantienen el acceso definido en la matriz. |
| HU-25, [#76](https://github.com/jucarlos10/martini-cell-apt/pull/76), Oscar | Anulación lógica del uso de un repuesto con motivo, fecha y actor; devolución de stock una vez y retiro del costo vigente. | Corregir una asignación errónea sin borrar su historial. Se bloquea si hay garantía o la orden fue entregada/cerrada. |
| HU-26, [#77](https://github.com/jucarlos10/martini-cell-apt/pull/77), Oscar | Matriz de perfiles en [documento específico](hu26-matriz-permisos.md), validación de operaciones en API y controles en Vue. HELPER puede consultar/crear clientes, equipos y órdenes, pero no editarlos; se restringen historiales internos. | La seguridad debe aplicarse en la API, además de orientar la interfaz. Las pruebas de su PR incluyen la suite backend de 343 casos y la compilación Vue. La comunicación de conformidad general permite avanzar, pero la exposición de RUT/contacto y el alcance financiero por perfil merecen una comprobación específica. |
| HU-25, [#78](https://github.com/jucarlos10/martini-cell-apt/pull/78), revisión | La API rechaza registrar una garantía nueva sobre un uso de repuesto ya anulado, aun cuando se invoque directamente. | La pantalla filtraba esos usos, pero la API aún aceptaba su ID. Hay prueba de rechazo 400 e integridad del historial; CI backend y frontend pasó. |

## Auditoría de garantías eliminadas

La corrección adicional en este documento incorpora `warranty_id_snapshot` al historial. La creación, edición y eliminación copian el ID de la garantía antes del borrado; `GET /api/orders/<orden>/warranties/<garantía>/history/` podrá recuperar esas revisiones aunque la garantía ya no exista, siempre con autenticación y rol ADMIN o TECH y comprobando la orden. Una migración completa el ID de revisiones cuyos registros aún existen. Se agregan pruebas para la consulta posterior al borrado y para rechazar el acceso desde otra orden.

Limitación: en eliminaciones físicas ocurridas antes de esta migración, la clave foránea histórica ya quedó en `NULL`. No es posible reconstruir de manera fiable el ID original de esas revisiones; el endpoint nuevo solo puede garantizar la consulta por ID de eliminaciones posteriores. Las revisiones antiguas siguen almacenadas. La alternativa de baja lógica para todos los registros existentes sería un cambio de política y de modelo más amplio; no se afirma que Marcos la haya elegido.

## Estado y criterio de movimiento del Kanban

| Columna / historias | Motivo del estado actual |
| --- | --- |
| Finalizado: [HU-18 #46](https://github.com/jucarlos10/martini-cell-apt/issues/46), [HU-19 #47](https://github.com/jucarlos10/martini-cell-apt/issues/47) | Estaban en «Validación con Marcos» con PR #57 y CI aprobados. Se cerraron el 30 sep. por la conformidad general comunicada por el responsable del proyecto; el tablero las trasladó automáticamente. No se registró como ejecutada una prueba manual adicional. |
| Finalizado: [HU-25 #53](https://github.com/jucarlos10/martini-cell-apt/issues/53) | PR #76 cerró la historia y la movió automáticamente; PR #78 refuerza la regla al crear garantías. Se documentó el alcance real para evitar que la descripción vieja parezca pendiente. |
| En pruebas: [HU-20 #48](https://github.com/jucarlos10/martini-cell-apt/issues/48), [HU-22 #50](https://github.com/jucarlos10/martini-cell-apt/issues/50), [HU-23 #51](https://github.com/jucarlos10/martini-cell-apt/issues/51) | Código integrado y pruebas automáticas, pero falta recorrer en interfaz los casos de modificación, apertura, propuesta, devolución y cierre, incluidos errores y permisos. |
| En pruebas: [HU-24 #52](https://github.com/jucarlos10/martini-cell-apt/issues/52), [HU-26 #54](https://github.com/jucarlos10/martini-cell-apt/issues/54) | La conformidad general permite dejar de tratarlas como bloqueadas por una validación formal; el comportamiento conservador de HU-24 y la matriz implementada de HU-26 se verifican ahora con escenarios reales y preguntas concretas. |
| En pruebas: [HU-21 #49](https://github.com/jucarlos10/martini-cell-apt/issues/49) | Se continúa con la eliminación física que describe la implementación de Oscar y se recupera la consulta de auditoría por ID para borrados futuros. Pendiente revisar la limitación histórica y el flujo en pantalla antes de cerrar. |
| En desarrollo: [TEC-03 #24](https://github.com/jucarlos10/martini-cell-apt/issues/24) | Política transversal de permisos, auditoría e inmutabilidad; HU-26 implementa una parte, no todo el alcance. |
| Pendiente: [HU-27 #55](https://github.com/jucarlos10/martini-cell-apt/issues/55) | Definir y registrar cambios sensibles de la orden; no queda completada automáticamente por HU-26. |

«Finalizado» significa historia cerrada con evidencia de código/pruebas y aceptación general comunicada cuando correspondía. «En pruebas» significa que hay implementación, pero se conservan comprobaciones técnicas o de uso. «Bloqueado» se reserva para un impedimento concreto que realmente detiene el trabajo. Los estados del tablero y los issues se actualizan por separado cuando la automatización no los sincroniza.

## Preguntas pequeñas y próximas comprobaciones

1. HU-24: confirmar si cantidad y nota son los únicos campos corregibles; para cambiar repuesto, proveedor o costo se propone anular y registrar otro uso. Confirmar también que una garantía asociada o entrega/cierre impida cambiar la cantidad. Hasta entonces se mantienen las reglas conservadoras implementadas.
2. HU-26: comprobar con un caso real qué datos de identificación/contacto necesita HELPER en recepción y qué importes puede consultar TECH; la matriz vigente está en [hu26-matriz-permisos.md](hu26-matriz-permisos.md). No ampliar acceso sin una decisión expresa.
3. HU-21: comprobar si la eliminación física con evento de auditoría y sin solicitudes asociadas cubre la operación diaria. La consulta histórica por ID funciona para eliminaciones posteriores a la migración, no repara IDs ya perdidos.
4. HU-20/22/23: recorrer en pantalla fechas inválidas, garantía vencida, reclamo duplicado, devolución al técnico, resolución administrativa y rechazos por perfil. Registrar cualquier defecto reproducible como tarea concreta.
5. HU-27/TEC-03: precisar qué campos de una orden exigen motivo, cuál es su regla por estado y qué evidencia de valor anterior/nuevo debe quedar.

## Cómo informar cambios sin confusiones

Para cada ajuste nuevo, enlazar la historia, PR, motivo, prueba automática, comprobación manual si se ejecutó y estado del tablero. Separar una corrección de seguridad o integridad de una preferencia funcional por confirmar. Si se comunica una conformidad general, escribir quién la comunicó y su alcance sin atribuirle a Marcos pruebas o decisiones particulares no registradas. Esto permite que Oscar, Rafael y el resto del equipo lean la misma evidencia y sepan qué queda abierto.
