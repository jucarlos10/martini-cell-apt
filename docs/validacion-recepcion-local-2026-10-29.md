# Recepción y entrega del seguimiento: validación en el local

Fecha: 29-10-2026. Resumen funcional sin datos de clientes.

## Flujo observado y decisiones

- En la recepción se anota nombre, teléfono, problema informado y precio de la reparación. La aplicación también asocia un equipo y genera código, fecha y estado inicial.
- Para entregar el código de seguimiento se aceptaron tres opciones: comprobante en papel, correo y WhatsApp. La elección depende de lo que el cliente pueda usar; si su teléfono está en reparación, papel o correo siguen disponibles. El personal selecciona el destinatario y envía el mensaje manualmente.
- La consulta pública enseña el código, estado y fechas de los cambios de estado. Nombre, teléfono, precio, observaciones, diagnóstico, notas y fotos permanecen en el área autenticada. Es una decisión de diseño orientada a dar información útil sin publicar datos del cliente o del taller.
- El comprobante privado muestra el código, fecha, cliente, teléfono de contacto, equipo, problema declarado, observaciones de ingreso y precio informado al recibir el equipo. Indica que ese precio puede cambiar tras la revisión técnica y que el comprobante no acredita pago ni autorización.
- El precio de ingreso es opcional si todavía no se puede informar. Se guarda por separado de `OrderFinancial.price_charged`, que representa el precio final para el cálculo financiero. Una corrección del precio inicial requiere motivo y queda auditada.

## Diferencia pendiente de validar

El registro actual de clientes requiere RUT y equipo, aunque la lista de datos anotados habitualmente en el local se centra en nombre y teléfono. Antes de cambiar la obligatoriedad del RUT conviene confirmar si lo necesitan para facturación o búsqueda posterior y cómo evitar clientes duplicados sin él. Mientras tanto no se elimina el campo ni se inventan identificadores.

## Prueba de aceptación sugerida

Con una orden y cliente de ensayo, registrar un precio inicial y generar el comprobante. Confirmar que las tres vías de entrega estén disponibles, que el mensaje de correo y WhatsApp solo incluya código y enlace, que la consulta pública no muestre datos privados y que un cambio del precio inicial solicite motivo. Repetir el comprobante desde el detalle y comprobar que el precio final continúe pendiente hasta registrarlo por separado.

La impresión, los borradores de correo y WhatsApp y la visualización móvil requieren prueba manual. Esta validación funcional no demuestra persistencia de fotos ni respaldos del host, que siguen en el PR #88.
