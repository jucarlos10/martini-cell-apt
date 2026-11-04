
<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { startSession } from '../services/auth'

const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)

watch([username, password], () => {
  error.value = ''
})

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
        <div class="login-brand">
          <span class="login-brand-mark" aria-hidden="true">
            <i class="bi bi-tools"></i>
          </span>
          <div>
            <div class="login-brand-name">MARTINI CELL</div>
            <div class="mc-muted small">Gestión de servicios técnicos</div>
          </div>
        </div>

        <div class="login-intro">
          <p class="login-eyebrow">Acceso del equipo</p>
          <h1>Bienvenido de nuevo</h1>
          <p>Ingresa para revisar órdenes, responder consultas y continuar el trabajo del taller.</p>
        </div>

        <div
          v-if="error"
          id="login-error"
          class="alert alert-danger py-2"
          role="alert"
        >
          {{ error }}
        </div>

        <label for="username" class="form-label fw-semibold">Usuario</label>
        <input
          id="username"
          v-model="username"
          name="username"
          class="form-control login-input mb-3"
          autocomplete="username"
          :aria-describedby="error ? 'login-error' : undefined"
          required
          :disabled="loading"
        >

        <label for="password" class="form-label fw-semibold">Contraseña</label>
        <div class="password-field mb-4">
          <input
            id="password"
            v-model="password"
            name="password"
            :type="showPassword ? 'text' : 'password'"
            class="form-control login-input"
            autocomplete="current-password"
            :aria-describedby="error ? 'login-error' : undefined"
            required
            :disabled="loading"
          >
          <button
            type="button"
            class="password-toggle"
            :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
            :aria-pressed="showPassword"
            :disabled="loading"
            @click="showPassword = !showPassword"
          >
            <i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'" aria-hidden="true"></i>
          </button>
        </div>

        <button
          type="submit"
          class="btn btn-primary login-submit w-100"
          :disabled="loading"
        >
          <span
            v-if="loading"
            class="spinner-border spinner-border-sm me-2"
            aria-hidden="true"
          ></span>
          {{ loading ? 'Iniciando sesión...' : 'Iniciar sesión' }}
        </button>

        <div class="login-separator"><span>¿Vienes a consultar una reparación?</span></div>

        <router-link
          to="/consulta"
          class="btn btn-outline-primary login-public-link w-100"
        >
          <i class="bi bi-search me-2"></i>
          Consultar reparación
        </router-link>

      </form>
    </section>

    <section class="login-hero">
      <div class="login-hero-content">
        <span class="login-hero-label">MARTINI CELL · PLATAFORMA DE GESTIÓN</span>
        <h2>Una vista clara de cada reparación.</h2>
        <p>Desde la recepción hasta la entrega, con el equipo y el cliente informados en cada etapa.</p>

        <div class="login-hero-flow" aria-label="Etapas principales de la plataforma">
          <div><i class="bi bi-box-arrow-in-down" aria-hidden="true"></i><span>Registrar el ingreso</span></div>
          <div><i class="bi bi-activity" aria-hidden="true"></i><span>Seguir el avance</span></div>
          <div><i class="bi bi-chat-dots" aria-hidden="true"></i><span>Responder consultas</span></div>
        </div>
      </div>
    </section>
  </div>
</template>
