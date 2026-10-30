<script setup>
import { computed, onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { authenticatedFetch, getCurrentUser } from '../services/auth'

const orders = ref([])
const loading = ref(true)
const error = ref('')
const loyaltyAlerts = ref([])
const loyaltyError = ref('')
const loyaltyLoading = ref(false)
const isAdmin = getCurrentUser()?.role === 'ADMIN'

async function loadLoyaltyAlerts() {
  if (!isAdmin) return
  loyaltyLoading.value = true
  loyaltyError.value = ''
  try {
    const response = await authenticatedFetch('/api/clients/loyalty/alerts/')
    if (!response.ok) throw new Error('No fue posible cargar los avisos de beneficios.')
    loyaltyAlerts.value = await response.json()
  } catch (err) {
    loyaltyError.value = err.message
  } finally {
    loyaltyLoading.value = false
  }
}

const open = computed(() =>
  orders.value.filter(
    (order) => !['DELIVERED', 'CLOSED', 'REJECTED'].includes(order.status)
  ).length
)

const auth = computed(() =>
  orders.value.filter(
    (order) => order.status === 'AUTHORIZATION'
  ).length
)

const part = computed(() =>
  orders.value.filter(
    (order) => order.status === 'PART'
  ).length
)

const ready = computed(() =>
  orders.value.filter(
    (order) => order.status === 'READY'
  ).length
)

const recent = computed(() =>
  [...orders.value]
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() -
        new Date(a.updated_at).getTime()
    )
    .slice(0, 5)
)

const metrics = computed(() => [
  { label: 'Órdenes abiertas', value: open.value },
  { label: 'Espera autorización', value: auth.value },
  { label: 'Espera repuesto', value: part.value },
  { label: 'Listas para entrega', value: ready.value },
])

const serviceFlow = [
  'Ingreso',
  'Diagnóstico',
  'Autorización',
  'Repuesto',
  'Reparación',
  'Pruebas',
  'Entrega',
]

function formatDate(value) {
  if (!value) return 'No disponible'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Fecha no disponible'
  }

  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function loadOrders() {
  loading.value = true
  error.value = ''

  try {
    const response = await authenticatedFetch('/api/orders/')

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error(
          'No tienes permiso para consultar las órdenes.'
        )
      }

      throw new Error(
        'No fue posible cargar el resumen de órdenes.'
      )
    }

    const data = await response.json()

    orders.value = Array.isArray(data)
      ? data
      : (Array.isArray(data?.results) ? data.results : [])

  } catch (err) {
    orders.value = []

    error.value =
      err?.message || 'Ocurrió un error al cargar el panel.'

  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadOrders()
  loadLoyaltyAlerts()
})
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Panel principal

      <template #subtitle>
        Resumen de la actividad actual de Martini Cell.
      </template>

      <template #actions>
        <router-link
          to="/ordenes/nueva"
          class="btn btn-primary"
        >
          <i class="bi bi-plus-lg me-1"></i>
          Nueva orden
        </router-link>
      </template>
    </PageHeader>

    <div v-if="isAdmin" class="mc-card p-3 mb-4">
      <div class="d-flex justify-content-between align-items-center gap-2 mb-2">
        <h5 class="mb-0">Beneficios por ingresos</h5>
        <div class="d-flex flex-wrap gap-2">
          <router-link to="/demo-beneficios" class="btn btn-sm btn-outline-secondary">
            Probar simulador
          </router-link>
          <button type="button" class="btn btn-sm btn-outline-primary" @click="loadLoyaltyAlerts">
            Actualizar avisos
          </button>
        </div>
      </div>
      <div v-if="loyaltyLoading" class="text-muted">Consultando avisos...</div>
      <div v-else-if="loyaltyError" class="alert alert-danger mb-0" role="alert">{{ loyaltyError }}</div>
      <div v-else-if="!loyaltyAlerts.length" class="text-muted">No hay beneficios pendientes de revisión.</div>
      <div v-else>
        <div v-for="client in loyaltyAlerts" :key="client.id" class="border-top py-2">
          <router-link :to="`/clientes?cliente=${client.id}`" class="fw-semibold">
            {{ client.name }}
          </router-link>
          · Ciclo {{ client.loyalty_cycle_visits }} / {{ client.loyalty_cycle_target }} ·
          Beneficio pendiente
        </div>
      </div>
      <div class="small text-muted mt-2">
        Prototipo de prueba: el aviso permanece hasta registrar el beneficio simulado.
      </div>
    </div>

    <div
      v-if="error"
      class="alert alert-danger"
      role="alert"
    >
      {{ error }}

      <button
        type="button"
        class="btn btn-sm btn-outline-danger ms-2"
        @click="loadOrders"
      >
        Reintentar
      </button>
    </div>

    <div class="row g-3 mb-4">
      <div
        v-for="metric in metrics"
        :key="metric.label"
        class="col-6 col-xl-3"
      >
        <div class="mc-card metric">
          <div class="value">
            {{
              loading || error
                ? '—'
                : metric.value
            }}
          </div>

          <div class="mc-muted">
            {{ metric.label }}
          </div>
        </div>
      </div>
    </div>

    <div class="row g-3">
      <div class="col-xl-8">
        <div class="mc-card p-3">
          <div class="d-flex justify-content-between mb-3">
            <h5 class="mb-0">
              Órdenes recientes
            </h5>

            <router-link to="/ordenes">
              Ver todas
            </router-link>
          </div>

          <div class="table-responsive">
            <table class="table mb-0">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Equipo</th>
                  <th>Estado</th>
                  <th>Registrado por</th>
                  <th>Actualización</th>
                </tr>
              </thead>

              <tbody>
                <tr v-if="loading">
                  <td
                    colspan="5"
                    class="text-center py-4"
                  >
                    <div
                      class="spinner-border text-primary mb-2"
                      role="status"
                    ></div>

                    <div class="text-muted">
                      Cargando órdenes...
                    </div>
                  </td>
                </tr>

                <tr v-else-if="error">
                  <td
                    colspan="5"
                    class="text-center py-4 text-muted"
                  >
                    No se pudieron cargar las órdenes.
                  </td>
                </tr>

                <tr v-else-if="recent.length === 0">
                  <td
                    colspan="5"
                    class="text-center py-4 text-muted"
                  >
                    No hay órdenes registradas.
                  </td>
                </tr>

                <tr
                  v-for="order in loading || error ? [] : recent"
                  :key="order.id"
                >
                  <td>
                    <router-link
                      :to="`/ordenes/${order.id}`"
                      class="fw-semibold text-decoration-none"
                    >
                      {{ order.tracking_code }}
                    </router-link>
                  </td>

                  <td>
                    {{ order.equipment_description }}
                  </td>

                  <td>
                    <StatusBadge
                      :status="order.status"
                      :label="order.status_display || order.status"
                    />
                  </td>

                  <td>
                    {{ order.created_by_username || 'No disponible' }}
                  </td>

                  <td>
                    {{ formatDate(order.updated_at) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="col-xl-4">
        <div class="mc-card p-4 h-100">
          <h5>Flujo del servicio</h5>

          <div class="small text-muted mb-3">
            Vista conceptual del proceso principal.
          </div>

          <div
            v-for="stage in serviceFlow"
            :key="stage"
            class="d-flex align-items-center gap-2 py-2 border-bottom"
          >
            <span class="badge rounded-pill text-bg-primary">
              {{ stage }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>
