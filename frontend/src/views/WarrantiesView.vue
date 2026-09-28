<script setup>
import { computed, onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'

const warranties = ref([])
const loading = ref(true)
const error = ref('')

const search = ref('')
const statusFilter = ref('')
const typeFilter = ref('')

const statusLabels = {
  ACTIVE: 'Vigente',
  EXPIRED: 'Vencida',
  NOT_STARTED: 'Aún no inicia',
  NOT_APPLICABLE: 'No aplica',
}

const statusOptions = [
  { value: '', label: 'Todos los estados' },
  { value: 'ACTIVE', label: 'Vigente' },
  { value: 'EXPIRED', label: 'Vencida' },
  { value: 'NOT_STARTED', label: 'Aún no inicia' },
  { value: 'NOT_APPLICABLE', label: 'No aplica' },
]

const typeOptions = [
  { value: '', label: 'Todos los tipos' },
  { value: 'SERVICE', label: 'Garantía del servicio' },
  { value: 'PART', label: 'Garantía de repuesto' },
]

const hasActiveFilters = computed(
  () =>
    search.value.trim() !== '' ||
    statusFilter.value !== '' ||
    typeFilter.value !== ''
)

function statusBadgeClass(value) {
  return {
    ACTIVE: 'text-bg-success',
    EXPIRED: 'text-bg-secondary',
    NOT_STARTED: 'text-bg-info',
    NOT_APPLICABLE: 'text-bg-light',
  }[value] || 'text-bg-secondary'
}

// Las fechas de garantía son fechas de calendario (YYYY-MM-DD).
// Se formatean sin convertirlas a UTC para evitar cambiar el día.
function formatDate(value) {
  if (!value) return '—'

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)

  if (!match) return 'Fecha no disponible'

  return `${match[3]}/${match[2]}/${match[1]}`
}

function formatValidity(warranty) {
  if (!warranty.is_applicable) {
    return 'No aplica'
  }

  return (
    `${formatDate(warranty.starts_on)} → ` +
    `${formatDate(warranty.ends_on)}`
  )
}

function buildWarrantyUrl() {
  const params = new URLSearchParams()

  const searchValue = search.value.trim()

  if (searchValue) {
    params.set('q', searchValue)
  }

  if (statusFilter.value) {
    params.set('status', statusFilter.value)
  }

  if (typeFilter.value) {
    params.set('type', typeFilter.value)
  }

  const query = params.toString()

  return query
    ? `/api/orders/warranties/?${query}`
    : '/api/orders/warranties/'
}

async function loadWarranties() {
  loading.value = true
  error.value = ''

  try {
    const response = await authenticatedFetch(
      buildWarrantyUrl()
    )

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error(
          'No tienes permiso para consultar las garantías.'
        )
      }

      throw new Error(
        data?.detail ||
        'No fue posible cargar las garantías. Inténtalo nuevamente.'
      )
    }

    warranties.value = Array.isArray(data)
      ? data
      : (Array.isArray(data?.results) ? data.results : [])

  } catch (err) {
    warranties.value = []

    error.value =
      err?.message ||
      'Ocurrió un error al consultar las garantías.'

  } finally {
    loading.value = false
  }
}

async function clearFilters() {
  search.value = ''
  statusFilter.value = ''
  typeFilter.value = ''

  await loadWarranties()
}

onMounted(loadWarranties)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Garantías

      <template #subtitle>
        Seguimiento y búsqueda de las garantías registradas en Martini Cell.
      </template>

      <template #actions>
        <button
          type="button"
          class="btn btn-outline-primary"
          :disabled="loading"
          @click="loadWarranties"
        >
          <i class="bi bi-arrow-clockwise me-1"></i>
          Actualizar
        </button>
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
        @click="loadWarranties"
      >
        Reintentar
      </button>
    </div>

    <!-- HU-33: búsqueda y filtros de garantías -->
    <div class="mc-card p-3 mb-3">
      <form
        class="row g-3 align-items-end"
        @submit.prevent="loadWarranties"
      >
        <div class="col-lg-6">
          <label
            for="warranty-search"
            class="form-label"
          >
            Buscar garantía
          </label>

          <input
            id="warranty-search"
            v-model="search"
            type="search"
            class="form-control"
            placeholder="Código de orden, RUT o nombre del cliente..."
            :disabled="loading"
          >

          <div class="form-text">
            Puedes buscar por código de seguimiento, RUT o nombre del cliente.
          </div>
        </div>

        <div class="col-md-6 col-lg-2">
          <label
            for="warranty-status"
            class="form-label"
          >
            Estado
          </label>

          <select
            id="warranty-status"
            v-model="statusFilter"
            class="form-select"
            :disabled="loading"
            @change="loadWarranties"
          >
            <option
              v-for="option in statusOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="col-md-6 col-lg-2">
          <label
            for="warranty-type"
            class="form-label"
          >
            Tipo
          </label>

          <select
            id="warranty-type"
            v-model="typeFilter"
            class="form-select"
            :disabled="loading"
            @change="loadWarranties"
          >
            <option
              v-for="option in typeOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="col-lg-2">
          <div class="d-grid gap-2">
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="loading"
            >
              <i class="bi bi-search me-1"></i>
              Buscar
            </button>

            <button
              type="button"
              class="btn btn-outline-secondary"
              :disabled="loading || !hasActiveFilters"
              @click="clearFilters"
            >
              Limpiar
            </button>
          </div>
        </div>
      </form>
    </div>

    <div class="mc-card p-3">
      <div class="table-responsive">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th scope="col">Orden</th>
              <th scope="col">Estado</th>
              <th scope="col">Vigencia</th>
              <th scope="col">Repuesto</th>
              <th scope="col">Proveedor</th>
              <th scope="col">Condiciones</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td
                colspan="6"
                class="text-center py-4"
              >
                <div
                  class="spinner-border text-primary mb-2"
                  role="status"
                ></div>

                <div class="text-muted">
                  Cargando garantías...
                </div>
              </td>
            </tr>

            <tr v-else-if="error">
              <td
                colspan="6"
                class="text-center py-4 text-muted"
              >
                No se pudieron cargar las garantías.
              </td>
            </tr>

            <tr v-else-if="warranties.length === 0">
              <td
                colspan="6"
                class="text-center py-4 text-muted"
              >
                <template v-if="hasActiveFilters">
                  No se encontraron garantías que coincidan con la búsqueda
                  o los filtros seleccionados.
                </template>

                <template v-else>
                  No hay garantías registradas.
                </template>
              </td>
            </tr>

            <tr
              v-for="warranty in loading || error ? [] : warranties"
              :key="warranty.id"
            >
              <td>
                <router-link
                  :to="`/ordenes/${warranty.order}`"
                  class="fw-semibold text-decoration-none"
                >
                  {{ warranty.tracking_code }}
                </router-link>

                <div class="small text-muted">
                  {{ warranty.warranty_type_display }}
                </div>
              </td>

              <td>
                <span
                  class="badge"
                  :class="statusBadgeClass(warranty.status)"
                >
                  {{
                    statusLabels[warranty.status] ||
                    warranty.status
                  }}
                </span>
              </td>

              <td>
                {{ formatValidity(warranty) }}
              </td>

              <td>
                {{
                  warranty.part_name ||
                  (warranty.warranty_type === 'SERVICE'
                    ? 'Servicio técnico'
                    : '—')
                }}
              </td>

              <td>
                {{ warranty.supplier_name || '—' }}
              </td>

              <td>
                {{
                  warranty.conditions ||
                  'Sin condiciones registradas'
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AdminLayout>
</template>