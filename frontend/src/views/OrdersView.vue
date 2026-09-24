
<script setup>
import { computed, onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { authenticatedFetch } from '../services/auth'

const orders = ref([])
const search = ref('')
const selectedStatus = ref('')

const loading = ref(true)
const error = ref('')

const statuses = [
  { value: '', label: 'Todos los estados' },
  { value: 'RECEIVED', label: 'Ingresado' },
  { value: 'DIAGNOSIS', label: 'Diagnóstico' },
  { value: 'AUTHORIZATION', label: 'Autorización' },
  { value: 'PART', label: 'Espera de repuesto' },
  { value: 'REPAIR', label: 'Reparación' },
  { value: 'TESTING', label: 'Pruebas' },
  { value: 'READY', label: 'Listo para retiro' },
  { value: 'DELIVERED', label: 'Entregado' },
  { value: 'CLOSED', label: 'Cerrado' },
  { value: 'REJECTED', label: 'No reparado/rechazado' },
]

// Buscar entre las órdenes reales obtenidas desde Django.
const filteredOrders = computed(() => {
  const term = search.value.trim().toLowerCase()

  return orders.value.filter((order) => {
    const matchesStatus =
      !selectedStatus.value ||
      order.status === selectedStatus.value

    const searchableText = [
      order.tracking_code,
      order.client_name,
      order.equipment_description,
      order.reported_issue,
    ]
      .join(' ')
      .toLowerCase()

    const matchesSearch =
      !term || searchableText.includes(term)

    return matchesStatus && matchesSearch
  })
})

function formatDate(value, includeTime = false) {
  if (!value) return 'No disponible'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Fecha no disponible'
  }

  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    ...(includeTime
      ? {
          hour: '2-digit',
          minute: '2-digit',
        }
      : {}),
  }).format(date)
}

// Consultar las órdenes registradas en PostgreSQL.
async function loadOrders() {
  loading.value = true
  error.value = ''

  try {
    const response = await authenticatedFetch('/api/orders/')

    if (!response.ok) {
      throw new Error(
        'No fue posible cargar las órdenes de servicio.'
      )
    }

    const data = await response.json()

    orders.value = Array.isArray(data)
      ? data
      : data.results || []

  } catch (err) {
    orders.value = []

    error.value =
      err.message || 'Error al cargar las órdenes.'

  } finally {
    loading.value = false
  }
}

onMounted(loadOrders)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Órdenes de servicio

      <template #subtitle>
        Gestión y consulta de órdenes registradas.
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

    <div class="mc-card p-3">
      <!-- Búsqueda y filtros -->
      <div class="row g-2 mb-3">
        <div class="col-md-8">
          <input
            v-model="search"
            class="form-control"
            type="search"
            placeholder="Buscar por código, cliente o equipo..."
            aria-label="Buscar órdenes"
          >
        </div>

        <div class="col-md-4">
          <select
            v-model="selectedStatus"
            class="form-select"
            aria-label="Filtrar por estado"
          >
            <option
              v-for="status in statuses"
              :key="status.value"
              :value="status.value"
            >
              {{ status.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- Tabla -->
      <div class="table-responsive">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th>Código</th>
              <th>Cliente</th>
              <th>Equipo</th>
              <th>Estado</th>
              <th>Registrado por</th>
              <th>Ingreso</th>
              <th>Actualización</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="text-center py-4">
                <div
                  class="spinner-border text-primary mb-2"
                  role="status"
                ></div>

                <div class="text-muted">
                  Cargando órdenes...
                </div>
              </td>
            </tr>

            <tr
              v-else-if="filteredOrders.length === 0"
            >
              <td
                colspan="7"
                class="empty-state text-center"
              >
                {{
                  error
                    ? 'No se pudieron cargar las órdenes.'
                    : 'No hay órdenes para los filtros seleccionados.'
                }}
              </td>
            </tr>

            <tr
              v-for="order in loading ? [] : filteredOrders"
              :key="order.id"
            >
              <!-- Enlace al detalle real de la orden -->
              <td>
                <router-link
                  :to="`/ordenes/${order.id}`"
                  class="fw-semibold text-decoration-none"
                >
                  {{ order.tracking_code }}
                </router-link>

                <div class="small text-muted">
                  Orden #{{ order.id }}
                </div>
              </td>

              <td>
                {{ order.client_name }}
              </td>

              <td>
                {{ order.equipment_description }}
              </td>

              <td>
                <StatusBadge
                  :status="order.status"
                  :label="
                    order.status_display || order.status
                  "
                />
              </td>

              <td>
                {{
                  order.created_by_username ||
                  'No disponible'
                }}
              </td>

              <td>
                {{ formatDate(order.received_at) }}
              </td>

              <td>
                {{ formatDate(order.updated_at, true) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AdminLayout>
</template>