<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { authenticatedFetch } from '../services/auth'

const route = useRoute()

const order = ref(null)
const history = ref([])
const technicalReport = ref(null)
const times = ref(null)

const tab = ref('resumen')
const loading = ref(true)
const error = ref('')
const historyError = ref('')
const reportError = ref('')
const timesError = ref('')

// Conservamos la estructura de pestañas del prototipo.
// Las secciones pendientes se habilitarán al integrar sus historias.
const tabs = [
  { key: 'resumen', label: 'Resumen', enabled: true },
  { key: 'diagnostico', label: 'Diagnóstico', enabled: true },
  { key: 'linea', label: 'Línea de tiempo', enabled: true },
  { key: 'evidencias', label: 'Evidencias', enabled: false },
  { key: 'repuestos', label: 'Repuestos y costos', enabled: false },
  { key: 'garantia', label: 'Garantía', enabled: false },
  { key: 'viabilidad', label: 'Índice de viabilidad', enabled: false },
]

function formatDate(value) {
  if (!value) return 'No disponible'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Fecha no disponible'

  return date.toLocaleString('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

async function getResponse(url) {
  const response = await authenticatedFetch(url)
  const data = await response.json().catch(() => null)

  return {
    ok: response.ok,
    status: response.status,
    data,
  }
}

let loadSequence = 0

async function loadOrder() {
  const sequence = ++loadSequence
  const orderId = String(route.params.id ?? '')

  loading.value = true
  error.value = ''
  historyError.value = ''
  reportError.value = ''
  timesError.value = ''

  order.value = null
  history.value = []
  technicalReport.value = null
  times.value = null
  tab.value = 'resumen'

  if (!/^[1-9]\d*$/.test(orderId)) {
    error.value = 'El ID de la orden no es válido.'
    loading.value = false
    return
  }

  try {
    const orderResponse = await getResponse(`/api/orders/${orderId}/`)
    if (sequence !== loadSequence) return

    if (!orderResponse.ok) {
      error.value = orderResponse.status === 404
        ? 'La orden solicitada no existe.'
        : 'No fue posible cargar la orden de servicio.'
      return
    }

    order.value = orderResponse.data

    // Estas consultas son de lectura. Si alguna falla, conservamos
    // el detalle principal y mostramos el problema en su sección.
    const [historyResult, reportResult, timesResult] = await Promise.allSettled([
      getResponse(`/api/orders/${orderId}/status/history/`),
      getResponse(`/api/orders/${orderId}/technical-report/`),
      getResponse(`/api/orders/${orderId}/times/`),
    ])

    if (sequence !== loadSequence) return

    if (
      historyResult.status === 'fulfilled' &&
      historyResult.value.ok &&
      Array.isArray(historyResult.value.data)
    ) {
      history.value = historyResult.value.data
    } else {
      historyError.value = 'No fue posible cargar la línea de tiempo.'
    }

    if (reportResult.status === 'fulfilled') {
      if (reportResult.value.ok) {
        technicalReport.value = reportResult.value.data
      } else if (reportResult.value.status !== 404) {
        reportError.value = 'No fue posible consultar el informe técnico.'
      }
    } else {
      reportError.value = 'No fue posible consultar el informe técnico.'
    }

    if (timesResult.status === 'fulfilled') {
      if (timesResult.value.ok) {
        times.value = timesResult.value.data
      } else {
        timesError.value = timesResult.value.status === 409
          ? (timesResult.value.data?.detail || 'El historial no permite calcular los tiempos.')
          : 'No fue posible calcular los tiempos del servicio.'
      }
    } else {
      timesError.value = 'No fue posible calcular los tiempos del servicio.'
    }
  } catch (err) {
    if (sequence === loadSequence) {
      error.value = err?.message || 'No fue posible cargar la orden de servicio.'
    }
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

// Permite cambiar entre /ordenes/1 y /ordenes/2 sin mostrar datos antiguos.
watch(() => route.params.id, loadOrder, { immediate: true })
</script>

<template>
  <AdminLayout>
    <div v-if="loading" class="mc-card p-4 text-center">
      <div class="spinner-border text-primary mb-2" role="status"></div>
      <div class="text-muted">Cargando orden de servicio...</div>
    </div>

    <div v-else-if="error" class="alert alert-warning" role="alert">
      {{ error }}
      <div class="mt-3">
        <router-link to="/ordenes" class="btn btn-outline-secondary btn-sm">
          Volver a órdenes
        </router-link>
        <button type="button" class="btn btn-outline-primary btn-sm ms-2" @click="loadOrder">
          Reintentar
        </button>
      </div>
    </div>

    <template v-else-if="order">
      <PageHeader>
        {{ order.tracking_code }}
        <StatusBadge
          :status="order.status"
          :label="order.status_display || order.status"
        />

        <template #subtitle>
          {{ order.equipment_description }} · Cliente: {{ order.client_name }}
          · Registrado por: {{ order.created_by_username || 'No disponible' }}
        </template>

        <template #actions>
          <router-link to="/ordenes" class="btn btn-outline-secondary">
            Volver a órdenes
          </router-link>
        </template>
      </PageHeader>

      <div class="section-tabs mb-4">
        <button
          v-for="item in tabs"
          :key="item.key"
          type="button"
          :class="{ active: tab === item.key }"
          :disabled="!item.enabled"
          :title="item.enabled ? item.label : `${item.label}: integración pendiente`"
          @click="tab = item.key"
        >
          {{ item.label }}
          <span v-if="!item.enabled" class="small">(pendiente)</span>
        </button>
      </div>

      <!-- RESUMEN: información real de la orden y sus tiempos -->
      <section v-if="tab === 'resumen'" class="row g-3">
        <div class="col-lg-8">
          <div class="mc-card p-4 h-100">
            <h5>Información general</h5>
            <div class="row g-3 mt-1">
              <div class="col-md-6">
                <div class="mc-muted small">Equipo</div>
                <strong>{{ order.equipment_description }}</strong>
                <div class="small text-muted">Equipo #{{ order.equipment }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Estado actual</div>
                <StatusBadge
                  :status="order.status"
                  :label="order.status_display || order.status"
                />
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Falla reportada</div>
                <div>{{ order.reported_issue }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Observaciones iniciales</div>
                <div>{{ order.initial_observations || 'Sin observaciones adicionales' }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Ingreso</div>
                <div>{{ formatDate(order.received_at) }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Última actualización</div>
                <div>{{ formatDate(order.updated_at) }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Diagnóstico actual</div>
                <div>{{ technicalReport?.diagnosis || (reportError || 'Pendiente') }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Trabajo realizado</div>
                <div>{{ technicalReport?.repair_actions || (reportError || 'Pendiente') }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-4">
          <div class="mc-card p-4">
            <h5>Tiempos del servicio</h5>
            <div v-if="timesError" class="alert alert-warning small mb-0">
              {{ timesError }}
            </div>
            <table v-else-if="times" class="table small mb-0">
              <tbody>
                <tr>
                  <td>Tiempo técnico</td>
                  <td class="text-end fw-semibold">{{ times.technical_display }}</td>
                </tr>
                <tr>
                  <td>Tiempo de espera</td>
                  <td class="text-end">{{ times.waiting_display }}</td>
                </tr>
                <tr class="fw-bold">
                  <td>Total</td>
                  <td class="text-end">{{ times.total_display }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="text-muted">Sin datos disponibles.</div>
            <div v-if="times" class="small text-muted mt-2">
              Calculado al consultar la orden. Los tiempos pueden seguir aumentando.
            </div>
          </div>
        </div>
      </section>

      <!-- DIAGNÓSTICO: lectura del informe real, cuando existe -->
      <section v-if="tab === 'diagnostico'" class="mc-card p-4">
        <h5>Diagnóstico y reparación</h5>
        <div v-if="reportError" class="alert alert-warning">{{ reportError }}</div>
        <div v-else-if="!technicalReport" class="alert alert-info mb-0">
          Esta orden todavía no tiene un informe técnico registrado.
          La edición del informe se integrará en su historia correspondiente.
        </div>
        <div v-else class="row g-3 mt-1">
          <div class="col-md-6">
            <div class="mc-muted small">Diagnóstico definitivo</div>
            <div class="fw-semibold">{{ technicalReport.diagnosis }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Reparación realizada</div>
            <div>{{ technicalReport.repair_actions }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Observaciones de reparación</div>
            <div>{{ technicalReport.repair_observations || 'Sin observaciones' }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Repuestos utilizados</div>
            <div>{{ technicalReport.parts_description || 'Sin descripción de repuestos' }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Resultado</div>
            <strong>{{ technicalReport.result_display || technicalReport.result }}</strong>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Técnico responsable</div>
            <strong>{{ technicalReport.technician_username }}</strong>
          </div>
        </div>
      </section>

      <!-- LÍNEA DE TIEMPO: historial persistido en PostgreSQL -->
      <section v-if="tab === 'linea'" class="row g-4">
        <div class="col-lg-7">
          <div class="mc-card p-4">
            <h5>Línea de tiempo</h5>
            <div v-if="historyError" class="alert alert-warning mt-3">
              {{ historyError }}
            </div>
            <div v-else-if="!history.length" class="text-muted mt-3">
              No hay eventos registrados para esta orden.
            </div>
            <div v-else class="timeline mt-4">
              <div
                v-for="event in [...history].reverse()"
                :key="event.id"
                class="timeline-item"
              >
                <div class="fw-semibold">
                  {{ event.to_status_display || event.to_status }}
                </div>
                <div class="small text-muted">
                  {{ formatDate(event.changed_at) }}
                  · {{ event.changed_by_username || 'Usuario no disponible' }}
                </div>
                <div v-if="event.note" class="mt-1">{{ event.note }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-5">
          <div class="mc-card p-4">
            <h5>Estado de la orden</h5>
            <StatusBadge
              :status="order.status"
              :label="order.status_display || order.status"
            />
            <p class="small text-muted mt-3 mb-0">
              Esta línea de tiempo utiliza el historial real de Django.
              La actualización de estados se conectará al integrar HU-10;
              no se guardarán cambios ficticios en el navegador.
            </p>
          </div>
        </div>
      </section>
    </template>
  </AdminLayout>
</template>
