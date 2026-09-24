
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

// Al seleccionar otro cliente, cargar su historial.
watch(selectedId, loadHistory)

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

onMounted(loadClients)
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
          :disabled="saving"
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
                :disabled="saving"
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

          <h6>Equipos asociados</h6>

          <div class="text-muted small">
            Conectaremos los equipos reales en HU-05.
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