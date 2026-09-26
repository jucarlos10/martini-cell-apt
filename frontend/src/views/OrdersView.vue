<script setup>
import { computed, onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { authenticatedFetch } from '../services/auth'

const orders = ref([])
const search = ref('')
const selectedStatus = ref('')

// Filtro por fecha de ingreso.
const dateMode = ref('single')
const selectedEntryDate = ref('')
const dateFrom = ref('')
const dateTo = ref('')

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

// Obtener la fecha local en formato YYYY-MM-DD.
// Debe coincidir con el día mostrado en la columna Ingreso.
function getLocalDateValue(value) {
  if (!value) return ''

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return ''

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

const invalidDateRange = computed(() => {
  return Boolean(
    dateMode.value === 'range' &&
    dateFrom.value &&
    dateTo.value &&
    dateFrom.value > dateTo.value
  )
})

const hasActiveDateFilter = computed(() => {
  if (dateMode.value === 'single') {
    return Boolean(selectedEntryDate.value)
  }

  return Boolean(dateFrom.value || dateTo.value)
})

function clearDateFilter() {
  selectedEntryDate.value = ''
  dateFrom.value = ''
  dateTo.value = ''
}

// Combinar búsqueda, estado y fecha de ingreso.
const filteredOrders = computed(() => {
  if (invalidDateRange.value) return []

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

    const entryDate = getLocalDateValue(order.received_at)

    let matchesEntryDate = true

    if (dateMode.value === 'single') {
      matchesEntryDate =
        !selectedEntryDate.value ||
        entryDate === selectedEntryDate.value
    } else if (dateFrom.value || dateTo.value) {
      matchesEntryDate =
        Boolean(entryDate) &&
        (!dateFrom.value || entryDate >= dateFrom.value) &&
        (!dateTo.value || entryDate <= dateTo.value)
    }

    return matchesStatus && matchesSearch && matchesEntryDate
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
      <!-- Búsqueda y estado -->
      <div class="row g-2 mb-3">
        <div class="col-md-8">
          <label
            for="order-search"
            class="form-label small mb-1"
          >
            Buscar orden
          </label>

          <input
            id="order-search"
            v-model="search"
            class="form-control"
            type="search"
            placeholder="Buscar por código, cliente o equipo..."
          >
        </div>

        <div class="col-md-4">
          <label
            for="order-status"
            class="form-label small mb-1"
          >
            Estado
          </label>

          <select
            id="order-status"
            v-model="selectedStatus"
            class="form-select"
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

      <!-- Filtro por fecha de ingreso -->
      <div class="row g-2 mb-3 align-items-end">
        <div class="col-md-3">
          <label
            for="order-date-mode"
            class="form-label small mb-1"
          >
            Filtrar por fecha de ingreso
          </label>

          <select
            id="order-date-mode"
            v-model="dateMode"
            class="form-select"
          >
            <option value="single">Un día</option>
            <option value="range">Rango de fechas</option>
          </select>
        </div>

        <div
          v-if="dateMode === 'single'"
          class="col-md-6"
        >
          <label
            for="order-entry-date"
            class="form-label small mb-1"
          >
            Fecha de ingreso
          </label>

          <input
            id="order-entry-date"
            v-model="selectedEntryDate"
            class="form-control"
            type="date"
          >
        </div>

        <template v-else>
          <div class="col-md-3">
            <label
              for="order-date-from"
              class="form-label small mb-1"
            >
              Desde
            </label>

            <input
              id="order-date-from"
              v-model="dateFrom"
              class="form-control"
              type="date"
            >
          </div>

          <div class="col-md-3">
            <label
              for="order-date-to"
              class="form-label small mb-1"
            >
              Hasta
            </label>

            <input
              id="order-date-to"
              v-model="dateTo"
              class="form-control"
              type="date"
            >
          </div>
        </template>

        <div class="col-md-3">
          <button
            type="button"
            class="btn btn-outline-secondary w-100"
            :disabled="!hasActiveDateFilter"
            @click="clearDateFilter"
          >
            <i class="bi bi-x-circle me-1"></i>
            Limpiar fechas
          </button>
        </div>
      </div>

      <div
        v-if="invalidDateRange"
        class="alert alert-warning"
        role="alert"
      >
        La fecha «Hasta» no puede ser anterior a la fecha «Desde».
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

            <tr v-else-if="filteredOrders.length === 0">
              <td
                colspan="7"
                class="empty-state text-center"
              >
                {{
                  error
                    ? 'No se pudieron cargar las órdenes.'
                    : invalidDateRange
                      ? 'Corrige el rango de fechas seleccionado.'
                      : 'No hay órdenes para los filtros seleccionados.'
                }}
              </td>
            </tr>

            <tr
              v-for="order in loading ? [] : filteredOrders"
              :key="order.id"
            >
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