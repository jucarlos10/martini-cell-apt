# Ensayo de trazabilidad en el host

Este recorrido comprueba la plataforma publicada. La CI usa datos y servicios
simulados; no acredita por sí sola el comportamiento de Vercel, Railway ni del
proveedor de mensajes.

## Preparación

- Usar una cuenta de ensayo con rol `ADMIN` o `TECH` y un cliente/equipo
  identificados claramente como **PRUEBA**. No usar una orden real de Marcos.
- Si se probará correo, registrar una casilla de ensayo que controle el equipo.
  Si se probará WhatsApp, usar solo un número de ensayo autorizado.
- Anotar el código `MC-...` de la orden. No compartir contraseñas, tokens, RUT
  reales ni capturas que muestren datos personales.

## Recorrido mínimo

| Paso | Acción en pantalla | Resultado esperado |
| --- | --- | --- |
| 1 | En **Órdenes → Nueva orden**, seleccionar cliente y equipo de prueba, describir la falla y guardar. | Aparece el código de seguimiento y el botón **Administrar esta orden**. |
| 2 | Abrir **Administrar esta orden → Resumen**. | El bloque **Trazabilidad de esta orden** muestra **Ingresado** como último movimiento. |
| 3 | Pulsar **Ver línea de tiempo**. | El primer evento indica ingreso, fecha y responsable; el estado actual es **Ingresado**. |
| 4 | Pulsar **Ver seguimiento como cliente**. | Se abre la consulta pública con el código cargado y el estado **Ingresado**. No aparecen RUT, contacto, notas internas ni responsable. |
| 5 | Volver a la línea de tiempo interna, elegir **Diagnóstico**, agregar una nota de prueba y pulsar **Guardar cambio de estado**. | Se registra un segundo evento con fecha, responsable y nota. Si se configuró un canal de ensayo, revisar el resultado del aviso. |
| 6 | Actualizar la consulta pública. | Se ve **Diagnóstico** y las fechas de los dos estados, sin la nota interna del paso 5. |
| 7 | Volver a **Órdenes**, buscar por código y abrir la fila. | La orden sigue disponible y el resumen muestra el último movimiento. |

No hay que recorrer los diez estados solo para probar la pantalla. El ensayo
termina al comprobar el cambio a **Diagnóstico** y deja la orden identificada
como prueba en la base. No subir fotografías hasta confirmar la persistencia
del volumen privado en Railway.

## Registro del resultado

Anotar fecha/hora, código de la orden de prueba, perfil usado, estado observado
en pasos 2, 3, 4, 5, 6 y 7, resultado del aviso si se configuró, y cualquier
mensaje de error exacto. Si algo falla, indicar **paso** y **resultado obtenido**;
no reenviar datos personales ni credenciales.

## Lo que este ensayo no cierra

TEC-03 (#24) sigue abierto hasta comprobar con casos reales autorizados los
permisos por rol, los cambios sensibles y los campos de la consulta pública.
Los historiales de informes, repuestos y garantías están en sus secciones;
la línea de tiempo principal registra estados y avisos, no todos los eventos
en una única lista.
