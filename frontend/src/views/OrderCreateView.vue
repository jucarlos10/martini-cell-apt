<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'

const step = ref(1)
const loading = ref(true)
const saving = ref(false)

const error = ref('')
const createdOrder = ref(null)

const clients = ref([])
const devices = ref([])

const clientId = ref('')
const equipmentId = ref('')
const clientSearch = ref('')

const order = ref({
  reported_issue: '',
  initial_observations: '',
})

// Normalizar el RUT para buscar con o sin puntos y guion.
function normalizeRut(value) {
  return String(value ?? '')
    .replace(/[^0-9kK]/g, '')
    .toUpperCase()
}

// Mostrar el RUT con puntos y guion.
function formatRut(value) {
  const clean = normalizeRut(value)

  if (clean.length <= 1) return clean

  const body = clean.slice(0, -1)
  const verifier = clean.slice(-1)

  const formattedBody = body.replace(
    /\B(?=(\d{3})+(?!\d))/g,
    '.'
  )

  return `${formattedBody}-${verifier}`
}

const selectedClient = computed(() =>
  clients.value.find(
    (client) => String(client.id) === String(clientId.value)
  ) || null
)

// Clientes que coinciden con el nombre o el RUT ingresado.
const matchingClients = computed(() => {
  const term = clientSearch.value.trim().toLowerCase()

  if (!term) return clients.value

  const rutTerm = /^[0-9.kK-]+$/.test(term)
    ? normalizeRut(term)
    : ''

  return clients.value.filter((client) =>
    String(client.name || '').toLowerCase().includes(term) ||
    (rutTerm !== '' && normalizeRut(client.rut).includes(rutTerm))
  )
})

// El cliente seleccionado permanece visible incluso si cambia la búsqueda.
const filteredClients = computed(() => {
  const selected = selectedClient.value
  const matches = matchingClients.value

  if (!clientSearch.value.trim() || !selected ||
      matches.some((client) => client.id === selected.id)) {
    return matches
  }

  return [selected, ...matches]
})

const availableDevices = computed(() => {
  if (!clientId.value) return []

  return devices.value.filter(
    (device) =>
      String(device.client) === String(clientId.value) &&
      device.is_active
  )
})

const selectedEquipment = computed(() =>
  availableDevices.value.find(
    (device) => String(device.id) === String(equipmentId.value)
  ) || null
)

// Al cambiar de cliente, limpiar la selección del equipo.
watch(clientId, () => {
  equipmentId.value = ''
})

// Mostrar errores enviados por Django.
function formatApiErrors(data) {
  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (!data || typeof data !== 'object') {
    return 'No fue posible completar la operación.'
  }

  return Object.entries(data)
    .map(([field, messages]) => {
      const message = Array.isArray(messages)
        ? messages.join(' ')
        : String(messages)

      return `${field}: ${message}`
    })
    .join(' ')
}

// Obtener clientes y equipos reales.
async function loadData() {
  loading.value = true
  error.value = ''

  try {
    const clientsResponse = await authenticatedFetch(
      '/api/clients/'
    )

    if (!clientsResponse.ok) {
      throw new Error(
        'No fue posible cargar los clientes.'
      )
    }

    const clientsData = await clientsResponse.json()

    clients.value = Array.isArray(clientsData)
      ? clientsData
      : clientsData.results || []

    const devicesResponse = await authenticatedFetch(
      '/api/devices/'
    )

    if (!devicesResponse.ok) {
      throw new Error(
        'No fue posible cargar los equipos.'
      )
    }

    const devicesData = await devicesResponse.json()

    devices.value = Array.isArray(devicesData)
      ? devicesData
      : devicesData.results || []

  } catch (err) {
    error.value =
      err.message || 'Error al cargar la información.'

  } finally {
    loading.value = false
  }
}

// Validaciones de los pasos.
function next() {
  error.value = ''

  if (step.value === 1) {
    if (!selectedClient.value) {
      error.value = 'Selecciona un cliente.'
      return
    }

    if (!selectedEquipment.value) {
      error.value =
        'Selecciona un equipo asociado al cliente.'
      return
    }
  }

  if (step.value === 2) {
    if (!order.value.reported_issue.trim()) {
      error.value =
        'Describe la falla o síntoma reportado.'
      return
    }
  }

  if (step.value < 3) {
    step.value++
  }
}

function previous() {
  if (saving.value || step.value === 1) return

  error.value = ''
  step.value--
}

// Crear la orden real mediante Django.
async function save() {
  if (saving.value || createdOrder.value) return

  error.value = ''

  if (!selectedClient.value || !selectedEquipment.value) {
    error.value =
      'Debes seleccionar un cliente y un equipo válido.'
    step.value = 1
    return
  }

  if (!order.value.reported_issue.trim()) {
    error.value =
      'Describe la falla o síntoma reportado.'
    step.value = 2
    return
  }

  saving.value = true

  try {
    const response = await authenticatedFetch('/api/orders/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client: selectedClient.value.id,
        equipment: selectedEquipment.value.id,
        reported_issue: order.value.reported_issue.trim(),
        initial_observations:
          order.value.initial_observations.trim(),
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)

      throw new Error(formatApiErrors(data))
    }

    // Django devuelve el ID y el código único de seguimiento.
    createdOrder.value = await response.json()

  } catch (err) {
    error.value =
      err.message || 'No fue posible crear la orden.'

  } finally {
    saving.value = false
  }
}

function restart() {
  createdOrder.value = null

  step.value = 1
  clientId.value = ''
  equipmentId.value = ''
  clientSearch.value = ''

  order.value = {
    reported_issue: '',
    initial_observations: '',
  }

  error.value = ''
}

onMounted(loadData)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Nueva orden de servicio

      <template #subtitle>
        Registro de recepción en tres pasos.
      </template>

      <template #actions>
        <router-link
          to="/ordenes"
          class="btn btn-outline-secondary"
        >
          Volver a órdenes
        </router-link>
      </template>
    </PageHeader>

    <div v-if="loading" class="mc-card p-4 text-center">
      <div
        class="spinner-border text-primary mb-2"
        role="status"
      ></div>

      <div class="text-muted">
        Cargando clientes y equipos...
      </div>
    </div>

    <!-- Confirmación de la orden creada -->
    <div
      v-else-if="createdOrder"
      class="mc-card p-4"
    >
      <div class="alert alert-success" role="status">
        <i class="bi bi-check-circle me-2"></i>
        Orden de servicio creada correctamente.
      </div>

      <h4 class="mb-3">
        {{ createdOrder.tracking_code }}
      </h4>

      <div class="mb-2">
        <strong>ID de orden:</strong>
        {{ createdOrder.id }}
      </div>

      <div class="mb-2">
        <strong>Cliente:</strong>
        {{ createdOrder.client_name }}
      </div>

      <div class="mb-2">
        <strong>Equipo:</strong>
        {{ createdOrder.equipment_description }}
      </div>

      <div class="mb-2">
        <strong>Estado inicial:</strong>
        {{
          createdOrder.status_display ||
          createdOrder.status
        }}
      </div>

      <div class="mb-3">
        <strong>Fecha de ingreso:</strong>
        {{
          new Date(
            createdOrder.received_at
          ).toLocaleString('es-CL')
        }}
      </div>

      <div class="alert alert-info">
        Guarda el código de seguimiento para identificar
        esta atención. Conectaremos la navegación al detalle
        real cuando integremos el listado y detalle de órdenes.
      </div>

      <button
        type="button"
        class="btn btn-primary"
        @click="restart"
      >
        Crear otra orden
      </button>
    </div>

    <!-- Formulario de tres pasos -->
    <div v-else class="mc-card p-4">

      <div class="d-flex flex-wrap gap-3 mb-4">
        <div
          v-for="n in 3"
          :key="n"
          class="d-flex align-items-center gap-2"
        >
          <span
            class="badge rounded-pill"
            :class="
              step >= n
                ? 'text-bg-primary'
                : 'text-bg-light'
            "
          >
            {{ n }}
          </span>

          <span class="small fw-semibold">
            {{
              n === 1
                ? 'Cliente y equipo'
                : n === 2
                  ? 'Recepción'
                  : 'Revisión'
            }}
          </span>
        </div>
      </div>

      <div
        v-if="error"
        class="alert alert-danger"
        role="alert"
      >
        {{ error }}
      </div>

      <!-- PASO 1: Cliente y equipo -->
      <section v-if="step === 1">
        <h5>Cliente y equipo</h5>

        <div class="row g-4 mt-1">

          <div class="col-lg-5">
            <label
              for="order-client"
              class="form-label"
            >
              Cliente registrado
            </label>

            <input
              id="order-client-search"
              v-model="clientSearch"
              type="search"
              class="form-control mb-2"
              placeholder="Buscar por RUT o nombre..."
              aria-label="Buscar cliente por RUT o nombre"
              :disabled="saving"
            >

            <select
              id="order-client"
              v-model="clientId"
              class="form-select"
              :disabled="saving"
            >
              <option value="">
                Seleccionar cliente...
              </option>

              <option
                v-for="client in filteredClients"
                :key="client.id"
                :value="client.id"
              >
                {{ client.name }} ·
                {{ formatRut(client.rut) }}
              </option>
            </select>

            <div
              v-if="clientSearch.trim() && matchingClients.length === 0"
              class="form-text text-warning"
            >
              No se encontraron coincidencias con esa búsqueda.
              Si ya seleccionaste un cliente, seguirá visible en la lista.
            </div>

            <div class="form-text">
              ¿El cliente aún no está registrado?
              <router-link to="/clientes">
                Regístralo en Clientes y equipos.
              </router-link>
            </div>
          </div>

          <div class="col-lg-7">
            <label
              for="order-equipment"
              class="form-label"
            >
              Equipo del cliente
            </label>

            <select
              id="order-equipment"
              v-model="equipmentId"
              class="form-select"
              :disabled="!selectedClient"
            >
              <option value="">
                Seleccionar equipo...
              </option>

              <option
                v-for="device in availableDevices"
                :key="device.id"
                :value="device.id"
              >
                Equipo #{{ device.id }} ·
                {{ device.brand }}
                {{ device.model }}
              </option>
            </select>

            <div
              v-if="
                selectedClient &&
                availableDevices.length === 0
              "
              class="alert alert-warning mt-3"
            >
              Este cliente no tiene equipos activos registrados.
              Primero debes registrar su equipo desde
              <router-link to="/clientes">
                Clientes y equipos
              </router-link>.
            </div>

            <div
              v-if="selectedEquipment"
              class="mt-3 small text-muted"
            >
              <div>
                <strong>Marca:</strong>
                {{ selectedEquipment.brand }}
              </div>

              <div>
                <strong>Modelo:</strong>
                {{ selectedEquipment.model }}
              </div>

              <div>
                <strong>ID interno:</strong>
                Equipo #{{ selectedEquipment.id }}
              </div>
            </div>
          </div>

        </div>
      </section>

      <!-- PASO 2: Recepción -->
      <section v-if="step === 2">
        <h5>Recepción</h5>

        <label
          for="reported-issue"
          class="form-label mt-3"
        >
          Falla o síntoma reportado
        </label>

        <textarea
          id="reported-issue"
          v-model="order.reported_issue"
          class="form-control mb-3"
          rows="4"
          placeholder="Describe el problema informado por el cliente."
          required
        ></textarea>

        <label
          for="initial-observations"
          class="form-label"
        >
          Observaciones iniciales
        </label>

        <textarea
          id="initial-observations"
          v-model="order.initial_observations"
          class="form-control mb-3"
          rows="3"
          placeholder="Estado de recepción, accesorios entregados u otras observaciones."
        ></textarea>

        <div class="form-text">
          Django registrará automáticamente la fecha,
          hora y usuario que crea la orden.
        </div>
      </section>

      <!-- PASO 3: Revisión -->
      <section v-if="step === 3">
        <h5>Revisión</h5>

        <div class="row g-3 mt-2">
          <div class="col-md-6">
            <div class="mc-card p-3 h-100">
              <div class="small text-muted">
                Cliente
              </div>

              <strong>
                {{ selectedClient?.name }}
              </strong>

              <div class="small text-muted">
                RUT:
                {{ formatRut(selectedClient?.rut) }}
              </div>

              <hr>

              <div class="small text-muted">
                Equipo
              </div>

              <strong>
                {{ selectedEquipment?.brand }}
                {{ selectedEquipment?.model }}
              </strong>

              <div class="small text-muted">
                Equipo #{{ selectedEquipment?.id }}
              </div>
            </div>
          </div>

          <div class="col-md-6">
            <div class="mc-card p-3 h-100">
              <div class="small text-muted">
                Falla reportada
              </div>

              <strong>
                {{ order.reported_issue }}
              </strong>

              <hr>

              <div class="small text-muted">
                Observaciones iniciales
              </div>

              <div>
                {{
                  order.initial_observations ||
                  'Sin observaciones adicionales'
                }}
              </div>
            </div>
          </div>
        </div>

        <div class="alert alert-info mt-3 mb-0">
          Al confirmar, Django generará el código único
          de seguimiento y registrará el estado inicial.
        </div>
      </section>

      <!-- Navegación -->
      <div
        class="d-flex justify-content-between mt-4"
      >
        <button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="step === 1 || saving"
          @click="previous"
        >
          Anterior
        </button>

        <button
          v-if="step < 3"
          type="button"
          class="btn btn-primary"
          @click="next"
        >
          Siguiente
          <i class="bi bi-arrow-right ms-1"></i>
        </button>

        <button
          v-else
          type="button"
          class="btn btn-primary"
          :disabled="saving"
          @click="save"
        >
          <span
            v-if="saving"
            class="spinner-border spinner-border-sm me-2"
            aria-hidden="true"
          ></span>

          {{
            saving
              ? 'Creando orden...'
              : 'Crear orden de servicio'
          }}
        </button>
      </div>

    </div>
  </AdminLayout>
</template>