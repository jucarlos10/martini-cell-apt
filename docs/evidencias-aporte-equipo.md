# Evidencias de aporte individual del equipo

## Proyecto APT — Martini Cell

Este documento reúne evidencias verificables dentro de GitHub que permiten identificar el aporte individual de los integrantes del equipo al Proyecto APT Martini Cell.

Su objetivo es respaldar el **Indicador de Evaluación 9** de la Fase 2: generar evidencias claras dentro del repositorio que permitan identificar la equidad en el trabajo y la participación de cada estudiante.

> **Criterio de elaboración:** las evidencias seleccionadas son representativas y no exhaustivas. Se incluyen únicamente aportes que pueden verificarse mediante repositorios, ramas, commits, pull requests o documentación disponible en GitHub.

---

## 1. Identificación del equipo

| Integrante | Usuario GitHub identificado | Evidencia principal |
|---|---|---|
| Rafael Muñoz | `RafaelMnHn` | Repositorio de origen y prototipo frontend inicial |
| Oscar Contreras | `osccontreras-web` | Desarrollo backend/frontend, pruebas, garantías, integraciones y despliegue |
| Juan Valencia | `jucarlos10` | Gestión del repositorio, documentación, CI/CD, seguridad, UX, despliegue y validaciones |

Repositorio de trabajo del equipo:

- [jucarlos10/martini-cell-apt](https://github.com/jucarlos10/martini-cell-apt)

El repositorio actual conserva en GitHub su relación de **fork** respecto del repositorio original:

- [RafaelMnHn/martini-cell-apt](https://github.com/RafaelMnHn/martini-cell-apt)

---

# 2. Rafael Muñoz — `RafaelMnHn`

## Aporte principal

Rafael participó en la etapa inicial del proyecto mediante la creación del repositorio original y el desarrollo del **prototipo navegable inicial del frontend** de Martini Cell.

El prototipo fue desarrollado con Vue/Vite y permitió representar tempranamente la navegación y las principales pantallas del sistema antes de integrar persistencia real, autenticación segura y API backend.

## Evidencias verificables

### Repositorio de origen

El repositorio actual del proyecto figura en GitHub como fork de:

- [RafaelMnHn/martini-cell-apt](https://github.com/RafaelMnHn/martini-cell-apt)

Esto permite verificar que el proyecto comenzó desde un repositorio creado bajo la cuenta de Rafael.

### Commits del repositorio inicial

- [Initial commit — eb92b36](https://github.com/RafaelMnHn/martini-cell-apt/commit/eb92b367a1d48f36063aad19088c94048ac2dadd)
- [Creación del repositorio y descripción del proyecto — 464314d](https://github.com/RafaelMnHn/martini-cell-apt/commit/464314d86abefe971b8158ffaa63cb8971248abd)

### Prototipo frontend inicial

La rama `feature/frontend` conserva commits realizados por `RafaelMnHn`:

- `3f41c54` — **feat(frontend): agregar prototipo navegable inicial de Martini Cell**
- `521c169` — Ignorar README local
- `319624c` — Integración de `main` con `feature/frontend`
- `7389af5` — Ajuste en README
- `ce157fe` — Definición de alcance del entregable

Como evidencia de revisión del prototipo se conserva:

- [PR #18 — Prototipo navegable del frontend para revisión de las historias](https://github.com/jucarlos10/martini-cell-apt/pull/18)

El PR registra un prototipo Vue/Vite con vistas de navegación interna, órdenes, clientes, repuestos, garantías, indicadores y consulta pública. El propio alcance del PR declara que correspondía a una versión de demostración y diseño, previa a la integración con datos reales y backend.

## Síntesis del aporte

- Creación del repositorio original.
- Definición inicial y descripción del proyecto.
- Construcción del prototipo navegable frontend.
- Diseño inicial de navegación y principales módulos visuales.
- Representación inicial de órdenes, clientes, repuestos, garantías, indicadores y consulta pública.
- Definición del alcance del prototipo para revisión funcional.

---

# 3. Oscar Contreras — `osccontreras-web`

## Aporte principal

Oscar participó ampliamente en la implementación funcional del sistema, tanto en backend como frontend, además de pruebas automatizadas, integración de módulos, seguridad, garantías, comunicaciones, despliegue e iteraciones finales del producto.

## Evidencias representativas

### Indicadores, inteligencia y evaluación de datos

- [PR #37 — HU-16: Consultar indicadores e índice de viabilidad](https://github.com/jucarlos10/martini-cell-apt/pull/37)
- [PR #38 — HU-17: Evaluar la estimación del tiempo técnico](https://github.com/jucarlos10/martini-cell-apt/pull/38)

### Pruebas e integración

- [PR #39 — TEC-01: Incorporar pruebas automatizadas del backend](https://github.com/jucarlos10/martini-cell-apt/pull/39)
- [PR #40 — TEC-02: Completar integración Vue con API Django](https://github.com/jucarlos10/martini-cell-apt/pull/40)

### Inventario, garantías y trazabilidad

- [PR #64 — HU-33: Buscar y filtrar garantías](https://github.com/jucarlos10/martini-cell-apt/pull/64)
- [PR #68 — HU-22: Ingresar una solicitud de garantía](https://github.com/jucarlos10/martini-cell-apt/pull/68)
- [PR #69 — HU-23: Resolver solicitud de garantía](https://github.com/jucarlos10/martini-cell-apt/pull/69)
- [PR #72 — HU-24: Corregir un repuesto registrado en una orden](https://github.com/jucarlos10/martini-cell-apt/pull/72)
- [PR #76 — HU-25: Anular el uso de un repuesto en una orden](https://github.com/jucarlos10/martini-cell-apt/pull/76)

### Seguridad y control de acceso

- [PR #77 — HU-26: Implementar autorización por perfiles de usuario](https://github.com/jucarlos10/martini-cell-apt/pull/77)
- [PR #81 — HU-27: Registrar cambios sensibles de una orden de servicio](https://github.com/jucarlos10/martini-cell-apt/pull/81)

### Chat, WhatsApp y notificaciones

- [PR #99 — HU-35: Chat online asociado a la orden](https://github.com/jucarlos10/martini-cell-apt/pull/99)
- [PR #101 — HU-36: Notificaciones de respuestas del chat](https://github.com/jucarlos10/martini-cell-apt/pull/101)
- [PR #103 — HU-37: Notificaciones automáticas por cambio de estado](https://github.com/jucarlos10/martini-cell-apt/pull/103)
- [PR #105 — TEC-04: Integrar WhatsApp Cloud API](https://github.com/jucarlos10/martini-cell-apt/pull/105)
- [PR #107 — HU-38: Iniciar conversación por número de orden](https://github.com/jucarlos10/martini-cell-apt/pull/107)

### Correo, dominio y mejoras finales

- [PR #111 — Integrar envío de correos con Resend](https://github.com/jucarlos10/martini-cell-apt/pull/111)
- [PR #112 — Enviar cambios de estado por Resend](https://github.com/jucarlos10/martini-cell-apt/pull/112)
- [PR #113 — Enviar comprobante de recepción por Resend](https://github.com/jucarlos10/martini-cell-apt/pull/113)
- [PR #114 — Enviar notificaciones de chat por Resend](https://github.com/jucarlos10/martini-cell-apt/pull/114)
- [PR #115 — Usar dominio público en notificaciones](https://github.com/jucarlos10/martini-cell-apt/pull/115)
- [PR #117 — Accesos rápidos de chat y garantía en órdenes](https://github.com/jucarlos10/martini-cell-apt/pull/117)
- [PR #118 — Permitir clientes sin RUT y documentos extranjeros](https://github.com/jucarlos10/martini-cell-apt/pull/118)
- [PR #119 — Agregar código interno de cliente](https://github.com/jucarlos10/martini-cell-apt/pull/119)

## Síntesis del aporte

- Desarrollo e integración backend/frontend.
- Implementación de indicadores e índice de viabilidad.
- Evaluación responsable de factibilidad de Machine Learning.
- Automatización de pruebas y regresión.
- Gestión avanzada de garantías y repuestos.
- Autorización por roles y auditoría de cambios sensibles.
- Chat asociado a órdenes.
- Integración de WhatsApp Cloud API.
- Integración de correos mediante Resend.
- Configuración del dominio público en notificaciones.
- Mejoras de identificación y búsqueda de clientes.
- Apoyo en despliegue y validación productiva.

---

# 4. Juan Valencia — `jucarlos10`

## Aporte principal

Juan participó en la administración del repositorio del equipo y en actividades de documentación, revisión, CI/CD, configuración de seguridad, preparación de datos, despliegue, experiencia de usuario y validaciones posteriores del producto.

## Evidencias representativas

### Gestión y documentación del repositorio

- [PR #19 — Agregar plantilla de revisión de PR](https://github.com/jucarlos10/martini-cell-apt/pull/19)
- [PR #66 — Actualizar README al estado actual del MVP](https://github.com/jucarlos10/martini-cell-apt/pull/66)
- [PR #80 — Guía de cambios legible para el equipo](https://github.com/jucarlos10/martini-cell-apt/pull/80)

### Seguridad y calidad del proceso

- [PR #45 — Configurar DEBUG y ALLOWED_HOSTS desde entorno](https://github.com/jucarlos10/martini-cell-apt/pull/45)
- [PR #56 — Ejecutar pruebas de Django en cada PR](https://github.com/jucarlos10/martini-cell-apt/pull/56)
- [PR #57 — Compilar frontend Vue en cada PR](https://github.com/jucarlos10/martini-cell-apt/pull/57)
- [PR #65 — Hacer atómica la actualización y auditoría de clientes](https://github.com/jucarlos10/martini-cell-apt/pull/65)
- [PR #75 — Proteger costos de repuestos para perfiles sin acceso financiero](https://github.com/jucarlos10/martini-cell-apt/pull/75)

### Datos y preparación de despliegue

- [PR #82 — Preparar dataset y configuración inicial para conexión al host](https://github.com/jucarlos10/martini-cell-apt/pull/82)
- [PR #83 — Preparar contrato y validación local del dataset para Oscar](https://github.com/jucarlos10/martini-cell-apt/pull/83)
- [PR #84 — Preparar la conexión al host](https://github.com/jucarlos10/martini-cell-apt/pull/84)
- [PR #85 — Comprobar el host antes de conectar el dominio](https://github.com/jucarlos10/martini-cell-apt/pull/85)
- [PR #88 — Registrar despliegue Vercel/Railway y verificar fotos persistentes](https://github.com/jucarlos10/martini-cell-apt/pull/88)

### Experiencia de usuario y validación del flujo

- [PR #89 — Permitir corregir el código durante la consulta pública](https://github.com/jucarlos10/martini-cell-apt/pull/89)
- [PR #91 — Comprobante y entrega del seguimiento con precio informado al ingreso](https://github.com/jucarlos10/martini-cell-apt/pull/91)
- [PR #109 — Limitar envíos y consultas del chat público](https://github.com/jucarlos10/martini-cell-apt/pull/109)
- [PR #110 — Mejorar diseño y uso del acceso y seguimiento público](https://github.com/jucarlos10/martini-cell-apt/pull/110)
- [PR #120 — Evitar error de sesión al registrar y entregar comprobantes](https://github.com/jucarlos10/martini-cell-apt/pull/120)
- [PR #121 — Hacer visible la trazabilidad al crear y abrir órdenes](https://github.com/jucarlos10/martini-cell-apt/pull/121)
- [PR #122 — Probar recorrido completo de trazabilidad y documentar ensayo en host](https://github.com/jucarlos10/martini-cell-apt/pull/122)

## Síntesis del aporte

- Administración y organización del repositorio.
- Documentación técnica y de proceso.
- Automatización de pruebas y compilación mediante GitHub Actions.
- Configuración de seguridad y variables de entorno.
- Mejoras de atomicidad y control de datos sensibles.
- Preparación y validación estructural de datasets.
- Preparación y documentación de despliegue.
- Mejoras de experiencia de usuario.
- Validación del seguimiento y trazabilidad del flujo completo.

---

# 5. Evidencia de colaboración y complementariedad

Los aportes registrados muestran una distribución complementaria del trabajo:

| Área | Rafael | Oscar | Juan |
|---|:---:|:---:|:---:|
| Prototipo frontend inicial | ✓ |  |  |
| Backend funcional |  | ✓ | ✓ |
| Integración frontend/backend |  | ✓ | ✓ |
| Pruebas automatizadas |  | ✓ | ✓ |
| Garantías e inventario |  | ✓ | ✓ |
| Seguridad y permisos |  | ✓ | ✓ |
| Datos / evaluación ML |  | ✓ | ✓ |
| Notificaciones / comunicaciones |  | ✓ | ✓ |
| CI/CD y calidad del repositorio |  | ✓ | ✓ |
| Despliegue y operación |  | ✓ | ✓ |
| Documentación y seguimiento del proyecto | ✓ | ✓ | ✓ |

Esta matriz no pretende medir el aporte únicamente por cantidad de commits o pull requests. La evidencia se utiliza para demostrar participación verificable en distintas etapas del ciclo de vida del proyecto: definición, prototipado, construcción, integración, pruebas, documentación, despliegue y validación.

---

# 6. Relación con el Indicador 9 de la evaluación

La evidencia reunida permite:

1. Identificar a cada integrante mediante su usuario GitHub.
2. Vincular cada integrante con aportes concretos.
3. Consultar directamente commits, ramas y pull requests.
4. Reconocer aportes realizados en distintas etapas del proyecto.
5. Evidenciar que el producto final corresponde a un trabajo colaborativo y evolutivo.

La trazabilidad de GitHub complementa las evidencias académicas y la presentación final del Proyecto APT.
