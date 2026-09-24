
<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'

import {
  authenticatedFetch,
  getAuthenticatedUser,
  getCurrentUser,
} from '../services/auth'

const router = useRouter()

const users = ref([])
const loading = ref(true)
const saving = ref(false)
const updatingId = ref(null)

const showForm = ref(false)
const editingId = ref(null)

const error = ref('')
const formError = ref('')
const actionError = ref('')
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
  editingId.value = null
  form.value = emptyForm()

  formError.value = ''
  actionError.value = ''
  success.value = ''

  showForm.value = true
}

function editUser(user) {
  if (saving.value || updatingId.value !== null) return

  editingId.value = user.id

  form.value = {
    username: user.username || '',
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    email: user.email || '',
    role: user.role,
    password: '',
    confirmPassword: '',
  }

  formError.value = ''
  actionError.value = ''
  success.value = ''

  showForm.value = true
}

function cancelForm() {
  if (saving.value) return

  showForm.value = false
  editingId.value = null

  formError.value = ''
  form.value = emptyForm()
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
      const text = Array.isArray(messages)
        ? messages.join(' ')
        : String(messages)

      return `${field}: ${text}`
    })
    .join(' ')
}

async function saveUser() {
  if (saving.value || updatingId.value !== null) return

  formError.value = ''
  actionError.value = ''
  success.value = ''

  const isEditing = editingId.value !== null

  if (!isEditing && !form.value.password) {
    formError.value = 'Debes ingresar una contraseña.'
    return
  }

  if (form.value.password !== form.value.confirmPassword) {
    formError.value = 'Las contraseñas no coinciden.'
    return
  }

  saving.value = true

  try {
    const payload = {
      username: form.value.username.trim(),
      first_name: form.value.first_name.trim(),
      last_name: form.value.last_name.trim(),
      email: form.value.email.trim(),
      role: form.value.role,
    }

    // Al crear, la contraseña es obligatoria.
    // Al editar, solo la enviamos si se ingresó una nueva.
    if (form.value.password) {
      payload.password = form.value.password
    }

    const url = isEditing
      ? `/api/users/${editingId.value}/`
      : '/api/users/'

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

      if (response.status === 403) {
        throw new Error(
          'No tienes permisos para realizar esta operación.'
        )
      }

      throw new Error(formatApiErrors(data))
    }

    const editedUserId = editingId.value

    showForm.value = false
    editingId.value = null
    form.value = emptyForm()

    success.value = isEditing
      ? 'Usuario actualizado correctamente.'
      : 'Usuario creado correctamente.'

    // Si el administrador editó su propia cuenta,
    // actualizamos también su perfil almacenado en sesión.
    if (
      isEditing &&
      editedUserId === getCurrentUser()?.id
    ) {
      const currentUser = await getAuthenticatedUser()

      if (currentUser?.role !== 'ADMIN') {
        await router.replace('/panel')
        return
      }
    }

    // Volvemos a obtener los datos reales desde PostgreSQL.
    await loadUsers()

  } catch (err) {
    formError.value =
      err.message || 'No fue posible guardar el usuario.'

  } finally {
    saving.value = false
  }
}

async function toggleUser(user) {
  if (updatingId.value !== null || saving.value) return

  const nextActive = !user.is_active

  if (
    !nextActive &&
    !window.confirm(
      `¿Estás seguro de que deseas desactivar al usuario ${user.username}?`
    )
  ) {
    return
  }

  updatingId.value = user.id
  actionError.value = ''
  success.value = ''

  try {
    const response = await authenticatedFetch(
      `/api/users/${user.id}/`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_active: nextActive,
        }),
      }
    )

    if (!response.ok) {
      const data = await response.json().catch(() => null)

      if (response.status === 403) {
        throw new Error(
          'No tienes permisos para modificar usuarios.'
        )
      }

      throw new Error(formatApiErrors(data))
    }

    const updatedUser = await response.json()

    // Solo cambiamos la tabla cuando Django confirma.
    users.value = users.value.map((item) =>
      item.id === user.id
        ? {
            ...item,
            is_active: updatedUser.is_active,
          }
        : item
    )

    success.value = updatedUser.is_active
      ? 'Usuario activado correctamente.'
      : 'Usuario desactivado correctamente.'

  } catch (err) {
    actionError.value =
      err.message || 'No fue posible cambiar el estado del usuario.'

  } finally {
    updatingId.value = null
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
          :disabled="saving || updatingId !== null"
          @click="openForm"
        >
          <i class="bi bi-plus-lg me-1"></i>
          Nuevo usuario
        </button>
      </template>
    </PageHeader>

    <!-- Mensajes generales -->
    <div
      v-if="success"
      class="alert alert-success"
      role="status"
    >
      {{ success }}
    </div>

    <div
      v-if="actionError"
      class="alert alert-danger"
      role="alert"
    >
      {{ actionError }}
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

    <!-- Formulario para crear o editar usuarios -->
    <div v-if="showForm" class="mc-card p-4 mb-4">
      <h5 class="mb-3">
        {{
          editingId !== null
            ? 'Editar usuario'
            : 'Registrar nuevo usuario'
        }}
      </h5>

      <div
        v-if="formError"
        class="alert alert-danger"
        role="alert"
      >
        {{ formError }}
      </div>

      <form @submit.prevent="saveUser">
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
              {{
                editingId !== null
                  ? 'Nueva contraseña (opcional)'
                  : 'Contraseña'
              }}
            </label>

            <input
              id="password"
              v-model="form.password"
              type="password"
              class="form-control"
              autocomplete="new-password"
              :required="editingId === null"
              :disabled="saving"
            >

            <div
              v-if="editingId !== null"
              class="form-text"
            >
              Déjala vacía para conservar la contraseña actual.
            </div>
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
              :required="editingId === null || !!form.password"
              :disabled="saving"
            >
          </div>

        </div>

        <div class="d-flex flex-wrap gap-2 mt-4">
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="saving || updatingId !== null"
          >
            {{
              saving
                ? 'Guardando...'
                : editingId !== null
                  ? 'Guardar cambios'
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

      <div class="text-muted">
        Cargando usuarios...
      </div>
    </div>

    <div v-else-if="!error" class="mc-card p-3 table-responsive">
      <table class="table mb-0">
        <thead>
          <tr>
            <th>Usuario</th>
            <th>Nombre</th>
            <th>Rol</th>
            <th>Estado</th>
            <th>Acciones</th>
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

            <td>
              <div class="d-flex flex-wrap gap-2">

                <button
                  class="btn btn-sm btn-outline-primary"
                  :disabled="saving || updatingId !== null"
                  @click="editUser(u)"
                >
                  <i class="bi bi-pencil me-1"></i>
                  Editar
                </button>

                <button
                  class="btn btn-sm btn-outline-secondary"
                  :disabled="saving || updatingId !== null"
                  @click="toggleUser(u)"
                >
                  {{
                    updatingId === u.id
                      ? 'Guardando...'
                      : u.is_active
                        ? 'Desactivar'
                        : 'Activar'
                  }}
                </button>

              </div>
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