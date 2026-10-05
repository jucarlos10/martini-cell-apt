# Entrega a Oscar: CSV de casos para HU-17

Esta guía prepara la **revisión del dataset de tiempo técnico**. El validador
funciona sin servidor, base de datos ni credenciales. No importa órdenes al
sistema, no entrena un modelo y no sube archivos. Una importación histórica de
órdenes al producto requiere un diseño aparte: el formulario actual asigna la
fecha de ingreso al crear la orden.

## 1. Preparar los casos en privado

Usar la planilla privada de preparación y conservar allí la relación entre
fuentes y casos. Las hojas de movimientos y chat contienen **candidatos**, no
órdenes confirmadas. Las hojas de fotos y audios sirven como índice de
evidencia; una fecha de mensaje o de cobro no demuestra cuándo empezó o terminó
la reparación. El catálogo de precios tampoco demuestra una reparación.

Para cada caso, confirmar con el registro operativo y la revisión técnica:

1. Una reparación real y única de Martini Cell, sin pagos duplicados ni ventas.
2. Estado final **entregado o cerrado**, resultado reparado o parcial, y fecha
   real de finalización. Registrar diagnóstico y trabajo en la ficha privada.
3. Minutos técnicos finales medidos con el historial de estados de HU-11 o
   reconstruidos y revisados expresamente por el técnico. Separar los minutos
   de espera, incluidos autorización, repuestos y retiro.
4. Clasificación de falla basada en lo **conocido al ingreso**, antes de
   observar el resultado. Revisar anonimización y procedencia con la persona
   responsable. Mantener las referencias y la aprobación en la planilla privada.

Crear un `case_id` UUID v4 nuevo por cada reparación. Guardar la correspondencia
entre ese ID y el número de orden, ID provisional, WhatsApp, audio y foto **solo
en el registro privado**. En Python se puede generar con
`python -c "import uuid; print(uuid.uuid4())"`. No copiar al CSV nombre, RUT,
teléfono, IMEI, serie, código de seguimiento, transcripciones, fotos ni audios.

## 2. Exportar el contrato v1

Copiar [`ml_cases_v1.csv`](templates/ml_cases_v1.csv) a
`private_data/ml_cases_v1.csv` en la raíz del proyecto. Esa carpeta está
excluida de Git. Editar o exportar en **CSV UTF-8 con comas**, encabezado en
el orden de la plantilla y una fila por caso confirmado. La plantilla vacía
debe fallar la validación: no hay casos para aprobar automáticamente.

| Columna | Contenido permitido |
| --- | --- |
| `case_id` | UUID v4 nuevo, sin vínculo público al cliente o a la orden. |
| `origin` | `MARTINI`; datos externos y sintéticos quedan en otro conjunto. |
| `source_verified`, `anonymized` | `SI` solo tras revisión humana de procedencia y anonimización. |
| `review_status` | `VALIDADO` solo después de confirmar el caso; el validador no comprueba quién lo revisó. |
| `final_status` | `DELIVERED` o `CLOSED`. |
| `repair_result` | `REPARADO` o `PARCIAL`; excluir casos sin reparación efectiva. |
| `equipment_type` | `CELULAR`, `NOTEBOOK`, `PC`, `TABLET` u `OTRO`, como en Django. |
| `issue_category_at_intake` | `PANTALLA`, `BATERIA`, `CARGA`, `SOFTWARE`, `PLACA` u `OTRA`; clasificar la falla informada al ingreso. |
| `finished_on` | Fecha real de finalización `AAAA-MM-DD`, no fecha comercial ni del mensaje. |
| `technical_minutes` | Número mayor que cero, hasta dos decimales, máximo 10.080; tiempo técnico final. |
| `waiting_minutes` | Número desde cero, hasta dos decimales, máximo 129.600; separado del técnico. |
| `time_basis` | `STATUS_HISTORY` si el cálculo proviene de HU-11; `MANUAL_VERIFIED` si fue reconstruido y revisado. |

Los límites máximos de minutos son alertas operativas del contrato, no una
afirmación sobre tiempos reales. Si un caso auténtico los supera, revisar el
historial y proponer un cambio de contrato documentado antes de incorporarlo.
No incluir columnas extra: un dato posterior a la reparación puede producir
fuga de información en una futura predicción.
Las entradas estructuradas de v1 son tipo de equipo y categoría de falla. La
marca y el modelo originales todavía requieren normalización y revisión de
privacidad; Oscar podrá proponer una versión nueva del contrato si los datos
validados justifican incorporarlos.

## 3. Validar antes de entregarlo

Desde la raíz del repositorio:

```bash
python tools/validate_ml_dataset.py private_data/ml_cases_v1.csv
```

El comando devuelve código `0` si todas las filas cumplen el formato y código
`1` si falta una fila válida o encuentra errores. Muestra cantidades y números
de línea, **nunca el contenido de las celdas**. Corregir en la fuente privada y
exportar de nuevo. Para verificar la herramienta sin datos reales:

```bash
python -m unittest discover -s tools -p 'test_*.py'
```

## 4. Entrega y siguiente decisión

Oscar puede trabajar con `private_data/ml_cases_v1.csv` localmente o en un
almacenamiento privado acordado con el equipo. El validador solo verifica
declaraciones y consistencia básica: un `SI` escrito en un CSV no acredita por
sí solo consentimiento, procedencia, anonimización ni aprobación de Marcos.
Mantener el registro fuente y la revisión humana por separado. Antes de un
experimento de ML, comparar el conjunto con los criterios de
[HU-17](evaluacion-hu17-estimacion-tiempo.md), revisar diversidad y separar
entrenamiento de evaluación sin fuga de información. El umbral de 30 casos es
una señal para reevaluar, no una aprobación automática.

Para importar órdenes históricas al backend o alojar el dataset en el host,
definir primero volumen privado, respaldo, permisos y política de fechas y
duplicados. Los pasos de despliegue pendientes están en
[preparación de datos y host](preparacion-dataset-y-host-2026-10-04.md). El CSV
de HU-17 no debe convertirse en órdenes del sistema por una carga directa.
