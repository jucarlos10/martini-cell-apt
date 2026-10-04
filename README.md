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

🚧 MVP en desarrollo. El backend Django y el frontend Vue están integrados en
`main`; los PR hacia esa rama ejecutan pruebas del backend y compilan el
frontend en GitHub Actions. Esto no sustituye la validación funcional con
Marcos. El avance de cada historia se registra en el
[tablero Kanban](https://github.com/users/jucarlos10/projects/1).

## Documentación

La [guía de cambios y estado del Kanban](docs/registro-de-cambios-y-tablero-2026-09-30.md)
explica qué se integró, por qué se ajustó y qué sigue en pruebas. La
[preparación de datos y conexión al host](docs/preparacion-dataset-y-host-2026-10-04.md)
resume el estado del dataset y los pasos para desplegar. Los demás
documentos técnicos están en [`docs/`](docs/) y las evidencias académicas
de la primera fase en [`fase 1/`](fase%201/).

## Estructura del repositorio

La estructura actual es:

- [`backend/`](backend/) — API Django, modelos, migraciones y pruebas.
- [`frontend/`](frontend/) — Aplicación Vue y Vite.
- [`docs/`](docs/) — Decisiones y evidencias técnicas.
- [`fase 1/`](fase%201/) — Evidencias académicas de la primera fase.
- [`.github/workflows/`](.github/workflows/) — Pruebas y compilación automáticas.

## Desarrollo local

Se requieren Python 3.12, PostgreSQL y Node.js 20 (versiones usadas en los
flujos de GitHub Actions). Configura una base de datos y un usuario local
de PostgreSQL, copia `backend/.env.example` a `backend/.env` y reemplaza los
valores de ejemplo, en particular la contraseña y `DJANGO_SECRET_KEY`.
El archivo `.env` está excluido de Git.

En una terminal, desde la raíz del repositorio:

```bash
python -m pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

En otra terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite sirve la interfaz en `http://localhost:5173` y redirige `/api` a
`http://127.0.0.1:8000` durante el desarrollo. Para usar otro backend local,
define `API_PROXY_TARGET` en el entorno del frontend. Las verificaciones que
corren en cada PR son `python manage.py test --noinput` dentro de `backend/`
y `npm run build` dentro de `frontend/`.

## Versionado

El proyecto utilizará Git y GitHub para mantener el control de versiones del código fuente y de la documentación relevante.

Las versiones funcionales del MVP serán identificadas mediante releases a medida que avance el desarrollo.
