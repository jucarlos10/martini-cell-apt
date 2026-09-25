<script setup>
import { onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'

const warranties = ref([])
const loading = ref(true)
const error = ref('')

const statusLabels = {
  ACTIVE: 'Vigente',
  EXPIRED: 'Vencida',
  NOT_STARTED: 'Aún no inicia',
  NOT_APPLICABLE: 'No aplica',
}

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

async function loadWarranties() {
  loading.value = true
  error.value = ''

  try {
    const response = await authenticatedFetch(
      '/api/orders/warranties/'
    )

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error(
          'No tienes permiso para consultar las garantías.'
        )
      }

      throw new Error(
        'No fue posible cargar las garantías. Inténtalo nuevamente.'
      )
    }

    const data = await response.json()

    warranties.value = Array.isArray(data)
      ? data
      : (Array.isArray(data?.results) ? data.results : [])

  } catch (err) {
    warranties.value = []

    error.value =
      err?.message || 'Ocurrió un error al consultar las garantías.'

  } finally {
    loading.value = false
  }
}

onMounted(loadWarranties)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Garantías

      <template #subtitle>
        Seguimiento de las garantías registradas en Martini Cell.
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
                No hay garantías registradas.
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
                {{ warranty.conditions || 'Sin condiciones registradas' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AdminLayout>
</template>