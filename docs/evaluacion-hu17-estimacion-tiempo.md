# HU-17 — Evaluación experimental de estimación del tiempo técnico

## 1. Objetivo

La HU-17 tiene como objetivo evaluar si Martini Cell dispone de datos
suficientes y adecuados para estimar el tiempo técnico de reparación mediante
Machine Learning.

La estimación solo se integrará al producto si se dispone de datos operacionales
reales, finalizados, consistentes y anonimizados, y si un modelo demuestra una
mejora medible frente a una línea base simple.

El resultado deberá utilizarse únicamente como apoyo para el técnico, nunca
como diagnóstico ni decisión automática.

---

## 2. Alcance y naturaleza de los datos actuales

**Fecha de evaluación:** 25-09-2026.

La base de datos local contiene actualmente cuatro órdenes utilizadas durante
el desarrollo y las pruebas funcionales de Martini Cell.

Estos registros NO constituyen un conjunto histórico validado de reparaciones
reales del negocio.

Por lo tanto, las cifras presentadas en este documento sirven para:

- comprobar que el sistema registra órdenes e historiales;
- verificar que HU-11 permite calcular tiempos técnicos;
- probar el funcionamiento del comando de evaluación de HU-17;
- identificar las limitaciones actuales del conjunto disponible.

No deben interpretarse como estadísticas operacionales representativas del
negocio ni como evidencia para validar un modelo predictivo.

**Decisión actual: NO ENTRENAR NI INTEGRAR UN MODELO PREDICTIVO.**

---

## 3. Cantidad de datos disponibles

Se ejecutó una revisión de los registros existentes en el entorno local de
desarrollo.

| Indicador | Resultado |
| --- | ---: |
| Órdenes registradas | 4 |
| Órdenes finalizadas | 0 |
| Órdenes con historial de estados | 4 |
| Órdenes con informe técnico | 2 |
| Historiales con tiempo calculable | 4 |
| Casos actualmente utilizables para entrenar ML | 0 |

Los cuatro historiales permiten efectuar el cálculo técnico de tiempos.

Sin embargo, ninguna orden está finalizada y los registros corresponden al
proceso de desarrollo y pruebas. Por ambas razones, no existe actualmente un
conjunto de entrenamiento válido para evaluar la utilidad del modelo en el
negocio.

---

## 4. Distribución de los registros de prueba

### Estados

| Estado | Cantidad |
| --- | ---: |
| Ingresado | 1 |
| Diagnóstico | 3 |

### Tipos de equipo

| Tipo de equipo | Cantidad |
| --- | ---: |
| Celular | 3 |
| Notebook | 1 |

Estas distribuciones describen únicamente los cuatro registros de prueba.

No permiten concluir que los celulares sean el tipo de equipo predominante en
las operaciones reales de Martini Cell ni describir los tiempos habituales de
atención del negocio.

---

## 5. Tiempo técnico calculado

Los cuatro historiales permiten calcular el tiempo técnico acumulado mediante
la lógica desarrollada en HU-11.

En la ejecución del comando del 25-09-2026 se obtuvo:

- Tiempo técnico acumulado mínimo: 0,00 horas.
- Tiempo técnico acumulado máximo: 40,74 horas.

Estos tiempos corresponden a órdenes todavía abiertas. Por lo tanto, pueden
aumentar mientras las órdenes permanezcan en etapas técnicas.

La diferencia respecto de una consulta anterior, que mostró un máximo de
40,26 horas, se explica porque el tiempo de una etapa técnica activa continúa
acumulándose.

Estos resultados verifican el funcionamiento del cálculo de tiempos, pero NO
constituyen tiempos finales de reparaciones reales.

---

## 6. Calidad, completitud y consistencia

La ejecución del comando de evaluación informó:

| Comprobación | Resultado |
| --- | ---: |
| Historiales válidos para el cálculo de tiempo | 4 |
| Historiales inválidos detectados | 0 |
| Tipo de equipo faltante | 0 |
| Marca faltante | 0 |
| Modelo faltante | 0 |

Estos resultados corresponden exclusivamente a los registros actuales de
prueba.

Que un historial sea técnicamente calculable no garantiza que el registro sea
representativo de una reparación real ni que reúna todas las condiciones
necesarias para entrenamiento predictivo.

Antes de incorporar un caso a un conjunto futuro deberán verificarse:

- procedencia operacional real del registro;
- finalización efectiva del trabajo técnico;
- historial de estados íntegro y consistente;
- tiempo técnico final calculable;
- disponibilidad y calidad de las variables de entrada;
- ausencia de información personal en el conjunto preparado para ML;
- disponibilidad de las variables al momento en que se realizaría la predicción.

Una orden marcada como finalizada no será automáticamente considerada un caso
válido de entrenamiento. También deberá comprobarse que representa una
intervención técnica pertinente para el objetivo de estimación.

---

## 7. Privacidad y anonimización

La futura evaluación deberá utilizar un conjunto preparado específicamente
para Machine Learning, sin identificadores directos de clientes ni equipos.

Se excluirán, entre otros:

- nombre del cliente;
- RUT;
- teléfono;
- correo electrónico;
- IMEI;
- número de serie;
- código de seguimiento;
- fotografías;
- otros identificadores personales innecesarios.

Los campos de texto libre deberán revisarse antes de utilizarlos, debido a que
podrían contener accidentalmente información personal.

Se priorizarán inicialmente variables estructuradas que puedan anonimizarse
adecuadamente.

El comando desarrollado en esta etapa muestra resultados agregados y
diagnósticos técnicos. No exporta un conjunto de entrenamiento ni realiza
entrenamiento de modelos.

---

## 8. Limitaciones y posibles sesgos

### Procedencia de los datos

Los registros actuales fueron utilizados durante el desarrollo y las pruebas
del sistema. No forman un conjunto histórico operacional validado.

Esta es la principal limitación para evaluar un modelo que pretenda funcionar
sobre reparaciones reales.

### Tamaño de muestra

Existen solamente cuatro órdenes.

Una muestra de este tamaño no permite medir de manera confiable la capacidad
de generalización de un modelo.

### Ausencia de tiempos finales

Ninguna orden está finalizada, por lo que no existen tiempos técnicos
definitivos que puedan emplearse como variable objetivo.

### Diversidad de casos

La base de prueba contiene tres celulares y un notebook.

Esa distribución no permite evaluar el comportamiento de una estimación frente
a los distintos tipos de reparaciones del negocio.

### Riesgo de fuga de información

No deberán utilizarse como entradas variables que solo se conocen después
de completada la reparación, porque revelarían información sobre el resultado
que se intenta predecir.

---

## 9. Variable objetivo futura

La variable objetivo propuesta será:

**Tiempo técnico final de reparación, expresado en horas.**

Se calculará a partir del historial de estados, reutilizando la lógica de
HU-11.

Solo se considerarán registros de intervenciones técnicas reales y finalizadas
cuyo historial sea válido.

El tiempo de espera por autorización, repuestos o retiro no deberá confundirse
con el tiempo técnico.

---

## 10. Posibles variables de entrada

Las variables deberán corresponder exclusivamente a información disponible
en el momento en que se pretenda generar la estimación.

Entre las candidatas se encuentran:

- tipo de equipo;
- marca;
- modelo normalizado;
- características estructuradas de la reparación disponibles previamente;
- dificultad técnica registrada por el técnico, cuando corresponda.

La selección definitiva dependerá de la calidad y disponibilidad de los datos
operacionales reales.

No se utilizarán como variables predictoras el tiempo técnico final, el
resultado definitivo de la reparación ni información futura que no estaba
disponible al momento de estimar.

---

## 11. Línea base propuesta

Antes de entrenar cualquier modelo se establecerá una línea base simple:

**Mediana del tiempo técnico final del conjunto de entrenamiento.**

La línea base predecirá ese mismo valor para los casos del conjunto de
evaluación.

La mediana se calculará únicamente con datos de entrenamiento, evitando
incorporar información del conjunto de evaluación.

Esta línea base todavía no puede calcularse de manera útil con los registros
actuales, porque no existen casos operacionales reales y finalizados
suficientes.

---

## 12. Métricas propuestas

### MAE — Error Absoluto Medio

Será la métrica principal y se expresará en horas.

Permitirá interpretar la diferencia absoluta promedio entre el tiempo
estimado y el tiempo técnico final real.

### RMSE — Raíz del Error Cuadrático Medio

Se utilizará como métrica complementaria para observar con mayor sensibilidad
los errores grandes.

No se utilizará MAPE como métrica principal, debido a que pueden existir
tiempos iguales o cercanos a cero.

Actualmente no se reportan valores de MAE o RMSE de un modelo, ya que no se ha
ejecutado ningún entrenamiento ni evaluación predictiva.

---

## 13. Condición inicial para reevaluar los datos

Como criterio operativo inicial del proyecto, se propone volver a examinar la
viabilidad del experimento al disponer de al menos:

**30 casos de reparaciones reales, finalizadas, válidas y anonimizadas.**

Este número es un umbral inicial para revisar nuevamente el conjunto, no una
garantía de suficiencia estadística ni una autorización automática para
entrenar o integrar un modelo.

Al alcanzar ese umbral deberán revisarse otra vez:

- procedencia real de los registros;
- cantidad efectiva de casos elegibles;
- diversidad de equipos y reparaciones;
- completitud de variables;
- consistencia de historiales;
- valores faltantes y extremos;
- representatividad y posibles sesgos.

Si la calidad continúa siendo insuficiente, el experimento se postergará.

Los registros de desarrollo y pruebas no deberán sumarse a los casos
operacionales reales para alcanzar artificialmente ese mínimo.

---

## 14. Separación de datos y reproducibilidad

Cuando se disponga de datos suficientes se definirá una separación adecuada
entre entrenamiento y evaluación.

Se considerará validación cruzada cuando las características y el volumen del
conjunto lo permitan.

Con un histórico mayor se evaluará una separación temporal, utilizando casos
anteriores para entrenar y casos posteriores para evaluar.

Las ejecuciones utilizarán una semilla fija cuando corresponda:

**random_state = 42**

Se documentarán las variables, los criterios de exclusión, el método de
separación, la línea base, las métricas y los resultados obtenidos.

Estas actividades están definidas metodológicamente, pero todavía no se han
ejecutado sobre un conjunto operacional apto.

---

## 15. Modelos candidatos

Una vez comprobada la suficiencia de los datos podrán evaluarse algoritmos de
regresión, por ejemplo:

- regresión lineal;
- árbol de regresión;
- Random Forest Regressor.

La selección no dependerá de la complejidad del algoritmo, sino de los
resultados reproducibles y de su utilidad frente a la línea base.

Actualmente no se ha seleccionado ni entrenado un modelo.

---

## 16. Criterio de utilidad

Un modelo no deberá integrarse únicamente porque pueda entrenarse.

Como criterio inicial de evaluación se propone exigir una reducción del MAE de
al menos un 10 % respecto de la línea base.

La mejora deberá ser suficientemente estable y no depender únicamente de unos
pocos casos particulares.

Este porcentaje es un criterio propuesto para el experimento del proyecto; no
constituye una garantía universal de desempeño.

Además, antes de integrar un modelo deberán revisarse su comportamiento ante
los distintos tipos de casos, sus limitaciones y la posibilidad de mantenerlo
actualizado.

---

## 17. Condiciones para integrar la funcionalidad

La estimación predictiva solo podrá incorporarse a Martini Cell si:

1. Se cuenta con un conjunto adecuado de casos operacionales reales.
2. Los registros representan reparaciones técnicas finalizadas.
3. Los datos poseen calidad y diversidad suficientes.
4. El conjunto utilizado está debidamente anonimizado.
5. Se calcula una línea base sin fuga de información.
6. Se realiza una evaluación reproducible.
7. El modelo demuestra una mejora medible y útil.
8. El resultado puede comunicarse responsablemente al técnico.

Si estas condiciones no se cumplen, no se integrará el modelo.

---

## 18. Presentación responsable del resultado

Si en el futuro se integra la estimación, deberá mostrarse como un valor
aproximado y no como un compromiso de tiempo de entrega.

Ejemplo ilustrativo de presentación:

**Tiempo técnico estimado: aproximadamente 4 horas.**

El valor anterior es únicamente un ejemplo de interfaz; NO corresponde al
resultado de un modelo entrenado.

La interfaz deberá aclarar que la estimación:

- se basa en casos históricos;
- puede presentar errores;
- no reemplaza el criterio profesional del técnico;
- no constituye diagnóstico ni decisión automática;
- no equivale necesariamente al tiempo total de entrega al cliente.

---

## 19. Relación con los criterios de aceptación

### CA-01 — Evaluación de los datos

Se realizó una evaluación inicial del conjunto de desarrollo y pruebas,
incluyendo cantidad, completitud estructurada, consistencia de historiales y
distribución de casos.

Queda pendiente una evaluación equivalente sobre datos operacionales reales
cuando estos estén disponibles.

### CA-02 — Línea base y métricas

Se definieron metodológicamente la mediana del tiempo técnico como línea base,
MAE como métrica principal y RMSE como métrica complementaria.

No se reportan resultados numéricos de predicción porque actualmente no existe
un conjunto apto.

### CA-03 — Separación y reproducibilidad

Se definió una metodología reproducible y la semilla `random_state = 42`.

La evaluación predictiva todavía no puede ejecutarse de forma válida por
insuficiencia de datos operacionales reales y finalizados.

### CA-04 — Integración condicionada

Se aplica la condición establecida en la historia de usuario: al no disponer
de evidencia suficiente, el modelo no se entrena ni se integra actualmente.

La decisión y sus fundamentos quedan documentados.

### CA-05 — Uso como apoyo

Se establece que cualquier estimación futura deberá presentarse solo como
apoyo al técnico, nunca como diagnóstico, promesa o decisión automática.

No existe actualmente una predicción integrada en la interfaz.

---

## 20. Resultado y conclusión

La revisión de HU-17 confirma que Martini Cell cuenta actualmente con cuatro
órdenes utilizadas para desarrollo y pruebas, ninguna de ellas finalizada.

El comando de evaluación permitió comprobar el cálculo de tiempos, la
consistencia de los historiales y la generación de un diagnóstico agregado,
pero esos registros no constituyen evidencia operacional suficiente para
validar Machine Learning.

Por lo tanto:

**Se decide no entrenar ni integrar actualmente un modelo predictivo de
estimación del tiempo técnico.**

Se conserva una metodología documentada para repetir la evaluación cuando se
disponga de un histórico suficiente de reparaciones reales, finalizadas,
consistentes y anonimizadas.

Esta decisión permite desarrollar HU-17 sin presentar resultados artificiales
como evidencia de utilidad real y sin incorporar una funcionalidad predictiva
que todavía no ha demostrado aportar valor al negocio.