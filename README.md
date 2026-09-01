# Martini Cell - Proyecto APT

## Plataforma web inteligente para la gestión y trazabilidad de servicios técnicos

Proyecto desarrollado en el contexto de la Asignatura de Portafolio de Título (APT) de la carrera de Ingeniería en Informática de Duoc UC, sede Viña del Mar.

## Descripción

Martini Cell es una PYME chilena dedicada al diagnóstico y reparación de celulares y computadores.

Actualmente, parte de la información relacionada con la recepción de equipos, antecedentes de clientes, estados de reparación, precios y control operativo se encuentra distribuida entre registros en papel, planillas, mensajería y organización física dentro del local.

El proyecto busca desarrollar y validar un Producto Mínimo Viable (MVP) de una plataforma web que permita centralizar la gestión de los servicios técnicos y mantener la trazabilidad de cada reparación desde el ingreso del equipo hasta su cierre.

## Objetivo

Proporcionar a Martini Cell una plataforma web que permita centralizar y mantener la trazabilidad de la gestión de sus servicios técnicos, apoyando el registro y seguimiento de clientes, equipos, órdenes de reparación, estados, tiempos, repuestos, costos, precios, márgenes y garantías.

La solución también busca apoyar la toma de decisiones mediante indicadores operacionales y un índice de viabilidad basado en reglas explicables.

## Alcance inicial del MVP

El MVP contempla, entre otras funcionalidades:

- Gestión de clientes y equipos.
- Registro de órdenes de reparación.
- Seguimiento de estados e historial de reparaciones.
- Registro de diagnósticos, reparaciones y evidencias.
- Registro de tiempos técnicos y tiempos de espera.
- Gestión de repuestos, costos, precios, márgenes y garantías.
- Consulta del estado de una reparación mediante código.
- Visualización de indicadores operacionales.
- Índice de viabilidad basado en reglas explicables.

Adicionalmente, se evaluará de manera experimental la factibilidad de utilizar Machine Learning para estimar el tiempo técnico de reparación, condicionado a la cantidad y calidad de los datos recopilados.

## Metodología

El proyecto será desarrollado utilizando Kanban como metodología de gestión del trabajo.

Las actividades serán organizadas y priorizadas mediante un backlog y avanzarán a través de diferentes estados del flujo de trabajo hasta cumplir los criterios establecidos en la Definition of Done (DoD).

El desarrollo de la solución será incremental y las funcionalidades completadas podrán agruparse en releases durante la construcción del MVP.

## Equipo

- Juan Valencia
- Oscar Contreras
- Rafael Muñoz

### Contraparte

- Marcos Martini — Martini Cell

## Estado del proyecto

🚧 En desarrollo — Fase 1: Definición y diseño.

## Documentación

La documentación generada durante el proyecto será incorporada progresivamente al directorio `/docs`.

La documentación se organizará de acuerdo con las distintas fases del Proyecto APT.

## Estructura del repositorio

La estructura del repositorio evolucionará durante el desarrollo del proyecto.

Inicialmente se consideran los siguientes directorios:

- `/docs` — Documentación académica y técnica.
- `/src` — Código fuente de la plataforma.
- `/tests` — Pruebas del sistema.
- `/database` — Recursos relacionados con el modelo y estructura de datos.
- `/data` — Datos anonimizados utilizados durante el proyecto.

## Versionado

El proyecto utilizará Git y GitHub para mantener el control de versiones del código fuente y de la documentación relevante.

Las versiones funcionales del MVP serán identificadas mediante releases a medida que avance el desarrollo.
