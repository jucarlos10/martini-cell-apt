# Beneficios por ingresos de clientes

Estado: prototipo universitario en pruebas. Este flujo se demuestra con fichas y
órdenes de ensayo; no establece una promoción comercial vigente ni compromete
descuentos para clientes reales.

Para presentarlo sin ingresar datos, un administrador puede entrar al panel y
abrir «Probar simulador». Allí completa el primer ciclo de seis ingresos, registra
un beneficio simulado y repite con cinco y luego con cuatro. La simulación vive
solo en la memoria de esa pantalla: no modifica la base de datos ni el contador
de ninguna ficha real y se borra al salir.

## Regla acordada en el local

Una visita se cuenta cuando se registra una orden de servicio para la ficha del cliente.
Consultar el código de seguimiento o iniciar sesión no suma visitas. El RUT sigue
siendo opcional para registrar al cliente, aunque se necesita para activar los
avisos del programa. Una ficha sin RUT conserva su historial de órdenes.

| Ciclo | Ingresos para avisar | Total acumulado al cumplirlo |
| --- | ---: | ---: |
| Primer beneficio | 6 | 6 |
| Segundo beneficio | 5 | 11 |
| Tercer beneficio | 4 | 15 |
| Siguientes beneficios | 4 | 19, 23, 27... |

Al cumplir la meta aparece un aviso persistente en el panel del administrador,
en el directorio de clientes y después de crear una orden. En la demostración,
el administrador representa la decisión de Marcos y registra el beneficio de
prueba elegido, con fecha y usuario responsable. El sistema no crea cupones,
modifica precios ni envía mensajes automáticos. Solo entonces se cierra
el aviso y el contador del ciclo empieza desde cero. Si se registran otras órdenes
antes de aplicar el beneficio, quedan contabilizadas para el ciclo siguiente.

Las órdenes anteriores vinculadas a la misma ficha también se consideran; si
el RUT se añade más tarde, puede aparecer un beneficio pendiente. Antes de crear
un cliente, buscar por nombre o teléfono para evitar fichas duplicadas. Una orden
reasignada a otro cliente deja de sumar al cliente anterior y pasa a sumar al
nuevo. El historial de beneficios ya aplicados se conserva para auditoría.

## Verificación manual antes de fusionar

1. En un entorno de ensayo, registrar seis órdenes para la misma ficha con datos ficticios.
   Revisar aviso en panel y ficha; la consulta pública solo debe mostrar estado.
2. Aplicar un beneficio en la ficha con usuario administrador. Confirmar que
   desaparece el aviso y que la próxima meta es cinco; ningún precio debe cambiar.
3. Registrar cinco órdenes más y repetir. Desde entonces la meta debe ser cuatro
   y mantenerse en cuatro después de cada aplicación.
4. Probar una ficha sin RUT: las órdenes deben sumar, pero no debe aparecer aviso
   hasta que se aporte el RUT. Probar otro rol: puede ver el contador interno,
   pero no registrar el beneficio ni consultar la lista de avisos del administrador.

Esta propuesta depende del RUT opcional de PR #91. La publicación requiere aplicar
la migración de clientes `0004_clientloyaltyreview` y completar las comprobaciones
habituales del host antes de fusionar.
