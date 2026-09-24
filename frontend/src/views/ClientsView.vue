<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'

const clients = ref([])
const selectedId = ref(null)

const search = ref('')
const showForm = ref(false)
const editingId = ref(null)

const loading = ref(true)
const saving = ref(false)

const error = ref('')
const formError = ref('')
const success = ref('')

const history = ref([])
const historyLoading = ref(false)
const historyError = ref('')

// HU-05: equipos reales asociados a cada cliente.
const equipment = ref([])
const equipmentLoading = ref(true)
const equipmentError = ref('')
const showEquipmentForm = ref(false)
const savingEquipment = ref(false)
const equipmentFormError = ref('')

const equipmentTypes = [
  { value: 'CELULAR', label: 'Celular' },
  { value: 'NOTEBOOK', label: 'Notebook' },
  { value: 'PC', label: 'PC' },
  { value: 'TABLET', label: 'Tablet' },
  { value: 'OTRO', label: 'Otro' },
]

const emptyEquipmentForm = () => ({
  equipment_type: 'CELULAR',
  brand: '',
  model: '',
  imei: '',
  serial_number: '',
  color: '',
  observations: '',
})

const equipmentForm = ref(emptyEquipmentForm())

// HU-06: hoja de vida del equipo seleccionado.
const expandedEquipmentId = ref(null)
const equipmentHistory = ref([])
const equipmentHistoryLoading = ref(false)
const equipmentHistoryError = ref('')
let equipmentHistoryRequestId = 0

let historyRequestId = 0

const emptyForm = () => ({
  rut: '',
  name: '',
  phone: '',
  email: '',
})

const form = ref(emptyForm())

const fieldLabels = {
  rut: 'RUT',
  name: 'Nombre',
  phone: 'Teléfono',
  email: 'Correo electrónico',
  is_active: 'Estado',
}

// Normalizar RUT: 12.345.678-5 -> 123456785
function normalizeRut(value) {
  return String(value ?? '')
    .replace(/[^0-9kK]/g, '')
    .toUpperCase()
}

// Mostrar RUT: 123456785 -> 12.345.678-5
function formatRut(value) {
  const clean = normalizeRut(value)

  if (!clean) return ''
  if (clean.length === 1) return clean

  const body = clean.slice(0, -1)
  const verifier = clean.slice(-1)

  const formattedBody = body.replace(
    /\B(?=(\d{3})+(?!\d))/g,
    '.'
  )

  return `${formattedBody}-${verifier}`
}

// Dar formato al RUT mientras se escribe.
function onRutInput(event) {
  const clean = normalizeRut(event.target.value)
  const limited = clean.slice(0, 9)

  form.value.rut = formatRut(limited)
  event.target.value = form.value.rut
}

// Buscar por nombre, RUT, teléfono o correo.
const filteredClients = computed(() => {
  const term = search.value.trim().toLowerCase()

  if (!term) return clients.value

  const looksLikeRut = /^[0-9.kK-]+$/.test(term)

  const normalizedSearchRut = looksLikeRut
    ? normalizeRut(term)
    : ''

  return clients.value.filter((client) => {
    const normalText = [
      client.name,
      client.phone,
      client.email,
      formatRut(client.rut),
    ]
      .join(' ')
      .toLowerCase()

    const clientRut = normalizeRut(client.rut)

    return (
      normalText.includes(term) ||
      (
        normalizedSearchRut &&
        clientRut.includes(normalizedSearchRut)
      )
    )
  })
})

const selectedClient = computed(() =>
  clients.value.find(
    (client) => client.id === selectedId.value
  ) || null
)

const selectedEquipment = computed(() =>
  equipment.value.filter(
    (item) => Number(item.client) === Number(selectedId.value)
  )
)

function equipmentTypeLabel(value) {
  return equipmentTypes.find((item) => item.value === value)?.label || value
}

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

function formatChangeValue(field, value) {
  if (value === null || value === undefined || value === '') {
    return 'Sin dato'
  }

  if (field === 'rut') {
    return formatRut(value)
  }

  if (field === 'is_active') {
    return value ? 'Activo' : 'Inactivo'
  }

  return String(value)
}

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

// Cargar clientes desde Django.
async function loadClients() {
  loading.value = true
  error.value = ''

  try {
    const response = await authenticatedFetch('/api/clients/')

    if (!response.ok) {
      throw new Error('No fue posible cargar los clientes.')
    }

    const data = await response.json()

    clients.value = Array.isArray(data)
      ? data
      : data.results || []

    if (
      !clients.value.some(
        (client) => client.id === selectedId.value
      )
    ) {
      selectedId.value = clients.value[0]?.id ?? null
    }

  } catch (err) {
    clients.value = []
    selectedId.value = null

    error.value =
      err.message || 'Error al cargar los clientes.'

  } finally {
    loading.value = false
  }
}

// Consultar historial del cliente seleccionado.
async function loadHistory(clientId) {
  const requestId = ++historyRequestId

  history.value = []
  historyError.value = ''

  if (clientId === null || clientId === undefined) {
    historyLoading.value = false
    return
  }

  historyLoading.value = true

  try {
    const response = await authenticatedFetch(
      `/api/clients/${clientId}/history/`
    )

    if (!response.ok) {
      throw new Error(
        'No fue posible cargar el historial del cliente.'
      )
    }

    const data = await response.json()

    // Evitar mostrar datos de otro cliente si
    // se cambia rápidamente la selección.
    if (requestId !== historyRequestId) return

    history.value = Array.isArray(data)
      ? data
      : data.results || []

  } catch (err) {
    if (requestId === historyRequestId) {
      historyError.value =
        err.message || 'Error al cargar el historial.'
    }

  } finally {
    if (requestId === historyRequestId) {
      historyLoading.value = false
    }
  }
}

// Evitar que la hoja de vida de un equipo quede visible al cambiar de cliente.
function clearEquipmentHistory() {
  equipmentHistoryRequestId += 1
  expandedEquipmentId.value = null
  equipmentHistory.value = []
  equipmentHistoryLoading.value = false
  equipmentHistoryError.value = ''
}

// Consultar todas las órdenes vinculadas al mismo equipo en Django.
async function loadEquipmentHistory(equipmentId) {
  const requestId = ++equipmentHistoryRequestId

  expandedEquipmentId.value = equipmentId
  equipmentHistory.value = []
  equipmentHistoryError.value = ''
  equipmentHistoryLoading.value = true

  try {
    const response = await authenticatedFetch(
      `/api/devices/${equipmentId}/history/`
    )

    if (!response.ok) {
      throw new Error(
        response.status === 403
          ? 'No tienes permisos para consultar esta hoja de vida.'
          : 'No fue posible cargar el historial técnico del equipo.'
      )
    }

    const data = await response.json()
    if (requestId !== equipmentHistoryRequestId) return

    equipmentHistory.value = Array.isArray(data)
      ? data
      : data.results || []

  } catch (err) {
    if (requestId === equipmentHistoryRequestId) {
      equipmentHistoryError.value =
        err.message || 'Error al consultar la hoja de vida.'
    }

  } finally {
    if (requestId === equipmentHistoryRequestId) {
      equipmentHistoryLoading.value = false
    }
  }
}

function toggleEquipmentHistory(item) {
  if (expandedEquipmentId.value === item.id) {
    clearEquipmentHistory()
    return
  }

  loadEquipmentHistory(item.id)
}

// Cargar el listado de equipos desde la API real.
async function loadEquipment() {
  equipmentLoading.value = true
  equipmentError.value = ''

  try {
    const response = await authenticatedFetch('/api/devices/')

    if (!response.ok) {
      throw new Error('No fue posible cargar los equipos.')
    }

    const data = await response.json()
    equipment.value = Array.isArray(data) ? data : data.results || []

  } catch (err) {
    equipment.value = []
    equipmentError.value = err.message || 'Error al cargar los equipos.'

  } finally {
    equipmentLoading.value = false
  }
}

function openEquipmentForm() {
  if (!selectedClient.value || !selectedClient.value.is_active) return
  if (saving.value || savingEquipment.value) return

  equipmentForm.value = emptyEquipmentForm()
  equipmentFormError.value = ''
  success.value = ''
  showEquipmentForm.value = true
}

function cancelEquipmentForm() {
  if (savingEquipment.value) return

  showEquipmentForm.value = false
  equipmentFormError.value = ''
  equipmentForm.value = emptyEquipmentForm()
}

async function createEquipment() {
  if (savingEquipment.value || saving.value) return

  const client = selectedClient.value
  equipmentFormError.value = ''
  success.value = ''

  if (!client || !client.is_active) {
    equipmentFormError.value = 'Selecciona un cliente activo.'
    return
  }

  savingEquipment.value = true

  try {
    const response = await authenticatedFetch('/api/devices/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        client: client.id,
        equipment_type: equipmentForm.value.equipment_type,
        brand: equipmentForm.value.brand.trim(),
        model: equipmentForm.value.model.trim(),
        imei: equipmentForm.value.imei.trim(),
        serial_number: equipmentForm.value.serial_number.trim(),
        color: equipmentForm.value.color.trim(),
        observations: equipmentForm.value.observations.trim(),
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(formatApiErrors(data))
    }

    const created = await response.json()

    // Añadir solo el registro confirmado por Django.
    equipmentError.value = ''
    equipmentLoading.value = false
    equipment.value = [
      created,
      ...equipment.value.filter((item) => item.id !== created.id),
    ]

    showEquipmentForm.value = false
    equipmentForm.value = emptyEquipmentForm()
    success.value = `Equipo #${created.id} registrado correctamente.`

  } catch (err) {
    equipmentFormError.value =
      err.message || 'No fue posible registrar el equipo.'

  } finally {
    savingEquipment.value = false
  }
}

// Al seleccionar otro cliente, recargar historial y cerrar el formulario
// anterior para no asociar un equipo a un cliente equivocado.
watch(selectedId, loadHistory)
watch(selectedId, () => {
  clearEquipmentHistory()
  showEquipmentForm.value = false
  equipmentFormError.value = ''
})

// Abrir formulario para crear.
function openForm() {
  editingId.value = null
  form.value = emptyForm()

  formError.value = ''
  success.value = ''

  showForm.value = true
}

// Abrir formulario para editar.
function editClient(client) {
  if (!client || saving.value) return

  editingId.value = client.id

  form.value = {
    rut: formatRut(client.rut),
    name: client.name || '',
    phone: client.phone || '',
    email: client.email || '',
  }

  formError.value = ''
  success.value = ''

  showForm.value = true
}

function cancelForm() {
  if (saving.value) return

  showForm.value = false
  editingId.value = null

  form.value = emptyForm()
  formError.value = ''
}

// Crear o actualizar un cliente en Django.
async function saveClient() {
  if (saving.value) return

  const isEditing = editingId.value !== null
  const clientId = editingId.value

  saving.value = true
  formError.value = ''
  success.value = ''

  try {
    const payload = {
      rut: normalizeRut(form.value.rut),
      name: form.value.name.trim(),
      phone: form.value.phone.trim(),
      email: form.value.email.trim(),
    }

    const url = isEditing
      ? `/api/clients/${clientId}/`
      : '/api/clients/'

    const method = isEditing ? 'PATCH' : 'POST'

    const response = await authenticatedFetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(formatApiErrors(data))
    }

    const savedClient = await response.json()

    showForm.value = false
    editingId.value = null
    form.value = emptyForm()

    // Recargar desde la base de datos.
    await loadClients()

    selectedId.value = savedClient.id

    // Recargar también el historial.
    await loadHistory(savedClient.id)

    success.value = isEditing
      ? 'Cliente actualizado correctamente.'
      : 'Cliente registrado correctamente.'

  } catch (err) {
    formError.value =
      err.message || 'No fue posible guardar el cliente.'

  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadClients()
  loadEquipment()
})
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Clientes y equipos

      <template #subtitle>
        Directorio de clientes de Martini Cell.
      </template>

      <template #actions>
        <button
          class="btn btn-primary"
          :disabled="saving || savingEquipment"
          @click="openForm"
        >
          <i class="bi bi-plus-lg me-1"></i>
          Nuevo cliente
        </button>
      </template>
    </PageHeader>

    <!-- Mensajes -->
    <div
      v-if="success"
      class="alert alert-success"
      role="status"
    >
      {{ success }}
    </div>

    <div
      v-if="error"
      class="alert alert-danger"
      role="alert"
    >
      {{ error }}

      <button
        class="btn btn-sm btn-outline-danger ms-3"
        @click="loadClients"
      >
        Reintentar
      </button>
    </div>

    <!-- Formulario para crear o editar -->
    <div
      v-if="showForm"
      class="mc-card p-4 mb-4"
    >
      <h5 class="mb-3">
        {{
          editingId !== null
            ? 'Editar cliente'
            : 'Registrar nuevo cliente'
        }}
      </h5>

      <div
        v-if="formError"
        class="alert alert-danger"
        role="alert"
      >
        {{ formError }}
      </div>

      <form @submit.prevent="saveClient">
        <div class="row g-3">

          <div class="col-md-6">
            <label for="client-rut" class="form-label">
              RUT
            </label>

            <input
              id="client-rut"
              :value="form.rut"
              class="form-control"
              placeholder="12.345.678-5"
              maxlength="12"
              autocomplete="off"
              required
              :disabled="saving"
              @input="onRutInput"
            >

            <div class="form-text">
              Ejemplo: 12.345.678-5
            </div>
          </div>

          <div class="col-md-6">
            <label for="client-name" class="form-label">
              Nombre
            </label>

            <input
              id="client-name"
              v-model="form.name"
              class="form-control"
              required
              :disabled="saving"
            >
          </div>

          <div class="col-md-6">
            <label for="client-phone" class="form-label">
              Teléfono
            </label>

            <input
              id="client-phone"
              v-model="form.phone"
              class="form-control"
              required
              :disabled="saving"
            >
          </div>

          <div class="col-md-6">
            <label for="client-email" class="form-label">
              Correo electrónico (opcional)
            </label>

            <input
              id="client-email"
              v-model="form.email"
              type="email"
              class="form-control"
              :disabled="saving"
            >
          </div>

        </div>

        <div class="d-flex flex-wrap gap-2 mt-4">

          <button
            type="submit"
            class="btn btn-primary"
            :disabled="saving"
          >
            {{
              saving
                ? 'Guardando...'
                : editingId !== null
                  ? 'Guardar cambios'
                  : 'Guardar cliente'
            }}
          </button>

          <button
            type="button"
            class="btn btn-outline-secondary"
            :disabled="saving"
            @click="cancelForm"
          >
            Cancelar
          </button>

        </div>
      </form>
    </div>

    <!-- Directorio y detalle -->
    <div class="row g-3">

      <!-- Lista de clientes -->
      <div class="col-lg-5">
        <div class="mc-card p-3">

          <input
            v-model="search"
            class="form-control mb-3"
            placeholder="Buscar cliente..."
            aria-label="Buscar cliente"
          >

          <div
            v-if="loading"
            class="text-center py-4"
          >
            <div
              class="spinner-border text-primary"
              role="status"
            ></div>

            <div class="text-muted mt-2">
              Cargando clientes...
            </div>
          </div>

          <div
            v-else
            class="list-group list-group-flush"
          >
            <button
              v-for="client in filteredClients"
              :key="client.id"
              type="button"
              class="list-group-item list-group-item-action"
              :disabled="saving || savingEquipment"
              :class="{
                active: selectedId === client.id
              }"
              @click="selectedId = client.id"
            >
              <strong>{{ client.name }}</strong>

              <div class="small">
                RUT: {{ formatRut(client.rut) }}
              </div>

              <div class="small">
                {{ client.phone }}
              </div>
            </button>

            <div
              v-if="!error && filteredClients.length === 0"
              class="text-muted text-center py-4"
            >
              No se encontraron clientes.
            </div>
          </div>

        </div>
      </div>

      <!-- Detalle e historial -->
      <div class="col-lg-7">

        <div
          v-if="selectedClient"
          class="mc-card p-4"
        >
          <div class="d-flex flex-wrap justify-content-between gap-2">
            <div>
              <h5>{{ selectedClient.name }}</h5>

              <div class="text-muted">
                RUT: {{ formatRut(selectedClient.rut) }}
              </div>
            </div>

            <div>
              <button
                class="btn btn-outline-primary btn-sm"
                :disabled="saving || savingEquipment"
                @click="editClient(selectedClient)"
              >
                <i class="bi bi-pencil me-1"></i>
                Editar cliente
              </button>
            </div>
          </div>

          <div class="mt-3">
            <strong>Teléfono:</strong>
            {{ selectedClient.phone }}
          </div>

          <div class="mt-2">
            <strong>Correo:</strong>
            {{ selectedClient.email || 'No registrado' }}
          </div>

          <div class="mt-2">
            <strong>Estado:</strong>
            {{
              selectedClient.is_active
                ? 'Activo'
                : 'Inactivo'
            }}
          </div>

          <div class="mt-2 small text-muted">
            Registrado:
            {{ formatDate(selectedClient.created_at) }}

            <span v-if="selectedClient.created_by_username">
              por {{ selectedClient.created_by_username }}
            </span>
          </div>

          <hr>

          <!-- Equipos asociados: HU-05 -->
          <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
            <h6 class="mb-0">Equipos asociados</h6>

            <button
              type="button"
              class="btn btn-sm btn-outline-primary"
              :disabled="saving || savingEquipment || !selectedClient.is_active"
              @click="openEquipmentForm"
            >
              <i class="bi bi-plus-lg me-1"></i>
              Nuevo equipo
            </button>
          </div>

          <div
            v-if="!selectedClient.is_active"
            class="text-muted small mb-3"
          >
            No es posible registrar equipos nuevos en un cliente inactivo.
          </div>

          <div v-if="equipmentError" class="alert alert-danger" role="alert">
            {{ equipmentError }}
            <button
              type="button"
              class="btn btn-sm btn-outline-danger ms-2"
              @click="loadEquipment"
            >
              Reintentar
            </button>
          </div>

          <div v-if="showEquipmentForm" class="border rounded p-3 mb-3">
            <h6 class="mb-3">Registrar equipo para {{ selectedClient.name }}</h6>

            <div
              v-if="equipmentFormError"
              class="alert alert-danger"
              role="alert"
            >
              {{ equipmentFormError }}
            </div>

            <form @submit.prevent="createEquipment">
              <div class="row g-3">
                <div class="col-md-6">
                  <label for="equipment-type" class="form-label">Tipo de equipo</label>
                  <select
                    id="equipment-type"
                    v-model="equipmentForm.equipment_type"
                    class="form-select"
                    required
                    :disabled="savingEquipment"
                  >
                    <option
                      v-for="type in equipmentTypes"
                      :key="type.value"
                      :value="type.value"
                    >
                      {{ type.label }}
                    </option>
                  </select>
                </div>

                <div class="col-md-6">
                  <label for="equipment-brand" class="form-label">Marca</label>
                  <input
                    id="equipment-brand"
                    v-model="equipmentForm.brand"
                    class="form-control"
                    maxlength="100"
                    required
                    :disabled="savingEquipment"
                  >
                </div>

                <div class="col-md-6">
                  <label for="equipment-model" class="form-label">Modelo</label>
                  <input
                    id="equipment-model"
                    v-model="equipmentForm.model"
                    class="form-control"
                    maxlength="100"
                    required
                    :disabled="savingEquipment"
                  >
                </div>

                <div class="col-md-6">
                  <label for="equipment-color" class="form-label">Color (opcional)</label>
                  <input
                    id="equipment-color"
                    v-model="equipmentForm.color"
                    class="form-control"
                    maxlength="50"
                    :disabled="savingEquipment"
                  >
                </div>

                <div class="col-md-6">
                  <label for="equipment-imei" class="form-label">IMEI (opcional)</label>
                  <input
                    id="equipment-imei"
                    v-model="equipmentForm.imei"
                    class="form-control"
                    maxlength="30"
                    autocomplete="off"
                    :disabled="savingEquipment"
                  >
                </div>

                <div class="col-md-6">
                  <label for="equipment-serial" class="form-label">N.º de serie (opcional)</label>
                  <input
                    id="equipment-serial"
                    v-model="equipmentForm.serial_number"
                    class="form-control"
                    maxlength="100"
                    autocomplete="off"
                    :disabled="savingEquipment"
                  >
                </div>

                <div class="col-12">
                  <label for="equipment-observations" class="form-label">Observaciones (opcional)</label>
                  <textarea
                    id="equipment-observations"
                    v-model="equipmentForm.observations"
                    class="form-control"
                    rows="2"
                    :disabled="savingEquipment"
                  ></textarea>
                </div>
              </div>

              <div class="d-flex flex-wrap gap-2 mt-3">
                <button
                  type="submit"
                  class="btn btn-primary"
                  :disabled="savingEquipment"
                >
                  {{ savingEquipment ? 'Guardando...' : 'Guardar equipo' }}
                </button>
                <button
                  type="button"
                  class="btn btn-outline-secondary"
                  :disabled="savingEquipment"
                  @click="cancelEquipmentForm"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>

          <div v-if="equipmentLoading" class="text-muted small">
            Cargando equipos...
          </div>
          <div
            v-else-if="!equipmentError && selectedEquipment.length === 0"
            class="text-muted small"
          >
            Este cliente aún no tiene equipos registrados.
          </div>
          <div v-else-if="!equipmentError" class="d-flex flex-column gap-2">
            <div
              v-for="item in selectedEquipment"
              :key="item.id"
              class="border rounded p-3"
            >
              <div class="d-flex justify-content-between gap-2">
                <strong>{{ item.brand }} {{ item.model }}</strong>
                <span class="badge text-bg-secondary">Equipo #{{ item.id }}</span>
              </div>
              <div class="small text-muted mt-1">
                {{ equipmentTypeLabel(item.equipment_type) }}
                <span v-if="item.color"> · {{ item.color }}</span>
              </div>
              <div v-if="item.imei" class="small mt-1">IMEI: {{ item.imei }}</div>
              <div v-if="item.serial_number" class="small mt-1">
                N.º de serie: {{ item.serial_number }}
              </div>
              <div v-if="item.observations" class="small mt-1">
                Observaciones: {{ item.observations }}
              </div>

              <!-- HU-06: historial de atenciones del equipo. -->
              <button
                type="button"
                class="btn btn-sm btn-outline-primary mt-3"
                :aria-expanded="expandedEquipmentId === item.id"
                @click="toggleEquipmentHistory(item)"
              >
                <i class="bi bi-clock-history me-1"></i>
                {{ expandedEquipmentId === item.id ? 'Ocultar hoja de vida' : 'Ver hoja de vida' }}
              </button>

              <div
                v-if="expandedEquipmentId === item.id"
                class="border-top mt-3 pt-3"
              >
                <h6>Historial técnico · Equipo #{{ item.id }}</h6>

                <div v-if="equipmentHistoryLoading" class="text-muted small">
                  Cargando historial técnico...
                </div>

                <div v-else-if="equipmentHistoryError" class="alert alert-danger" role="alert">
                  {{ equipmentHistoryError }}
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-danger ms-2"
                    @click="loadEquipmentHistory(item.id)"
                  >
                    Reintentar
                  </button>
                </div>

                <div v-else-if="equipmentHistory.length === 0" class="text-muted small">
                  Este equipo todavía no tiene órdenes de atención registradas.
                </div>

                <div v-else class="d-flex flex-column gap-3">
                  <div
                    v-for="order in equipmentHistory"
                    :key="order.id"
                    class="border rounded p-3"
                  >
                    <div class="fw-semibold">
                      Orden #{{ order.id }} · {{ order.tracking_code }}
                    </div>
                    <div class="small text-muted mb-2">
                      Ingreso: {{ formatDate(order.received_at) }}
                    </div>
                    <div class="small mt-1">
                      <strong>Falla reportada:</strong>
                      {{ order.reported_issue || 'Sin información' }}
                    </div>
                    <div v-if="order.initial_observations" class="small mt-1">
                      <strong>Observaciones iniciales:</strong>
                      {{ order.initial_observations }}
                    </div>
                    <div class="small mt-1">
                      <strong>Diagnóstico:</strong>
                      {{ order.diagnosis || 'Aún sin informe técnico' }}
                    </div>
                    <div class="small mt-1">
                      <strong>Reparación:</strong>
                      {{ order.repair_actions || 'Aún sin informe técnico' }}
                    </div>
                    <div v-if="order.repair_observations" class="small mt-1">
                      <strong>Observaciones de reparación:</strong>
                      {{ order.repair_observations }}
                    </div>
                    <div v-if="order.parts_description" class="small mt-1">
                      <strong>Repuestos:</strong>
                      {{ order.parts_description }}
                    </div>
                    <div class="small mt-1">
                      <strong>Resultado:</strong>
                      {{ order.result_display || 'Pendiente de informe técnico' }}
                    </div>
                    <div v-if="order.technician_username" class="small mt-1">
                      <strong>Técnico:</strong>
                      {{ order.technician_username }}
                    </div>
                    <div class="small text-muted mt-2">
                      El acceso al detalle de esta orden se conectará en HU-07.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <hr>

          <!-- Historial de cambios de HU-04 -->
          <h6 class="mb-3">
            <i class="bi bi-clock-history me-1"></i>
            Historial de modificaciones
          </h6>

          <div
            v-if="historyLoading"
            class="text-muted"
          >
            Cargando historial...
          </div>

          <div
            v-else-if="historyError"
            class="alert alert-danger"
            role="alert"
          >
            {{ historyError }}

            <button
              class="btn btn-sm btn-outline-danger ms-2"
              @click="loadHistory(selectedClient.id)"
            >
              Reintentar
            </button>
          </div>

          <div
            v-else-if="history.length === 0"
            class="text-muted small"
          >
            Este cliente aún no tiene modificaciones registradas.
          </div>

          <div
            v-else
            class="d-flex flex-column gap-3"
          >
            <div
              v-for="entry in history"
              :key="entry.id"
              class="border rounded p-3"
            >
              <div class="small text-muted mb-2">
                <i class="bi bi-calendar-event me-1"></i>
                {{ formatDate(entry.changed_at) }}

                <span class="ms-2">
                  <i class="bi bi-person me-1"></i>
                  {{
                    entry.changed_by_username ||
                    'Usuario no disponible'
                  }}
                </span>
              </div>

              <div
                v-for="(change, field) in entry.changes"
                :key="field"
                class="small mb-2"
              >
                <strong>
                  {{ fieldLabels[field] || field }}:
                </strong>

                <div class="text-muted">
                  Anterior:
                  {{ formatChangeValue(field, change.from) }}
                </div>

                <div>
                  Nuevo:
                  {{ formatChangeValue(field, change.to) }}
                </div>
              </div>
            </div>
          </div>

        </div>

        <div
          v-else-if="!loading"
          class="mc-card p-4 text-muted"
        >
          Selecciona un cliente para ver su información.
        </div>

      </div>
    </div>
  </AdminLayout>
</template>
