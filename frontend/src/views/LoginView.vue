
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { startSession } from '../services/auth'

const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function login() {
  if (loading.value) return

  error.value = ''
  loading.value = true

  try {
    await startSession(username.value.trim(), password.value)
    await router.push('/panel')
  } catch (err) {
    error.value = err.message || 'No fue posible iniciar sesión.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <section class="login-panel">
      <form class="login-form" @submit.prevent="login">

        <div class="mb-4">
          <div class="fs-4 fw-bold" style="color: var(--mc-navy)">
            <i class="bi bi-tools me-2"></i>
            MARTINI CELL
          </div>
          <div class="mc-muted">
            Gestión de servicios técnicos
          </div>
        </div>

        <div v-if="error" class="alert alert-danger py-2" role="alert">
          {{ error }}
        </div>

        <label for="username" class="form-label">Usuario</label>
        <input
          id="username"
          v-model="username"
          class="form-control mb-3"
          autocomplete="username"
          required
          :disabled="loading"
        >

        <label for="password" class="form-label">Contraseña</label>
        <input
          id="password"
          v-model="password"
          type="password"
          class="form-control mb-3"
          autocomplete="current-password"
          required
          :disabled="loading"
        >

        <button
          type="submit"
          class="btn btn-primary w-100"
          :disabled="loading"
        >
          <span
            v-if="loading"
            class="spinner-border spinner-border-sm me-2"
            aria-hidden="true"
          ></span>
          {{ loading ? 'Iniciando sesión...' : 'Iniciar sesión' }}
        </button>

        <div class="text-center my-3 text-muted">o</div>

        <router-link
          to="/consulta"
          class="btn btn-outline-primary w-100"
        >
          <i class="bi bi-search me-2"></i>
          Consultar reparación
        </router-link>

      </form>
    </section>

    <section class="login-hero">
      <h2 class="display-6 fw-bold">
        Reparamos.<br>
        Conectamos.<br>
        Acompañamos.
      </h2>
      <p class="opacity-75">
        Plataforma de gestión de servicios técnicos.
      </p>
    </section>
  </div>
</template>