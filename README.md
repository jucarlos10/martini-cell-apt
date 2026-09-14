# Martini Cell — Prototipo Frontend

**Plataforma web para la gestión y trazabilidad de servicios técnicos en Martini Cell**

## Objetivo de esta versión

Este avance representa la **capa frontend/prototipo navegable**. No contiene backend, API, PostgreSQL, JWT real ni lógica de negocio definitiva.

Los datos son ficticios y se cargan desde `src/mockStore.js`. Algunas acciones guardan cambios en `localStorage` para que el prototipo se sienta interactivo sin agregar infraestructura innecesaria en esta etapa.

## Pantallas incluidas

- Inicio de sesión demo.
- Panel principal.
- Lista y filtro de órdenes.
- Nueva orden en 3 pasos.
- Detalle de reparación con resumen, diagnóstico, línea de tiempo, autorización, evidencias simuladas, costos, garantía e índice de viabilidad.
- Clientes y equipos.
- Repuestos y proveedores.
- Garantías.
- Indicadores operacionales simulados.
- Usuarios y roles.
- Consulta pública mediante código.

## Fuera del alcance de esta versión

- Persistencia en base de datos.
- API REST.
- Autenticación y seguridad reales.
- Carga real de archivos.
- Cálculo real del índice de viabilidad.
- Machine Learning.
- Envío de mensajes o aprobación de presupuesto por parte del cliente.

## Ejecutar con Docker

Desde la carpeta del proyecto:

```bash
docker compose up --build
```

Abrir:

```text
http://localhost:5173

```

## Ejecutar sin Docker

Requiere Node.js 20+:

```bash
npm install
npm run dev
```

## Usuarios demo

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | admin | Admin123! |
| Técnico | tecnico | Tecnico123! |
| Ayudante | ayudante | Ayudante123! |

Consulta pública demo: `MC-1047`.