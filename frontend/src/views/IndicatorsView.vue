<script setup>
import { computed, onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'


function localDateText(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}


const today = new Date()
const firstDayOfMonth = new Date(
  today.getFullYear(),
  today.getMonth(),
  1,
)

const start = ref(localDateText(firstDayOfMonth))
const end = ref(localDateText(today))

const indicators = ref(null)
const loading = ref(false)
const error = ref('')


const statusRows = computed(
  () => indicators.value?.orders_by_status || []
)


const maxCount = computed(() => {
  const counts = statusRows.value.map(
    (item) => Number(item.count || 0)
  )

  return Math.max(1, ...counts)
})


function formatPeriodDate(value) {
  if (!value) return '—'

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)

  if (!match) return value

  return `${match[3]}-${match[2]}-${match[1]}`
}


function formatDuration(seconds) {
  const totalSeconds = Math.max(
    0,
    Math.floor(Number(seconds) || 0)
  )

  const days = Math.floor(
    totalSeconds / 86400
  )

  const hours = Math.floor(
    (totalSeconds % 86400) / 3600
  )

  const minutes = Math.floor(
    (totalSeconds % 3600) / 60
  )

  const parts = []

  if (days) {
    parts.push(`${days} d`)
  }

  if (hours) {
    parts.push(`${hours} h`)
  }

  if (minutes || parts.length === 0) {
    parts.push(`${minutes} min`)
  }

  return parts.join(' ')
}


function apiError(data, fallback) {
  if (!data) return fallback

  if (typeof data.detail === 'string') {
    return data.detail
  }

  return fallback
}


async function loadIndicators() {
  error.value = ''

  if (!start.value || !end.value) {
    error.value = 'Selecciona una fecha inicial y una fecha final.'
    return
  }

  if (start.value > end.value) {
    error.value = (
      'La fecha inicial no puede ser posterior a la fecha final.'
    )
    return
  }

  loading.value = true

  try {
    const query = new URLSearchParams({
      start: start.value,
      end: end.value,
    })

    const response = await authenticatedFetch(
      `/api/orders/indicators/?${query.toString()}`
    )

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(
        apiError(
          data,
          'No fue posible consultar los indicadores.'
        )
      )
    }

    indicators.value = data
  } catch (err) {
    indicators.value = null
    error.value = (
      err?.message
      || 'Error al consultar los indicadores operacionales.'
    )
  } finally {
    loading.value = false
  }
}


onMounted(loadIndicators)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Indicadores operacionales

      <template #subtitle>
        Métricas calculadas desde las órdenes registradas en Martini Cell.
      </template>

      <template #actions>
        <div class="d-flex flex-wrap gap-2">
          <input
            v-model="start"
            type="date"
            class="form-control form-control-sm"
            aria-label="Fecha inicial"
            :disabled="loading"
          >

          <input
            v-model="end"
            type="date"
            class="form-control form-control-sm"
            aria-label="Fecha final"
            :disabled="loading"
          >

          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="loading"
            @click="loadIndicators"
          >
            <span
              v-if="loading"
              class="spinner-border spinner-border-sm me-1"
            ></span>

            {{ loading ? 'Calculando...' : 'Actualizar' }}
          </button>
        </div>
      </template>
    </PageHeader>

    <div
      v-if="error"
      class="alert alert-danger"
      role="alert"
    >
      {{ error }}
    </div>

    <div
      v-if="loading && !indicators"
      class="mc-card p-4 text-muted"
    >
      Calculando indicadores...
    </div>

    <template v-else-if="indicators">
      <div class="alert alert-light border mb-4">
        <div class="d-flex flex-wrap justify-content-between gap-2">
          <div>
            <strong>Período de cálculo:</strong>
            {{ formatPeriodDate(indicators.period.start) }}
            al
            {{ formatPeriodDate(indicators.period.end) }}
          </div>

          <div class="text-muted small">
            {{ indicators.orders_with_time_data }}
            orden(es) con tiempos verificables ·
            {{ indicators.orders_without_time_data }}
            sin datos de tiempo válidos
          </div>
        </div>
      </div>

      <div class="row g-3 mb-4">
        <div class="col-6 col-xl">
          <div class="mc-card metric h-100">
            <div class="value">
              {{ indicators.orders_received }}
            </div>
            <div class="mc-muted">
              Órdenes recibidas
            </div>
          </div>
        </div>

        <div class="col-6 col-xl">
          <div class="mc-card metric h-100">
            <div class="value">
              {{ indicators.orders_finalized }}
            </div>
            <div class="mc-muted">
              Órdenes finalizadas
            </div>
          </div>
        </div>

        <div class="col-6 col-xl">
          <div class="mc-card metric h-100">
            <div class="value">
              {{
                formatDuration(
                  indicators.average_technical_seconds
                )
              }}
            </div>
            <div class="mc-muted">
              Tiempo técnico promedio
            </div>
          </div>
        </div>

        <div class="col-6 col-xl">
          <div class="mc-card metric h-100">
            <div class="value">
              {{
                formatDuration(
                  indicators.average_waiting_seconds
                )
              }}
            </div>
            <div class="mc-muted">
              Tiempo de espera promedio
            </div>
          </div>
        </div>

        <div class="col-12 col-xl">
          <div class="mc-card metric h-100">
            <div class="value">
              {{
                formatDuration(
                  indicators.average_total_seconds
                )
              }}
            </div>
            <div class="mc-muted">
              Tiempo total promedio
            </div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-lg-8">
          <div class="mc-card p-4 h-100">
            <h5 class="mb-1">
              Órdenes por estado
            </h5>

            <p class="small text-muted mb-4">
              Distribución de las órdenes recibidas durante el período seleccionado.
            </p>

            <div
              v-for="item in statusRows"
              :key="item.status"
              class="mt-3"
            >
              <div
                class="d-flex justify-content-between small gap-3"
              >
                <span>
                  {{ item.status_display }}
                </span>

                <strong>
                  {{ item.count }}
                </strong>
              </div>

              <div class="bar-track mt-1">
                <div
                  class="bar-fill"
                  :style="{
                    width: `${(item.count / maxCount) * 100}%`
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-4">
          <div class="mc-card p-4 h-100">
            <h5>
              Fuente de cálculo
            </h5>

            <p class="text-muted">
              Las métricas se calculan en el backend a partir de
              las órdenes persistidas y del historial real de
              estados.
            </p>

            <div class="alert alert-light border small mb-0">
              <i class="bi bi-info-circle me-1"></i>
              Los tiempos reutilizan la lógica de HU-11. Una
              orden con historial inconsistente sigue contando
              como orden del período, pero no participa en los
              promedios de tiempo.
            </div>
          </div>
        </div>
      </div>
    </template>
  </AdminLayout>
</template>