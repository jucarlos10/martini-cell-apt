<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const code = ref('')
const data = ref(null)
const error = ref('')
const loading = ref(false)

const notFoundMessage = 'No se encontró una orden con ese código. Revísalo e inténtalo nuevamente.'
let currentRequest = 0
let controller = null

// Una consulta pública no utiliza ni envía tokens de la sesión interna.
watch(code, () => {
  currentRequest += 1
  if (controller) controller.abort()
  controller = null
  data.value = null
  error.value = ''
  loading.value = false
})

function formatDate(value) {
  if (!value) return 'No disponible'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'No disponible'
  return date.toLocaleString('es-CL', { dateStyle: 'short', timeStyle: 'short' })
}

async function search() {
  const normalizedCode = code.value.trim().toUpperCase()
  const requestId = ++currentRequest
  if (controller) controller.abort()
  controller = null
  data.value = null
  error.value = ''

  if (!/^MC-[A-F0-9]{12}$/.test(normalizedCode)) {
    error.value = notFoundMessage
    loading.value = false
    return
  }

  const requestController = new AbortController()
  controller = requestController
  loading.value = true

  try {
    const response = await fetch(
      `/api/orders/public/${encodeURIComponent(normalizedCode)}/`,
      {
        method: 'GET',
        headers: { Accept: 'application/json' },
        cache: 'no-store',
        signal: requestController.signal,
      },
    )

    if (requestId !== currentRequest) return

    if (response.status === 404) {
      error.value = notFoundMessage
      return
    }
    if (response.status === 429) {
      error.value = 'Se alcanzó el límite de consultas. Inténtalo más tarde.'
      return
    }
    if (!response.ok) {
      error.value = 'No fue posible consultar el estado. Inténtalo nuevamente.'
      return
    }

    const result = await response.json()
    if (requestId !== currentRequest) return

    // Solo presentamos los campos públicos definidos por la API de Django.
    if (
      result?.tracking_code !== normalizedCode ||
      typeof result?.status !== 'string' ||
      typeof result?.status_display !== 'string'
    ) {
      error.value = 'No fue posible interpretar la respuesta. Inténtalo nuevamente.'
      return
    }
    data.value = {
      tracking_code: result.tracking_code,
      status_display: result.status_display,
      updated_at: result.updated_at,
    }
  } catch (err) {
    if (requestId === currentRequest && err?.name !== 'AbortError') {
      error.value = 'No fue posible conectar con el servicio. Inténtalo nuevamente.'
    }
  } finally {
    if (requestId === currentRequest) {
      loading.value = false
      controller = null
    }
  }
}

onBeforeUnmount(() => {
  currentRequest += 1
  if (controller) controller.abort()
})
</script>

<template>
  <main class="min-vh-100 py-4 px-3" style="background: #eef4f8">
    <div class="mobile-public">
      <header class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <div class="fw-bold fs-5" style="color: var(--mc-navy)">
          <i class="bi bi-tools me-2" aria-hidden="true"></i>MARTINI CELL
        </div>
        <router-link to="/login" class="small">Iniciar sesión</router-link>
      </header>

      <section class="mc-card p-4 mb-3" aria-labelledby="tracking-heading">
        <h1 id="tracking-heading" class="h4 fw-bold">Consulta tu reparación</h1>
        <p class="text-muted">Ingresa el código de seguimiento entregado al recibir tu equipo.</p>

        <form class="row g-2 align-items-end" @submit.prevent="search">
          <div class="col-12 col-sm-8">
            <label for="tracking-code" class="form-label">Código de seguimiento</label>
            <input
              id="tracking-code"
              v-model="code"
              type="text"
              class="form-control"
              placeholder="MC-XXXXXXXXXXXX"
              autocomplete="off"
              autocapitalize="characters"
              :aria-invalid="Boolean(error)"
              :disabled="loading"
              required
            >
          </div>
          <div class="col-12 col-sm-4">
            <button class="btn btn-primary w-100" type="submit" :disabled="loading || !code.trim()">
              <span v-if="loading" class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>
              {{ loading ? 'Consultando...' : 'Consultar' }}
            </button>
          </div>
        </form>

        <div v-if="error" class="alert alert-warning mt-3 mb-0" role="alert">{{ error }}</div>
      </section>

      <section v-if="data" class="mc-card p-4" aria-labelledby="tracking-result-heading" aria-live="polite">
        <h2 id="tracking-result-heading" class="h5 fw-bold mb-3">Estado de tu reparación</h2>
        <div class="small text-muted">Código de seguimiento</div>
        <div class="fw-semibold text-break">{{ data.tracking_code }}</div>
        <div class="small text-muted mt-3">Estado actual</div>
        <div class="fs-4 fw-bold text-primary">{{ data.status_display }}</div>
        <div class="small text-muted mt-2">Última actualización: {{ formatDate(data.updated_at) }}</div>
        <div class="alert alert-light border small mt-4 mb-0">
          Para más información, contacta directamente a Martini Cell.
        </div>
      </section>

      <p class="text-center text-muted small mt-4">
        Esta consulta pública no muestra datos personales, fotografías, costos internos ni diagnósticos.
      </p>
    </div>
  </main>
</template>
