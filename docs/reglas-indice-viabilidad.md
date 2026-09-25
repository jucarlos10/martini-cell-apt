\# Reglas del Índice de Viabilidad



\## HU-16 — Consultar indicadores e índice de viabilidad



Versión de reglas: \*\*HU16-v1\*\*



\## Objetivo



El índice de viabilidad de Martini Cell busca apoyar al técnico o responsable del servicio en la evaluación de una reparación antes de tomar una decisión.



El resultado se obtiene mediante reglas explicables utilizando información disponible en la orden de servicio.



El índice funciona únicamente como una herramienta de apoyo y \*\*no reemplaza la decisión profesional del técnico\*\*.



\---



\## Puntaje máximo



El índice utiliza cinco factores con un puntaje máximo total de \*\*100 puntos\*\*.



| Factor | Puntaje máximo |

| --- | ---: |

| Dificultad técnica | 20 |

| Disponibilidad de repuestos | 20 |

| Margen estimado | 25 |

| Tiempo técnico | 20 |

| Riesgo de garantía | 15 |

| \*\*Total\*\* | \*\*100\*\* |



\---



\## 1. Dificultad técnica



La dificultad técnica es registrada manualmente por el técnico o responsable de la orden.



| Dificultad | Puntaje |

| --- | ---: |

| Baja | 20 |

| Media | 12 |

| Alta | 5 |



Este factor permite representar la complejidad estimada de la reparación.



\---



\## 2. Disponibilidad de repuestos



La disponibilidad se calcula utilizando los repuestos asociados actualmente a la orden.



| Condición | Puntaje |

| --- | ---: |

| No existen repuestos registrados como necesarios | 20 |

| Todos los repuestos registrados están activos y tienen stock | 20 |

| Existe al menos un repuesto sin stock | 10 |

| Existe al menos un repuesto inactivo | 5 |



\### Consideración



En la versión \*\*HU16-v1\*\*, el sistema utiliza los datos de repuestos disponibles actualmente en la plataforma.



Si la orden todavía no tiene repuestos registrados, el factor no descuenta puntaje.



Esta regla podrá ser refinada en futuras versiones si se incorpora un registro específico de repuestos requeridos antes de realizar la reparación.



\---



\## 3. Margen estimado



El margen se calcula utilizando los datos financieros de la orden.



La fórmula utilizada es:



\*\*Margen estimado = Precio cobrado - Costo directo total\*\*



El porcentaje de margen se calcula como:



\*\*Margen % = (Margen estimado / Precio cobrado) × 100\*\*



El costo directo total considera:



\- costo de repuestos;

\- mano de obra;

\- otros costos directos.



\### Puntaje



| Margen estimado | Puntaje |

| --- | ---: |

| 30 % o superior | 25 |

| Desde 15 % y menor a 30 % | 20 |

| Desde 0 % y menor a 15 % | 12 |

| Margen negativo | 0 |



Si no existe información financiera suficiente para calcular el margen, este factor se considera pendiente.



\---



\## 4. Tiempo técnico



El tiempo técnico se obtiene desde el historial real de estados de la orden, utilizando la misma lógica implementada para el seguimiento de tiempos del sistema.



| Tiempo técnico acumulado | Puntaje |

| --- | ---: |

| Hasta 2 horas | 20 |

| Más de 2 y hasta 6 horas | 15 |

| Más de 6 y hasta 12 horas | 8 |

| Más de 12 horas | 3 |



Si el historial de estados no permite obtener un tiempo válido, este factor se considera pendiente.



\---



\## 5. Riesgo de garantía



El riesgo de garantía es registrado manualmente por el técnico o responsable de la orden.



| Riesgo | Puntaje |

| --- | ---: |

| Bajo | 15 |

| Medio | 9 |

| Alto | 3 |



Este factor representa el nivel de riesgo estimado de que la reparación genere problemas posteriores asociados a garantía.



\---



\## Clasificación del resultado



Cuando los cinco factores poseen información suficiente, sus puntajes se suman.



| Puntaje total | Nivel de viabilidad |

| --- | --- |

| 75 a 100 | Alta |

| 50 a 74 | Media |

| 0 a 49 | Baja |



Ejemplo:



\- Dificultad técnica: 20/20

\- Disponibilidad de repuestos: 20/20

\- Margen estimado: 25/25

\- Tiempo técnico: 3/20

\- Riesgo de garantía: 9/15



\*\*Resultado: 77/100 — Viabilidad Alta\*\*



\---



\## Información insuficiente



El sistema no entrega un puntaje final cuando falta información necesaria para evaluar alguno de los factores obligatorios.



Entre los posibles factores pendientes se encuentran:



\- dificultad técnica;

\- riesgo de garantía;

\- margen estimado;

\- disponibilidad de repuestos;

\- tiempo técnico.



La interfaz informa qué datos están pendientes y permite al usuario dirigirse al lugar correspondiente para completarlos o revisarlos.



\---



\## Explicabilidad



El sistema muestra individualmente:



\- nombre del factor;

\- puntaje obtenido;

\- puntaje máximo;

\- explicación de por qué se asignó ese resultado.



Esto permite conocer cómo se construyó el índice y evita que el resultado sea presentado como una decisión automática sin explicación.



\---



\## Uso del índice



El índice debe interpretarse como una ayuda para evaluar la conveniencia de una reparación.



La decisión final continúa siendo responsabilidad del técnico o responsable de Martini Cell, quien puede considerar antecedentes adicionales que no formen parte de las reglas del sistema.



> El índice es una herramienta de apoyo y no reemplaza la decisión profesional del técnico.
