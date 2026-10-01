# Registro de cambios de Martini Cell

Guía para Juan, Oscar, Rafael y Marcos. Corte: 30 de septiembre de 2026, hora de Chile. [Repositorio](https://github.com/jucarlos10/martini-cell-apt) · [Tablero Kanban](https://github.com/users/jucarlos10/projects/1).

## Resumen para el equipo

El producto ya reúne usuarios, clientes, equipos, órdenes, repuestos, costos, garantías e indicadores. Oscar implementó las historias recientes de garantías, repuestos y permisos. Después de revisar esos cambios se integraron ajustes puntuales de privacidad, trazabilidad e integridad de datos. Esos ajustes complementan el trabajo de Oscar: cada uno tiene un motivo y una PR que permite ver el cambio exacto.

El responsable del proyecto comunicó que Marcos dio su conformidad general para avanzar sin otra ronda formal. Por eso HU-18 y HU-19 salieron de «Validación con Marcos» y quedaron finalizadas. La conformidad general no se registra aquí como una prueba manual de cada pantalla ni como respuesta individual a todos los casos particulares.

Las PR mencionadas abajo están integradas en `main`. Sus pruebas de backend y la compilación del frontend aprobaron en GitHub Actions. Las historias «En pruebas» todavía necesitan recorridos de uso y casos reales antes de cerrarse. No se afirma una puesta en producción.

## Cómo se construyó la base

Del 22 al 24 de septiembre se incorporaron autenticación, usuarios, clientes, equipos, órdenes, estados, tiempos, consulta pública por código, interfaz e inventario. El detalle está en las [PR #20 a #34](https://github.com/jucarlos10/martini-cell-apt/pulls?q=is%3Apr+is%3Amerged).

El 25 de septiembre se agregaron costos y márgenes, garantías e historial, indicadores, pruebas de regresión e integración Vue-Django ([PR #35 a #40](https://github.com/jucarlos10/martini-cell-apt/pulls?q=is%3Apr+is%3Amerged)). Luego llegaron eliminaciones seguras, filtro de órdenes por fecha y configuración de entorno ([PR #41 a #45](https://github.com/jucarlos10/martini-cell-apt/pulls?q=is%3Apr+is%3Amerged)).

Entre el 26 y el 29 de septiembre se automatizaron las pruebas Django y la compilación Vue ([PR #56](https://github.com/jucarlos10/martini-cell-apt/pull/56) y [#57](https://github.com/jucarlos10/martini-cell-apt/pull/57)); también se añadieron búsqueda de garantías, auditoría atómica de clientes y actualización del README ([PR #64 a #66](https://github.com/jucarlos10/martini-cell-apt/pulls?q=is%3Apr+is%3Amerged)).

## Garantías y reclamos

### HU-18 y HU-19 Consultar y registrar garantías

Oscar ya había incorporado la consulta y el registro de garantías del servicio y de repuestos, con fechas, condiciones, permisos e historial. Las [PR #36](https://github.com/jucarlos10/martini-cell-apt/pull/36), [#40](https://github.com/jucarlos10/martini-cell-apt/pull/40) y [#57](https://github.com/jucarlos10/martini-cell-apt/pull/57) reúnen la implementación y evidencia técnica. HU-18 y HU-19 estaban esperando la validación general de Marcos. Con la conformidad comunicada, se cerraron los [issues #46](https://github.com/jucarlos10/martini-cell-apt/issues/46) y [#47](https://github.com/jucarlos10/martini-cell-apt/issues/47), y el tablero los movió a Finalizado. No se registró como ejecutado un recorrido manual adicional.

### HU-21 Eliminar una garantía ingresada por error

Oscar integró la [PR #67](https://github.com/jucarlos10/martini-cell-apt/pull/67). Se puede eliminar una garantía sin borrar la orden ni el repuesto; la interfaz pide confirmación, se registra un evento de eliminación y se impide borrar una garantía que ya tiene reclamos asociados.

En la revisión se observó que el historial quedaba guardado, pero perdía el vínculo necesario para consultarlo por el ID de la garantía borrada. La [PR #79](https://github.com/jucarlos10/martini-cell-apt/pull/79) guarda una copia estable de ese ID en cada revisión y permite consultar la auditoría posterior al borrado con el mismo control de permisos y de orden. La prueba automática comprueba la consulta y rechaza usar el ID desde otra orden.

Límite conocido: para garantías eliminadas antes de la nueva migración, el ID original de las revisiones antiguas ya no se puede reconstruir con certeza. Esas filas siguen guardadas. El [issue #49](https://github.com/jucarlos10/martini-cell-apt/issues/49) está En pruebas para revisar la interacción en pantalla y confirmar si la eliminación física satisface los casos reales.

### HU-22 Ingresar una solicitud de garantía

La [PR #68](https://github.com/jucarlos10/martini-cell-apt/pull/68) de Oscar permite abrir un reclamo asociado a una garantía, registrar problema e historial, y aplicar reglas de vigencia y solicitudes repetidas. Una solicitud es el reclamo concreto; no cambia por sí sola la cobertura original.

La revisión protegió las fotografías de reclamos detrás de una ruta privada ([PR #71](https://github.com/jucarlos10/martini-cell-apt/pull/71)) y corrigió la extensión del archivo descargado ([PR #74](https://github.com/jucarlos10/martini-cell-apt/pull/74)). El motivo fue impedir acceso público por enlace directo y conservar un archivo que se pueda abrir correctamente. El [issue #50](https://github.com/jucarlos10/martini-cell-apt/issues/50) sigue En pruebas del flujo completo.

### HU-23 Resolver una solicitud de garantía

Oscar integró API e interfaz en las [PR #69](https://github.com/jucarlos10/martini-cell-apt/pull/69) y [#70](https://github.com/jucarlos10/martini-cell-apt/pull/70). TECH propone una solución; ADMIN puede aprobarla, rechazarla o devolverla con motivo. El historial conserva propuestas, correcciones y decisión final. Esta separación permite identificar quién propuso y quién autorizó. El [issue #51](https://github.com/jucarlos10/martini-cell-apt/issues/51) sigue En pruebas para recorrer propuesta, devolución, resolución y rechazos por perfil.

### HU-20 Modificar una garantía

La modificación de garantía y su historial ya estaban implementados. El [issue #48](https://github.com/jucarlos10/martini-cell-apt/issues/48) continúa En pruebas: falta recorrer la edición en pantalla, fechas inválidas, permisos y casos de órdenes cerradas o con reclamos.

## Repuestos y costos

### HU-24 Corregir un uso de repuesto

Oscar integró la [PR #72](https://github.com/jucarlos10/martini-cell-apt/pull/72). Se puede corregir cantidad o nota con motivo e historial. Un cambio de cantidad ajusta el stock y recalcula el costo de la orden. La [PR #73](https://github.com/jucarlos10/martini-cell-apt/pull/73) conservó la identidad del autor en ese historial aunque después se archive o elimine su cuenta.

La regla actual es conservadora: este flujo no cambia repuesto, proveedor ni costo unitario; impide corregir cantidad cuando hay garantía asociada y bloquea cambios tras entrega o cierre. La conformidad general permite avanzar sin esperar otra ronda formal, pero esas reglas aún deben comprobarse en escenarios reales. El [issue #52](https://github.com/jucarlos10/martini-cell-apt/issues/52) pasó de Bloqueado a En pruebas.

### HU-25 Anular un uso de repuesto

Oscar integró la [PR #76](https://github.com/jucarlos10/martini-cell-apt/pull/76): anulación lógica con motivo, fecha y actor; devolución de unidades al stock una sola vez y exclusión del costo vigente. Se conserva el registro original. El sistema impide anular si hay una garantía vinculada o si la orden fue entregada o cerrada.

La interfaz ya omitía los usos anulados al ofrecer repuestos para una garantía, pero una llamada directa a la API todavía aceptaba su ID. La [PR #78](https://github.com/jucarlos10/martini-cell-apt/pull/78) cerró ese paso y agregó una prueba de rechazo sin registros parciales. Backend y frontend aprobaron en CI. El [issue #53](https://github.com/jucarlos10/martini-cell-apt/issues/53) está Finalizado.

## Permisos por perfil

### HU-26 ADMIN TECH y HELPER

La [PR #77](https://github.com/jucarlos10/martini-cell-apt/pull/77) de Oscar documentó la [matriz de permisos](hu26-matriz-permisos.md) y aplicó controles en la API y en Vue. HELPER puede consultar y crear clientes, equipos y órdenes, pero no modificar los registros existentes; tampoco ve historiales internos reservados. La suite backend de esa PR registró 343 pruebas y el frontend compiló.

Antes, la [PR #75](https://github.com/jucarlos10/martini-cell-apt/pull/75) impidió que HELPER recibiera costos unitarios y subtotales de repuestos desde la API. Se hizo porque esconderlos solo en la pantalla permitía obtenerlos mediante una llamada directa.

Con la conformidad general comunicada, el [issue #54](https://github.com/jucarlos10/martini-cell-apt/issues/54) pasó de En desarrollo a En pruebas. Antes de cerrarlo hay que comprobar qué RUT y contactos necesita HELPER en recepción y qué importes debe consultar TECH. No se amplió acceso a datos mientras se aclaran esos puntos.

## Estado del Kanban al cierre de esta revisión

- Finalizado: HU-18 (#46), HU-19 (#47) y HU-25 (#53). Las dos primeras salieron de «Validación con Marcos» por la conformidad general comunicada; HU-25 quedó cerrada tras su implementación y corrección.
- En pruebas: HU-20 (#48), HU-21 (#49), HU-22 (#50), HU-23 (#51), HU-24 (#52) y HU-26 (#54). El código está integrado, pero aún quedan recorridos de uso o casos concretos por comprobar.
- En desarrollo: TEC-03 (#24), la política transversal de permisos, auditoría e inmutabilidad de órdenes. HU-26 cubre una parte de ese trabajo.
- Pendiente: HU-27 (#55), cambios sensibles de una orden. La implementación de permisos no resuelve por sí sola qué campos pueden cambiar y cómo registrar valor anterior, nuevo, responsable y motivo.

El [tablero](https://github.com/users/jucarlos10/projects/1) y los issues muestran el estado vivo; esta guía deja constancia de las razones de los movimientos del 30 de septiembre.

## Decisiones y comprobaciones que faltan

1. HU-24: confirmar si cantidad y nota son los únicos campos corregibles. Para cambiar repuesto, proveedor o costo se propone anular el uso y registrar uno nuevo. Confirmar los límites ante garantía asociada y orden entregada o cerrada.
2. HU-26: comprobar con recepción el acceso necesario de HELPER a RUT y contacto, y con el equipo técnico los importes que necesita TECH. No ampliar permisos mientras se resuelve.
3. HU-21: comprobar si la eliminación física con auditoría y bloqueo ante reclamos cubre el trabajo diario. La corrección del historial solo garantiza la consulta por ID para borrados posteriores a la migración.
4. HU-20, HU-22 y HU-23: probar fechas inválidas, garantía vencida, reclamo repetido, devolución, resolución final y errores de permisos en la interfaz. Registrar cada defecto reproducible en un issue.
5. TEC-03 y HU-27: precisar campos sensibles de órdenes, regla por estado y evidencia del cambio.

Para comunicar un ajuste nuevo al equipo, indicar historia, PR, cambio, motivo, prueba automática y prueba manual solo si realmente se ejecutó. Así todos pueden distinguir lo ya integrado de una decisión que todavía falta tomar.
