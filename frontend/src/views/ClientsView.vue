<script setup>
import { computed, onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'

const clients = ref([])
const selectedId = ref(null)

const search = ref('')
const showForm = ref(false)
const loading = ref(true)
const saving = ref(false)

const error = ref('')
const formError = ref('')
const success = ref('')

const emptyForm = () => ({
  rut: '',
  name: '',
  phone: '',
  email: '',
})

const form = ref(emptyForm())

// Quita puntos, guion y cualquier otro carácter del RUT.
// Ejemplo: 12.345.678-5 -> 123456785
function normalizeRut(value) {
  return String(value ?? '')
    .replace(/[^0-9kK]/g, '')
    .toUpperCase()
}

// Formatea un RUT para mostrarlo de manera legible.
// Ejemplo: 123456785 -> 12.345.678-5
function formatRut(value) {
  const clean = normalizeRut(value)

  if (!clean) {
    return ''
  }

  if (clean.length === 1) {
    return clean
  }

  const body = clean.slice(0, -1)
  const verifier = clean.slice(-1)

  const formattedBody = body.replace(
    /\B(?=(\d{3})+(?!\d))/g,
    '.'
  )

  return `${formattedBody}-${verifier}`
}

// Formatea automáticamente el RUT mientras se escribe.
function onRutInput(event) {
  const clean = normalizeRut(event.target.value)

  // Un RUT chileno ocupa como máximo 9 caracteres
  // sin contar puntos ni guion.
  const limited = clean.slice(0, 9)

  form.value.rut = formatRut(limited)
}

const filteredClients = computed(() => {
  const term = search.value.trim().toLowerCase()

  if (!term) {
    return clients.value
  }

  const normalizedSearchRut = normalizeRut(term)

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

    // Mantener el cliente seleccionado si todavía existe.
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

function openForm() {
  form.value = emptyForm()

  formError.value = ''
  success.value = ''

  showForm.value = true
}

function cancelForm() {
  if (saving.value) return

  form.value = emptyForm()
  formError.value = ''
  showForm.value = false
}

function formatApiErrors(data) {
  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (!data || typeof data !== 'object') {
    return 'No fue posible guardar el cliente.'
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

async function createClient() {
  if (saving.value) return

  saving.value = true
  formError.value = ''
  success.value = ''

  try {
    const response = await authenticatedFetch(
      '/api/clients/',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          rut: form.value.rut.trim(),
          name: form.value.name.trim(),
          phone: form.value.phone.trim(),
          email: form.value.email.trim(),
        }),
      }
    )

    if (!response.ok) {
      const data = await response.json().catch(() => null)

      throw new Error(
        formatApiErrors(data)
      )
    }

    const createdClient = await response.json()

    showForm.value = false
    form.value = emptyForm()

    // Volver a consultar Django para mostrar los datos reales.
    await loadClients()

    selectedId.value = createdClient.id

    success.value =
      'Cliente registrado correctamente.'

  } catch (err) {
    formError.value =
      err.message ||
      'No fue posible registrar el cliente.'

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

    <!-- Formulario de registro -->
    <div
      v-if="showForm"
      class="mc-card p-4 mb-4"
    >
      <h5 class="mb-3">
        Registrar nuevo cliente
      </h5>

      <div
        v-if="formError"
        class="alert alert-danger"
        role="alert"
      >
        {{ formError }}
      </div>

      <form @submit.prevent="createClient">
        <div class="row g-3">

          <div class="col-md-6">
            <label
              for="client-rut"
              class="form-label"
            >
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
            <label
              for="client-name"
              class="form-label"
            >
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
            <label
              for="client-phone"
              class="form-label"
            >
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
            <label
              for="client-email"
              class="form-label"
            >
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
              <strong>
                {{ client.name }}
              </strong>

              <div class="small">
                RUT: {{ formatRut(client.rut) }}
              </div>

              <div class="small">
                {{ client.phone }}
              </div>
            </button>

            <div
              v-if="
                !error &&
                filteredClients.length === 0
              "
              class="text-muted text-center py-4"
            >
              No se encontraron clientes.
            </div>
          </div>
        </div>
      </div>

      <!-- Detalle del cliente -->
      <div class="col-lg-7">
        <div
          v-if="selectedClient"
          class="mc-card p-4"
        >
          <h5>
            {{ selectedClient.name }}
          </h5>

          <div class="text-muted">
            RUT: {{ formatRut(selectedClient.rut) }}
          </div>

          <div class="mt-3">
            <strong>Teléfono:</strong>
            {{ selectedClient.phone }}
          </div>

          <div class="mt-2">
            <strong>Correo:</strong>

            {{
              selectedClient.email ||
              'No registrado'
            }}
          </div>

          <div class="mt-2">
            <strong>Estado:</strong>

            {{
              selectedClient.is_active
                ? 'Activo'
                : 'Inactivo'
            }}
          </div>

          <hr>

          <h6>Equipos asociados</h6>

          <div class="text-muted small">
            Conectaremos los equipos reales en HU-05.
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