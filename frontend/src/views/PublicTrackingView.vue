<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const code = ref('')
const data = ref(null)
const error = ref('')
const loading = ref(false)

const chatOpen = ref(false)
const chatData = ref(null)
const chatMessage = ref('')
const chatError = ref('')
const chatLoading = ref(false)
const chatSending = ref(false)
const chatMessagesContainer = ref(null)

const CHAT_POLL_INTERVAL = 5000

let chatController = null
let chatPollTimer = null
let chatRequest = 0

const notFoundMessage =
  'No se encontró una orden con ese código. Revísalo e inténtalo nuevamente.'

const trackingSteps = [
  {
    key: 'RECEIVED',
    label: 'Ingresado',
    description: 'Tu equipo fue recibido por Martini Cell.',
  },
  {
    key: 'DIAGNOSIS',
    label: 'Diagnóstico',
    description: 'El equipo está siendo revisado para identificar la falla.',
  },
  {
    key: 'AUTHORIZATION',
    label: 'Autorización',
    description: 'Se está gestionando la autorización para continuar.',
  },
  {
    key: 'PART',
    label: 'Espera de repuesto',
    description: 'Se requiere un repuesto para continuar con el servicio.',
    optional: true,
  },
  {
    key: 'REPAIR',
    label: 'Reparación',
    description: 'El equipo se encuentra en proceso de reparación.',
  },
  {
    key: 'TESTING',
    label: 'Pruebas',
    description: 'Se están realizando pruebas para verificar el funcionamiento.',
  },
  {
    key: 'READY',
    label: 'Listo para retiro',
    description: 'El equipo está listo para ser retirado.',
  },
  {
    key: 'DELIVERED',
    label: 'Entregado',
    description: 'El equipo fue entregado al cliente.',
  },
  {
    key: 'CLOSED',
    label: 'Cerrado',
    description: 'El servicio técnico fue finalizado.',
  },
]

const mainStepKeys = trackingSteps.map((step) => step.key)

let currentRequest = 0
let controller = null

watch(code, () => {
  currentRequest += 1

  if (controller) controller.abort()

  controller = null
  data.value = null
  error.value = ''
  loading.value = false

  resetChat()
})

function formatDate(value) {
  if (!value) return ''

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return ''

  return date.toLocaleString('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

function historyForStatus(status) {
  if (!data.value?.history) return []

  return data.value.history.filter(
    (entry) => entry.status === status,
  )
}

function getStatusDate(status) {
  const entries = historyForStatus(status)

  if (!entries.length) return ''

  return entries[entries.length - 1].changed_at
}

function hasVisited(status) {
  return historyForStatus(status).length > 0
}

function getStepState(step) {
  if (!data.value) return 'pending'

  if (data.value.status === step.key) {
    return 'current'
  }

  if (hasVisited(step.key)) {
    return 'completed'
  }

  if (step.optional) {
    const currentIndex = mainStepKeys.indexOf(data.value.status)
    const stepIndex = mainStepKeys.indexOf(step.key)

    if (currentIndex > stepIndex) {
      return 'skipped'
    }
  }

  return 'pending'
}

function getStepText(step) {
  const state = getStepState(step)

  if (state === 'current') return 'Estado actual'
  if (state === 'completed') return 'Completado'
  if (state === 'skipped') return 'No requerido'

  return 'Pendiente'
}

function getStepIcon(step) {
  const state = getStepState(step)

  if (state === 'completed') return 'bi-check-lg'
  if (state === 'current') return 'bi-geo-alt-fill'
  if (state === 'skipped') return 'bi-dash-lg'

  return 'bi-circle'
}

function hasRejectedStatus() {
  if (!data.value) return false

  return (
    data.value.status === 'REJECTED'
    || hasVisited('REJECTED')
  )
}

function rejectedDate() {
  return getStatusDate('REJECTED')
}

function stopChatPolling() {
  if (chatPollTimer) {
    window.clearInterval(chatPollTimer)
    chatPollTimer = null
  }
}

function abortChatRequest() {
  chatRequest += 1

  if (chatController) {
    chatController.abort()
    chatController = null
  }
}

function resetChat() {
  stopChatPolling()
  abortChatRequest()

  chatOpen.value = false
  chatData.value = null
  chatMessage.value = ''
  chatError.value = ''
  chatLoading.value = false
  chatSending.value = false
}

function scrollChatToBottom() {
  window.requestAnimationFrame(() => {
    const container = chatMessagesContainer.value

    if (!container) return

    container.scrollTop = container.scrollHeight
  })
}

function normalizeChatResponse(result) {
  if (
    !result
    || !Array.isArray(result.messages)
    || (
      result.tracking_code
      && result.tracking_code !== data.value?.tracking_code
    )
  ) {
    return null
  }

  return {
    tracking_code:
      result.tracking_code || data.value?.tracking_code || '',
    status: result.status ?? null,
    status_display:
      result.status_display || 'Sin conversación',
    created_at: result.created_at ?? null,
    updated_at: result.updated_at ?? null,
    messages: result.messages,
  }
}

async function loadChat({ silent = false } = {}) {
  const trackingCode = data.value?.tracking_code

  if (!trackingCode || !chatOpen.value) return

  const requestId = ++chatRequest

  if (chatController) chatController.abort()

  const requestController = new AbortController()
  chatController = requestController

  if (!silent) {
    chatLoading.value = true
    chatError.value = ''
  }

  try {
    const response = await fetch(
      `/api/orders/public/${encodeURIComponent(trackingCode)}/chat/`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        cache: 'no-store',
        signal: requestController.signal,
      },
    )

    if (
      requestId !== chatRequest
      || trackingCode !== data.value?.tracking_code
      || !chatOpen.value
    ) {
      return
    }

    if (response.status === 404) {
      chatError.value =
        'No fue posible encontrar la orden asociada al chat.'
      stopChatPolling()
      return
    }

    if (response.status === 429) {
      if (!silent) {
        chatError.value =
          'Se alcanzó el límite de consultas del chat. Inténtalo más tarde.'
      }
      return
    }

    if (!response.ok) {
      if (!silent) {
        chatError.value =
          'No fue posible cargar la conversación. Inténtalo nuevamente.'
      }
      return
    }

    const result = await response.json()
    const normalized = normalizeChatResponse(result)

    if (!normalized) {
      if (!silent) {
        chatError.value =
          'No fue posible interpretar la conversación.'
      }
      return
    }

    const previousMessages =
      chatData.value?.messages || []
    const previousLastId =
      previousMessages.length
        ? previousMessages[previousMessages.length - 1].id
        : null

    chatData.value = normalized

    const nextLastId =
      normalized.messages.length
        ? normalized.messages[normalized.messages.length - 1].id
        : null

    if (
      !silent
      || previousLastId !== nextLastId
    ) {
      scrollChatToBottom()
    }
  } catch (err) {
    if (
      requestId === chatRequest
      && err?.name !== 'AbortError'
      && !silent
    ) {
      chatError.value =
        'No fue posible conectar con el chat. Inténtalo nuevamente.'
    }
  } finally {
    if (requestId === chatRequest) {
      chatLoading.value = false
      chatController = null
    }
  }
}

function startChatPolling() {
  stopChatPolling()

  chatPollTimer = window.setInterval(() => {
    loadChat({ silent: true })
  }, CHAT_POLL_INTERVAL)
}

async function openChat() {
  chatOpen.value = true
  chatError.value = ''

  await loadChat()

  if (chatOpen.value) {
    startChatPolling()
  }
}

function closeChat() {
  chatOpen.value = false
  stopChatPolling()
  abortChatRequest()
  chatLoading.value = false
}

async function toggleChat() {
  if (chatOpen.value) {
    closeChat()
    return
  }

  await openChat()
}

async function sendChatMessage() {
  const trackingCode = data.value?.tracking_code
  const body = chatMessage.value.trim()

  if (
    !trackingCode
    || !body
    || chatSending.value
    || chatData.value?.status === 'CLOSED'
  ) {
    return
  }

  chatSending.value = true
  chatError.value = ''

  stopChatPolling()
  abortChatRequest()

  try {
    const response = await fetch(
      `/api/orders/public/${encodeURIComponent(trackingCode)}/chat/`,
      {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ body }),
      },
    )

    let result = null

    try {
      result = await response.json()
    } catch {
      result = null
    }

    if (response.status === 409) {
      chatError.value =
        result?.detail
        || 'La conversación está cerrada.'
      return
    }

    if (response.status === 429) {
      chatError.value =
        'Se alcanzó el límite de mensajes. Inténtalo más tarde.'
      return
    }

    if (!response.ok) {
      const bodyErrors = result?.body

      if (Array.isArray(bodyErrors) && bodyErrors.length) {
        chatError.value = bodyErrors[0]
      } else {
        chatError.value =
          result?.detail
          || 'No fue posible enviar el mensaje.'
      }
      return
    }

    const normalized = normalizeChatResponse(result)

    if (!normalized) {
      chatError.value =
        'El mensaje fue enviado, pero no fue posible actualizar la conversación.'
      return
    }

    chatData.value = normalized
    chatMessage.value = ''
    scrollChatToBottom()

    if (!chatPollTimer) {
      startChatPolling()
    }
  } catch {
    chatError.value =
      'No fue posible conectar con el chat. Inténtalo nuevamente.'
  } finally {
    chatSending.value = false

    if (chatOpen.value && !chatPollTimer) {
      startChatPolling()
    }
  }
}

function chatStatusClass(status) {
  if (status === 'NEW') return 'chat-status-new'
  if (status === 'PENDING') return 'chat-status-pending'
  if (status === 'ANSWERED') return 'chat-status-answered'
  if (status === 'CLOSED') return 'chat-status-closed'

  return 'chat-status-empty'
}

async function search() {
  const normalizedCode = code.value.trim().toUpperCase()
  const requestId = ++currentRequest

  resetChat()

  if (controller) controller.abort()

  controller = null
  data.value = null
  error.value = ''

  if (!/^MC-[A-F0-9]{12}$/.test(normalizedCode)) {
    error.value = notFoundMessage
    loading.value = false
    return
  }

  const requestController = new AbortController()
  controller = requestController
  loading.value = true

  try {
    const response = await fetch(
      `/api/orders/public/${encodeURIComponent(normalizedCode)}/`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        cache: 'no-store',
        signal: requestController.signal,
      },
    )

    if (requestId !== currentRequest) return

    if (response.status === 404) {
      error.value = notFoundMessage
      return
    }

    if (response.status === 429) {
      error.value =
        'Se alcanzó el límite de consultas. Inténtalo más tarde.'
      return
    }

    if (!response.ok) {
      error.value =
        'No fue posible consultar el estado. Inténtalo nuevamente.'
      return
    }

    const result = await response.json()

    if (requestId !== currentRequest) return

    if (
      result?.tracking_code !== normalizedCode
      || typeof result?.status !== 'string'
      || typeof result?.status_display !== 'string'
      || !Array.isArray(result?.history)
    ) {
      error.value =
        'No fue posible interpretar la respuesta. Inténtalo nuevamente.'
      return
    }

    data.value = {
      tracking_code: result.tracking_code,
      status: result.status,
      status_display: result.status_display,
      updated_at: result.updated_at,
      history: result.history,
    }
  } catch (err) {
    if (
      requestId === currentRequest
      && err?.name !== 'AbortError'
    ) {
      error.value =
        'No fue posible conectar con el servicio. Inténtalo nuevamente.'
    }
  } finally {
    if (requestId === currentRequest) {
      loading.value = false
      controller = null
    }
  }
}

onBeforeUnmount(() => {
  currentRequest += 1

  if (controller) controller.abort()

  stopChatPolling()
  abortChatRequest()
})
</script>

<template>
  <main
    class="min-vh-100 py-4 px-3"
    style="background: #eef4f8"
  >
    <div class="mobile-public">
      <header
        class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4"
      >
        <div
          class="fw-bold fs-5"
          style="color: var(--mc-navy)"
        >
          <i
            class="bi bi-tools me-2"
            aria-hidden="true"
          ></i>
          MARTINI CELL
        </div>

        <router-link
          to="/login"
          class="small"
        >
          Iniciar sesión
        </router-link>
      </header>

      <section
        class="mc-card p-4 mb-3"
        aria-labelledby="tracking-heading"
      >
        <h1
          id="tracking-heading"
          class="h4 fw-bold"
        >
          Consulta tu reparación
        </h1>

        <p class="text-muted">
          Ingresa el código de seguimiento entregado al recibir tu equipo.
        </p>

        <form
          class="row g-2 align-items-end"
          @submit.prevent="search"
        >
          <div class="col-12 col-sm-8">
            <label
              for="tracking-code"
              class="form-label"
            >
              Código de seguimiento
            </label>

            <input
              id="tracking-code"
              v-model="code"
              type="text"
              class="form-control"
              placeholder="MC-XXXXXXXXXXXX"
              autocomplete="off"
              autocapitalize="characters"
              :aria-invalid="Boolean(error)"
              :disabled="loading"
              required
            >
          </div>

          <div class="col-12 col-sm-4">
            <button
              class="btn btn-primary w-100"
              type="submit"
              :disabled="loading || !code.trim()"
            >
              <span
                v-if="loading"
                class="spinner-border spinner-border-sm me-1"
                aria-hidden="true"
              ></span>

              {{ loading ? 'Consultando...' : 'Consultar' }}
            </button>
          </div>
        </form>

        <div
          v-if="error"
          class="alert alert-warning mt-3 mb-0"
          role="alert"
        >
          {{ error }}
        </div>
      </section>

      <section
        v-if="data"
        class="mc-card p-4"
        aria-labelledby="tracking-result-heading"
        aria-live="polite"
      >
        <div class="mb-4">
          <h2
            id="tracking-result-heading"
            class="h5 fw-bold mb-2"
          >
            Seguimiento de tu reparación
          </h2>

          <div class="small text-muted">
            Código de seguimiento
          </div>

          <div class="fw-semibold text-break">
            {{ data.tracking_code }}
          </div>
        </div>

        <div class="current-status-card mb-4">
          <div class="small text-muted mb-1">
            Estado actual
          </div>

          <div class="fs-4 fw-bold text-primary">
            {{ data.status_display }}
          </div>

          <div class="small text-muted mt-1">
            Última actualización:
            {{ formatDate(data.updated_at) }}
          </div>
        </div>

        <div class="tracking-timeline">
          <div
            v-for="(step, index) in trackingSteps"
            :key="step.key"
            class="tracking-step"
            :class="`tracking-${getStepState(step)}`"
          >
            <div class="tracking-left">
              <div
                class="tracking-marker"
                :aria-label="getStepText(step)"
              >
                <i
                  class="bi"
                  :class="getStepIcon(step)"
                  aria-hidden="true"
                ></i>
              </div>

              <div
                v-if="index < trackingSteps.length - 1"
                class="tracking-line"
              ></div>
            </div>

            <div class="tracking-content">
              <div
                class="d-flex flex-wrap justify-content-between gap-2"
              >
                <div>
                  <div class="tracking-title">
                    {{ step.label }}
                  </div>

                  <div
                    v-if="step.optional"
                    class="small text-muted"
                  >
                    Si corresponde
                  </div>
                </div>

                <span
                  class="tracking-state"
                  :class="`state-${getStepState(step)}`"
                >
                  {{ getStepText(step) }}
                </span>
              </div>

              <p class="small text-muted mb-1 mt-1">
                {{ step.description }}
              </p>

              <div
                v-if="getStatusDate(step.key)"
                class="tracking-date"
              >
                <i
                  class="bi bi-clock me-1"
                  aria-hidden="true"
                ></i>
                {{ formatDate(getStatusDate(step.key)) }}
              </div>
            </div>
          </div>
        </div>

        <div
          v-if="hasRejectedStatus()"
          class="alert alert-warning mt-3 mb-0"
        >
          <div class="fw-semibold">
            <i
              class="bi bi-exclamation-circle me-1"
              aria-hidden="true"
            ></i>
            No reparado / rechazado
          </div>

          <div
            v-if="rejectedDate()"
            class="small mt-1"
          >
            Registrado el {{ formatDate(rejectedDate()) }}
          </div>
        </div>

        <div class="contact-card mt-4">
          <div
            class="d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-3"
          >
            <div>
              <div class="fw-semibold">
                ¿Necesitas hablar con nosotros?
              </div>

              <div class="small text-muted mt-1">
                Escríbenos directamente sobre esta orden.
              </div>
            </div>

            <button
              type="button"
              class="btn btn-outline-primary"
              :aria-expanded="chatOpen"
              aria-controls="order-chat-panel"
              @click="toggleChat"
            >
              <i
                class="bi me-1"
                :class="chatOpen ? 'bi-x-lg' : 'bi-chat-dots'"
                aria-hidden="true"
              ></i>
              {{ chatOpen ? 'Cerrar chat' : 'Hablar con Martini Cell' }}
            </button>
          </div>

          <div
            v-if="chatOpen"
            id="order-chat-panel"
            class="chat-panel mt-3"
          >
            <div
              class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3"
            >
              <div>
                <div class="fw-bold">
                  Chat de la orden
                </div>

                <div class="small text-muted">
                  {{ data.tracking_code }}
                </div>
              </div>

              <span
                class="chat-status-badge"
                :class="chatStatusClass(chatData?.status)"
              >
                {{ chatData?.status_display || 'Sin conversación' }}
              </span>
            </div>

            <div
              v-if="chatError"
              class="alert alert-warning py-2 small"
              role="alert"
            >
              {{ chatError }}
            </div>

            <div
              v-if="chatLoading && !chatData"
              class="chat-loading text-center text-muted"
            >
              <span
                class="spinner-border spinner-border-sm me-2"
                aria-hidden="true"
              ></span>
              Cargando conversación...
            </div>

            <div
              v-else
              ref="chatMessagesContainer"
              class="chat-messages"
              aria-live="polite"
            >
              <div
                v-if="!chatData?.messages?.length"
                class="chat-empty text-center"
              >
                <i
                  class="bi bi-chat-square-text fs-3 d-block mb-2"
                  aria-hidden="true"
                ></i>

                <div class="fw-semibold">
                  Aún no hay mensajes
                </div>

                <div class="small text-muted mt-1">
                  Envía tu primera consulta a Martini Cell.
                </div>
              </div>

              <div
                v-for="message in chatData?.messages || []"
                :key="message.id"
                class="chat-message-row"
                :class="
                  message.sender_type === 'CLIENT'
                    ? 'chat-message-client'
                    : 'chat-message-staff'
                "
              >
                <div class="chat-bubble">
                  <div class="chat-message-sender">
                    {{ message.sender_name }}
                  </div>

                  <div class="chat-message-body">
                    {{ message.body }}
                  </div>

                  <div class="chat-message-time">
                    {{ formatDate(message.created_at) }}
                  </div>
                </div>
              </div>
            </div>

            <div
              v-if="chatData?.status === 'CLOSED'"
              class="alert alert-secondary small mt-3 mb-0"
            >
              Esta conversación está cerrada. Martini Cell puede
              reabrirla si necesitas continuar hablando sobre la orden.
            </div>

            <form
              v-else
              class="chat-composer mt-3"
              @submit.prevent="sendChatMessage"
            >
              <label
                for="chat-message"
                class="form-label fw-semibold"
              >
                Tu mensaje
              </label>

              <textarea
                id="chat-message"
                v-model="chatMessage"
                class="form-control"
                rows="3"
                maxlength="2000"
                placeholder="Escribe tu consulta..."
                :disabled="chatSending"
                required
              ></textarea>

              <div
                class="d-flex flex-wrap justify-content-between align-items-center gap-2 mt-2"
              >
                <span class="small text-muted">
                  {{ chatMessage.length }}/2000
                </span>

                <button
                  type="submit"
                  class="btn btn-primary"
                  :disabled="chatSending || !chatMessage.trim()"
                >
                  <span
                    v-if="chatSending"
                    class="spinner-border spinner-border-sm me-1"
                    aria-hidden="true"
                  ></span>

                  <i
                    v-else
                    class="bi bi-send me-1"
                    aria-hidden="true"
                  ></i>

                  {{ chatSending ? 'Enviando...' : 'Enviar mensaje' }}
                </button>
              </div>
            </form>

            <div class="small text-muted mt-3">
              La conversación se actualiza automáticamente mientras
              mantengas este chat abierto.
            </div>
          </div>
        </div>
      </section>

      <p class="text-center text-muted small mt-4">
        Esta consulta pública no muestra datos personales, fotografías,
        costos internos ni diagnósticos.
      </p>
    </div>
  </main>
</template>

<style scoped>
.current-status-card {
  padding: 1rem 1.1rem;
  border: 1px solid #dbe4ec;
  border-radius: 0.9rem;
  background: #f8fbfd;
}

.tracking-timeline {
  margin-top: 1rem;
}

.tracking-step {
  display: flex;
  gap: 1rem;
  min-height: 110px;
}

.tracking-left {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 34px;
  flex-shrink: 0;
}

.tracking-marker {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #c7d0d9;
  background: #ffffff;
  color: #8b98a5;
  z-index: 2;
}

.tracking-line {
  width: 3px;
  flex: 1;
  min-height: 72px;
  background: #d9e0e6;
}

.tracking-content {
  flex: 1;
  padding-bottom: 1.4rem;
}

.tracking-title {
  font-weight: 700;
  color: #273849;
}

.tracking-date {
  font-size: 0.82rem;
  font-weight: 600;
  color: #5b6977;
}

.tracking-state {
  display: inline-flex;
  align-items: center;
  height: fit-content;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.tracking-completed .tracking-marker {
  background: #198754;
  border-color: #198754;
  color: #ffffff;
}

.tracking-completed .tracking-line {
  background: #198754;
}

.tracking-current .tracking-marker {
  background: #0d6efd;
  border-color: #0d6efd;
  color: #ffffff;
  box-shadow: 0 0 0 5px rgba(13, 110, 253, 0.12);
}

.tracking-current .tracking-title {
  color: #0d6efd;
}

.tracking-skipped .tracking-marker {
  background: #f1f3f5;
  border-color: #adb5bd;
  color: #6c757d;
}

.state-completed {
  background: #d1e7dd;
  color: #0f5132;
}

.state-current {
  background: #cfe2ff;
  color: #084298;
}

.state-pending {
  background: #f1f3f5;
  color: #6c757d;
}

.state-skipped {
  background: #e9ecef;
  color: #6c757d;
}

.contact-card {
  padding: 1rem;
  border: 1px solid #dbe4ec;
  border-radius: 0.9rem;
  background: #ffffff;
}

.chat-panel {
  padding-top: 1rem;
  border-top: 1px solid #e2e8ee;
}

.chat-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.chat-status-new {
  background: #cfe2ff;
  color: #084298;
}

.chat-status-pending {
  background: #fff3cd;
  color: #664d03;
}

.chat-status-answered {
  background: #d1e7dd;
  color: #0f5132;
}

.chat-status-closed,
.chat-status-empty {
  background: #e9ecef;
  color: #495057;
}

.chat-loading,
.chat-empty {
  padding: 2rem 1rem;
  border: 1px dashed #ccd6df;
  border-radius: 0.85rem;
  background: #f8fbfd;
}

.chat-messages {
  max-height: 390px;
  overflow-y: auto;
  padding: 0.9rem;
  border: 1px solid #dbe4ec;
  border-radius: 0.85rem;
  background: #f8fbfd;
}

.chat-message-row {
  display: flex;
  margin-bottom: 0.75rem;
}

.chat-message-row:last-child {
  margin-bottom: 0;
}

.chat-message-client {
  justify-content: flex-end;
}

.chat-message-staff {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: min(82%, 520px);
  padding: 0.7rem 0.85rem;
  border-radius: 0.9rem;
  box-shadow: 0 1px 2px rgba(24, 39, 56, 0.06);
}

.chat-message-client .chat-bubble {
  background: #0d6efd;
  color: #ffffff;
  border-bottom-right-radius: 0.3rem;
}

.chat-message-staff .chat-bubble {
  background: #ffffff;
  color: #273849;
  border: 1px solid #dbe4ec;
  border-bottom-left-radius: 0.3rem;
}

.chat-message-sender {
  margin-bottom: 0.2rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.chat-message-client .chat-message-sender,
.chat-message-client .chat-message-time {
  color: rgba(255, 255, 255, 0.82);
}

.chat-message-staff .chat-message-sender,
.chat-message-staff .chat-message-time {
  color: #6c757d;
}

.chat-message-body {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.chat-message-time {
  margin-top: 0.35rem;
  font-size: 0.7rem;
}

.chat-composer textarea {
  resize: vertical;
  min-height: 86px;
}

@media (max-width: 575.98px) {
  .tracking-step {
    gap: 0.75rem;
  }

  .tracking-content {
    padding-bottom: 1.1rem;
  }

  .tracking-state {
    font-size: 0.7rem;
  }

  .chat-bubble {
    max-width: 92%;
  }

  .chat-messages {
    max-height: 340px;
    padding: 0.7rem;
  }
}
</style>