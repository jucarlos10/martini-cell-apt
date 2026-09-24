
<script setup>
import { onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'

const users = ref([])
const loading = ref(true)
const saving = ref(false)
const showForm = ref(false)
const error = ref('')
const formError = ref('')
const success = ref('')

const emptyForm = () => ({
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  role: 'TECH',
  password: '',
  confirmPassword: '',
})

const form = ref(emptyForm())

async function loadUsers() {
  loading.value = true
  error.value = ''

  try {
    const response = await authenticatedFetch('/api/users/')

    if (response.status === 403) {
      throw new Error(
        'No tienes permisos para consultar los usuarios.'
      )
    }

    if (!response.ok) {
      throw new Error('No fue posible cargar los usuarios.')
    }

    const data = await response.json()

    users.value = Array.isArray(data)
      ? data
      : data.results || []
  } catch (err) {
    users.value = []
    error.value = err.message || 'Error al cargar los usuarios.'
  } finally {
    loading.value = false
  }
}

function getFullName(user) {
  return [user.first_name, user.last_name]
    .filter(Boolean)
    .join(' ') || 'Sin nombre registrado'
}

function openForm() {
  form.value = emptyForm()
  formError.value = ''
  success.value = ''
  showForm.value = true
}

function cancelForm() {
  showForm.value = false
  formError.value = ''
  form.value = emptyForm()
}

function formatApiErrors(data) {
  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (!data || typeof data !== 'object') {
    return 'No fue posible guardar el usuario.'
  }

  return Object.entries(data)
    .map(([field, messages]) => {
      const text = Array.isArray(messages)
        ? messages.join(' ')
        : String(messages)

      return `${field}: ${text}`
    })
    .join(' ')
}

async function createUser() {
  if (saving.value) return

  formError.value = ''
  success.value = ''

  if (form.value.password !== form.value.confirmPassword) {
    formError.value = 'Las contraseñas no coinciden.'
    return
  }

  saving.value = true

  try {
    const response = await authenticatedFetch('/api/users/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: form.value.username.trim(),
        first_name: form.value.first_name.trim(),
        last_name: form.value.last_name.trim(),
        email: form.value.email.trim(),
        role: form.value.role,
        password: form.value.password,
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)

      if (response.status === 403) {
        throw new Error(
          'No tienes permisos para crear usuarios.'
        )
      }

      throw new Error(formatApiErrors(data))
    }

    showForm.value = false
    form.value = emptyForm()

    success.value = 'Usuario creado correctamente.'
    await loadUsers()
  } catch (err) {
    formError.value = err.message || 'Error al crear el usuario.'
  } finally {
    saving.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Usuarios y roles

      <template #subtitle>
        Usuarios registrados en Martini Cell.
      </template>

      <template #actions>
        <button
          class="btn btn-primary"
          :disabled="saving"
          @click="openForm"
        >
          <i class="bi bi-plus-lg me-1"></i>
          Nuevo usuario
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
        @click="loadUsers"
      >
        Reintentar
      </button>
    </div>

    <!-- Formulario para crear usuarios -->
    <div v-if="showForm" class="mc-card p-4 mb-4">
      <h5 class="mb-3">Registrar nuevo usuario</h5>

      <div
        v-if="formError"
        class="alert alert-danger"
        role="alert"
      >
        {{ formError }}
      </div>

      <form @submit.prevent="createUser">
        <div class="row g-3">
          <div class="col-md-6">
            <label for="username" class="form-label">
              Usuario
            </label>

            <input
              id="username"
              v-model="form.username"
              class="form-control"
              autocomplete="off"
              required
              :disabled="saving"
            >
          </div>

          <div class="col-md-6">
            <label for="email" class="form-label">
              Correo electrónico
            </label>

            <input
              id="email"
              v-model="form.email"
              type="email"
              class="form-control"
              autocomplete="off"
              :disabled="saving"
            >
          </div>

          <div class="col-md-6">
            <label for="first_name" class="form-label">
              Nombre
            </label>

            <input
              id="first_name"
              v-model="form.first_name"
              class="form-control"
              required
              :disabled="saving"
            >
          </div>

          <div class="col-md-6">
            <label for="last_name" class="form-label">
              Apellido
            </label>

            <input
              id="last_name"
              v-model="form.last_name"
              class="form-control"
              required
              :disabled="saving"
            >
          </div>

          <div class="col-md-6">
            <label for="role" class="form-label">
              Rol
            </label>

            <select
              id="role"
              v-model="form.role"
              class="form-select"
              :disabled="saving"
            >
              <option value="ADMIN">Administrador</option>
              <option value="TECH">Técnico</option>
              <option value="HELPER">Ayudante</option>
            </select>
          </div>

          <div class="col-md-6">
            <label for="password" class="form-label">
              Contraseña
            </label>

            <input
              id="password"
              v-model="form.password"
              type="password"
              class="form-control"
              autocomplete="new-password"
              required
              :disabled="saving"
            >
          </div>

          <div class="col-md-6">
            <label for="confirmPassword" class="form-label">
              Confirmar contraseña
            </label>

            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              class="form-control"
              autocomplete="new-password"
              required
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
                : 'Guardar usuario'
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

    <!-- Listado de usuarios reales -->
    <div v-if="loading" class="mc-card p-4 text-center">
      <div
        class="spinner-border text-primary mb-2"
        role="status"
      ></div>

      <div class="text-muted">Cargando usuarios...</div>
    </div>

    <div v-else-if="!error" class="mc-card p-3 table-responsive">
      <table class="table mb-0">
        <thead>
          <tr>
            <th>Usuario</th>
            <th>Nombre</th>
            <th>Rol</th>
            <th>Estado</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>

            <td>{{ getFullName(u) }}</td>

            <td>{{ u.role_display || u.role }}</td>

            <td>
              <span
                class="badge"
                :class="
                  u.is_active
                    ? 'text-bg-success'
                    : 'text-bg-secondary'
                "
              >
                {{ u.is_active ? 'Activo' : 'Inactivo' }}
              </span>
            </td>

            <td class="text-end">
              <button
                class="btn btn-sm btn-outline-secondary"
                disabled
              >
                {{ u.is_active ? 'Desactivar' : 'Activar' }}
              </button>
            </td>
          </tr>

          <tr v-if="users.length === 0">
            <td colspan="5" class="text-center text-muted py-4">
              No hay usuarios registrados.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </AdminLayout>
</template>