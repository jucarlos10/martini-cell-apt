<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch } from '../services/auth'

const conversations = ref([])
const selectedConversation = ref(null)
const selectedConversationId = ref(null)

const loadingList = ref(true)
const loadingConversation = ref(false)
const sendingMessage = ref(false)
const changingStatus = ref(false)

const listError = ref('')
const conversationError = ref('')
const notificationFeedback = ref(null)

const statusFilter = ref('')
const unreadOnly = ref(false)
const messageBody = ref('')

const messagesContainer = ref(null)

const POLL_INTERVAL = 5000

let pollTimer = null
let listRequestId = 0
let detailRequestId = 0

const statusOptions = [
  { value: '', label: 'Todos los estados' },
  { value: 'NEW', label: 'Nuevo' },
  { value: 'PENDING', label: 'Pendiente de respuesta' },
  { value: 'ANSWERED', label: 'Respondido' },
  { value: 'CLOSED', label: 'Cerrado' },
]

const totalUnread = computed(() =>
  conversations.value.reduce(
    (total, conversation) =>
      total + Number(conversation.unread_staff_count || 0),
    0,
  )
)

const selectedIsClosed = computed(
  () => selectedConversation.value?.status === 'CLOSED',
)

function formatDate(value) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Fecha no disponible'
  }

  return new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

function statusBadgeClass(status) {
  return {
    NEW: 'text-bg-primary',
    PENDING: 'text-bg-warning',
    ANSWERED: 'text-bg-success',
    CLOSED: 'text-bg-secondary',
  }[status] || 'text-bg-light'
}

function statusBorderClass(status) {
  return {
    NEW: 'chat-card-new',
    PENDING: 'chat-card-pending',
    ANSWERED: 'chat-card-answered',
    CLOSED: 'chat-card-closed',
  }[status] || ''
}

function notificationAlertClass(status) {
  return {
    SENT: 'alert-success',
    PREPARED: 'alert-info',
    FAILED: 'alert-warning',
  }[status] || 'alert-secondary'
}

function notificationBadgeClass(status) {
  return {
    SENT: 'text-bg-success',
    PREPARED: 'text-bg-info',
    FAILED: 'text-bg-warning',
  }[status] || 'text-bg-secondary'
}

function notificationStatusLabel(status) {
  return {
    SENT: 'Enviado',
    PREPARED: 'Preparado',
    FAILED: 'Fallido',
  }[status] || status || 'Sin estado'
}

function notificationChannelLabel(channel) {
  return {
    EMAIL: 'Correo electrónico',
    WHATSAPP: 'WhatsApp',
  }[channel] || channel || 'Sin canal'
}

function buildListUrl() {
  const params = new URLSearchParams()

  if (statusFilter.value) {
    params.set('status', statusFilter.value)
  }

  if (unreadOnly.value) {
    params.set('unread', 'true')
  }

  const query = params.toString()

  return query
    ? `/api/orders/chat/?${query}`
    : '/api/orders/chat/'
}

function scrollMessagesToBottom() {
  nextTick(() => {
    const container = messagesContainer.value

    if (!container) return

    container.scrollTop = container.scrollHeight
  })
}

function normalizeList(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

async function loadConversations({ silent = false } = {}) {
  const requestId = ++listRequestId

  if (!silent) {
    loadingList.value = true
    listError.value = ''
  }

  try {
    const response = await authenticatedFetch(
      buildListUrl(),
      {
        headers: {
          Accept: 'application/json',
        },
      },
    )

    const data = await response.json().catch(() => null)

    if (requestId !== listRequestId) return

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error(
          'No tienes permiso para acceder al chat de órdenes.',
        )
      }

      throw new Error(
        data?.detail ||
        'No fue posible cargar las conversaciones.',
      )
    }

    conversations.value = normalizeList(data)

  } catch (error) {
    if (requestId !== listRequestId) return

    if (!silent) {
      listError.value =
        error?.message ||
        'Ocurrió un error al cargar las conversaciones.'
    }

  } finally {
    if (requestId === listRequestId) {
      loadingList.value = false
    }
  }
}

async function loadConversation(
  conversationId,
  { silent = false } = {},
) {
  if (!conversationId) return

  const requestId = ++detailRequestId

  if (!silent) {
    loadingConversation.value = true
    conversationError.value = ''
  }

  try {
    const response = await authenticatedFetch(
      `/api/orders/chat/${conversationId}/`,
      {
        headers: {
          Accept: 'application/json',
        },
      },
    )

    const data = await response.json().catch(() => null)

    if (
      requestId !== detailRequestId ||
      selectedConversationId.value !== conversationId
    ) {
      return
    }

    if (!response.ok) {
      throw new Error(
        data?.detail ||
        'No fue posible cargar la conversación.',
      )
    }

    const previousLastMessageId =
      selectedConversation.value?.messages?.length
        ? selectedConversation.value.messages[
            selectedConversation.value.messages.length - 1
          ].id
        : null

    selectedConversation.value = data

    const nextLastMessageId =
      data?.messages?.length
        ? data.messages[data.messages.length - 1].id
        : null

    if (
      !silent ||
      previousLastMessageId !== nextLastMessageId
    ) {
      scrollMessagesToBottom()
    }

  } catch (error) {
    if (
      requestId === detailRequestId &&
      !silent
    ) {
      conversationError.value =
        error?.message ||
        'Ocurrió un error al cargar la conversación.'
    }

  } finally {
    if (requestId === detailRequestId) {
      loadingConversation.value = false
    }
  }
}

async function selectConversation(conversation) {
  selectedConversationId.value = conversation.id
  selectedConversation.value = null
  messageBody.value = ''
  conversationError.value = ''
  notificationFeedback.value = null

  await loadConversation(conversation.id)
  await loadConversations({ silent: true })
}

async function sendMessage() {
  const conversationId = selectedConversationId.value
  const body = messageBody.value.trim()

  if (
    !conversationId ||
    !body ||
    sendingMessage.value ||
    selectedIsClosed.value
  ) {
    return
  }

  sendingMessage.value = true
  conversationError.value = ''
  notificationFeedback.value = null

  try {
    const response = await authenticatedFetch(
      `/api/orders/chat/${conversationId}/`,
      {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ body }),
      },
    )

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      if (response.status === 409) {
        throw new Error(
          data?.detail ||
          'La conversación está cerrada.',
        )
      }

      const bodyErrors = data?.body

      if (Array.isArray(bodyErrors) && bodyErrors.length) {
        throw new Error(bodyErrors[0])
      }

      throw new Error(
        data?.detail ||
        'No fue posible enviar el mensaje.',
      )
    }

    selectedConversation.value = data
    notificationFeedback.value =
      data?.notification_result || null
    messageBody.value = ''

    scrollMessagesToBottom()

    await loadConversations({ silent: true })

  } catch (error) {
    conversationError.value =
      error?.message ||
      'Ocurrió un error al enviar el mensaje.'

  } finally {
    sendingMessage.value = false
  }
}

async function changeConversationStatus(status) {
  const conversationId = selectedConversationId.value

  if (
    !conversationId ||
    changingStatus.value
  ) {
    return
  }

  changingStatus.value = true
  conversationError.value = ''

  try {
    const response = await authenticatedFetch(
      `/api/orders/chat/${conversationId}/status/`,
      {
        method: 'PATCH',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      },
    )

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(
        data?.detail ||
        'No fue posible actualizar el estado del chat.',
      )
    }

    selectedConversation.value = data

    await loadConversations({ silent: true })

  } catch (error) {
    conversationError.value =
      error?.message ||
      'Ocurrió un error al actualizar el chat.'

  } finally {
    changingStatus.value = false
  }
}

async function closeConversation() {
  await changeConversationStatus('CLOSED')
}

async function reopenConversation() {
  await changeConversationStatus('PENDING')
}

async function applyFilters() {
  await loadConversations()
}

async function clearFilters() {
  statusFilter.value = ''
  unreadOnly.value = false

  await loadConversations()
}

async function refreshAll() {
  await loadConversations()

  if (selectedConversationId.value) {
    await loadConversation(
      selectedConversationId.value,
      { silent: true },
    )
  }
}

function startPolling() {
  stopPolling()

  pollTimer = window.setInterval(async () => {
    await loadConversations({ silent: true })

    if (selectedConversationId.value) {
      await loadConversation(
        selectedConversationId.value,
        { silent: true },
      )
    }
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (!pollTimer) return

  window.clearInterval(pollTimer)
  pollTimer = null
}

onMounted(async () => {
  await loadConversations()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
  listRequestId += 1
  detailRequestId += 1
})
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Chat de órdenes

      <template #subtitle>
        Conversaciones de clientes asociadas a sus órdenes de servicio.
      </template>

      <template #actions>
        <button
          type="button"
          class="btn btn-outline-primary"
          :disabled="loadingList"
          @click="refreshAll"
        >
          <i class="bi bi-arrow-clockwise me-1"></i>
          Actualizar
        </button>
      </template>
    </PageHeader>

    <div
      v-if="listError"
      class="alert alert-danger"
      role="alert"
    >
      {{ listError }}

      <button
        type="button"
        class="btn btn-sm btn-outline-danger ms-2"
        @click="loadConversations"
      >
        Reintentar
      </button>
    </div>

    <div class="mc-card p-3 mb-3">
      <form
        class="row g-3 align-items-end"
        @submit.prevent="applyFilters"
      >
        <div class="col-md-5">
          <label
            for="chat-status-filter"
            class="form-label"
          >
            Estado
          </label>

          <select
            id="chat-status-filter"
            v-model="statusFilter"
            class="form-select"
            :disabled="loadingList"
            @change="applyFilters"
          >
            <option
              v-for="option in statusOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="col-md-4">
          <div class="form-check chat-unread-filter">
            <input
              id="chat-unread-only"
              v-model="unreadOnly"
              class="form-check-input"
              type="checkbox"
              :disabled="loadingList"
              @change="applyFilters"
            >

            <label
              class="form-check-label"
              for="chat-unread-only"
            >
              Solo conversaciones con mensajes no leídos
            </label>
          </div>
        </div>

        <div class="col-md-3">
          <button
            type="button"
            class="btn btn-outline-secondary w-100"
            :disabled="
              loadingList ||
              (!statusFilter && !unreadOnly)
            "
            @click="clearFilters"
          >
            Limpiar filtros
          </button>
        </div>
      </form>
    </div>

    <div class="row g-3 chat-workspace">
      <div class="col-lg-5 col-xl-4">
        <div class="mc-card chat-inbox-card">
          <div class="chat-inbox-header">
            <div>
              <div class="fw-bold">
                Bandeja de conversaciones
              </div>

              <div class="small text-muted">
                {{ conversations.length }}
                conversación{{ conversations.length === 1 ? '' : 'es' }}
              </div>
            </div>

            <span
              v-if="totalUnread > 0"
              class="badge rounded-pill text-bg-danger"
            >
              {{ totalUnread }} no leído{{ totalUnread === 1 ? '' : 's' }}
            </span>
          </div>

          <div
            v-if="loadingList"
            class="chat-state text-center text-muted"
          >
            <span
              class="spinner-border spinner-border-sm me-2"
              aria-hidden="true"
            ></span>
            Cargando conversaciones...
          </div>

          <div
            v-else-if="!conversations.length"
            class="chat-state text-center"
          >
            <i
              class="bi bi-chat-square-text fs-2 text-muted"
              aria-hidden="true"
            ></i>

            <div class="fw-semibold mt-2">
              No hay conversaciones
            </div>

            <div class="small text-muted mt-1">
              No existen chats que coincidan con los filtros actuales.
            </div>
          </div>

          <div
            v-else
            class="chat-conversation-list"
          >
            <button
              v-for="conversation in conversations"
              :key="conversation.id"
              type="button"
              class="chat-conversation-card"
              :class="[
                statusBorderClass(conversation.status),
                {
                  active:
                    selectedConversationId === conversation.id,
                },
              ]"
              @click="selectConversation(conversation)"
            >
              <div
                class="d-flex justify-content-between align-items-start gap-2"
              >
                <div class="min-w-0 text-start">
                  <div class="fw-bold text-truncate">
                    {{ conversation.client_name }}
                  </div>

                  <div class="small text-muted text-truncate">
                    {{ conversation.tracking_code }}
                  </div>
                </div>

                <span
                  v-if="conversation.unread_staff_count > 0"
                  class="badge rounded-pill text-bg-danger"
                >
                  {{ conversation.unread_staff_count }}
                </span>
              </div>

              <div class="small mt-2 text-start">
                {{ conversation.equipment_description }}
              </div>

              <div
                v-if="conversation.last_message"
                class="chat-last-message text-start mt-2"
              >
                <span class="fw-semibold">
                  {{ conversation.last_message.sender_type_display }}:
                </span>
                {{ conversation.last_message.body }}
              </div>

              <div
                class="d-flex flex-wrap justify-content-between align-items-center gap-2 mt-2"
              >
                <span
                  class="badge"
                  :class="statusBadgeClass(conversation.status)"
                >
                  {{ conversation.status_display }}
                </span>

                <span class="chat-time">
                  {{ formatDate(conversation.last_message_at) }}
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>

      <div class="col-lg-7 col-xl-8">
        <div class="mc-card chat-detail-card">
          <div
            v-if="!selectedConversationId"
            class="chat-detail-empty"
          >
            <i
              class="bi bi-chat-left-dots fs-1 text-muted"
              aria-hidden="true"
            ></i>

            <h5 class="mt-3 mb-1">
              Selecciona una conversación
            </h5>

            <p class="text-muted mb-0">
              Elige un chat de la bandeja para revisar el historial y responder.
            </p>
          </div>

          <div
            v-else-if="loadingConversation && !selectedConversation"
            class="chat-detail-empty"
          >
            <span
              class="spinner-border text-primary"
              aria-hidden="true"
            ></span>

            <div class="mt-3 text-muted">
              Cargando conversación...
            </div>
          </div>

          <template v-else-if="selectedConversation">
            <div class="chat-detail-header">
              <div>
                <div class="d-flex flex-wrap align-items-center gap-2">
                  <h5 class="mb-0">
                    {{ selectedConversation.client_name }}
                  </h5>

                  <span
                    class="badge"
                    :class="statusBadgeClass(selectedConversation.status)"
                  >
                    {{ selectedConversation.status_display }}
                  </span>
                </div>

                <div class="small text-muted mt-1">
                  {{ selectedConversation.tracking_code }}
                  ·
                  {{ selectedConversation.equipment_description }}
                </div>

                <RouterLink
                  :to="`/ordenes/${selectedConversation.order_id}`"
                  class="small text-decoration-none d-inline-block mt-1"
                >
                  <i class="bi bi-box-arrow-up-right me-1"></i>
                  Ver orden
                </RouterLink>
              </div>

              <div class="d-flex flex-wrap gap-2">
                <button
                  v-if="!selectedIsClosed"
                  type="button"
                  class="btn btn-sm btn-outline-secondary"
                  :disabled="changingStatus"
                  @click="closeConversation"
                >
                  <span
                    v-if="changingStatus"
                    class="spinner-border spinner-border-sm me-1"
                    aria-hidden="true"
                  ></span>
                  <i
                    v-else
                    class="bi bi-lock me-1"
                    aria-hidden="true"
                  ></i>
                  Cerrar conversación
                </button>

                <button
                  v-else
                  type="button"
                  class="btn btn-sm btn-outline-primary"
                  :disabled="changingStatus"
                  @click="reopenConversation"
                >
                  <span
                    v-if="changingStatus"
                    class="spinner-border spinner-border-sm me-1"
                    aria-hidden="true"
                  ></span>
                  <i
                    v-else
                    class="bi bi-unlock me-1"
                    aria-hidden="true"
                  ></i>
                  Reabrir conversación
                </button>
              </div>
            </div>

            <div
              v-if="conversationError"
              class="alert alert-danger py-2 small mx-3 mt-3 mb-0"
              role="alert"
            >
              {{ conversationError }}
            </div>

            <div
              v-if="notificationFeedback"
              class="alert py-2 small mx-3 mt-3 mb-0"
              :class="
                notificationAlertClass(
                  notificationFeedback.status,
                )
              "
              role="status"
            >
              <div
                class="d-flex flex-wrap justify-content-between align-items-start gap-2"
              >
                <div>
                  <div class="fw-semibold">
                    Respuesta guardada correctamente
                  </div>

                  <div class="mt-1">
                    {{
                      notificationFeedback.detail ||
                      (
                        notificationFeedback.status === 'SENT'
                          ? 'El aviso al cliente fue enviado.'
                          : notificationFeedback.status === 'PREPARED'
                            ? 'El aviso al cliente quedó preparado.'
                            : 'No fue posible notificar al cliente.'
                      )
                    }}
                  </div>

                  <div
                    v-if="notificationFeedback.channel"
                    class="mt-1"
                  >
                    Canal:
                    <strong>
                      {{
                        notificationFeedback.channel_display ||
                        notificationChannelLabel(
                          notificationFeedback.channel,
                        )
                      }}
                    </strong>
                  </div>
                </div>

                <a
                  v-if="
                    notificationFeedback.status === 'PREPARED' &&
                    notificationFeedback.action_url
                  "
                  :href="notificationFeedback.action_url"
                  class="btn btn-sm btn-success"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <i class="bi bi-whatsapp me-1"></i>
                  Abrir WhatsApp
                </a>
              </div>
            </div>

            <div
              ref="messagesContainer"
              class="chat-messages"
            >
              <div
                v-if="!selectedConversation.messages?.length"
                class="chat-state text-center"
              >
                No hay mensajes en esta conversación.
              </div>

              <div
                v-for="message in selectedConversation.messages || []"
                :key="message.id"
                class="chat-message-row"
                :class="
                  message.sender_type === 'STAFF'
                    ? 'chat-message-staff'
                    : 'chat-message-client'
                "
              >
                <div class="chat-bubble">
                  <div class="chat-message-meta">
                    <span class="fw-bold">
                      {{
                        message.sender_type === 'STAFF'
                          ? (
                              message.sender_username
                                ? `Martini Cell · ${message.sender_username}`
                                : 'Martini Cell'
                            )
                          : 'Cliente'
                      }}
                    </span>

                    <span>
                      {{ formatDate(message.created_at) }}
                    </span>
                  </div>

                  <div class="chat-message-body">
                    {{ message.body }}
                  </div>

                  <div
                    v-if="message.sender_type === 'STAFF'"
                    class="chat-read-state"
                  >
                    <i
                      class="bi"
                      :class="
                        message.read_by_client
                          ? 'bi-check2-all'
                          : 'bi-check2'
                      "
                      aria-hidden="true"
                    ></i>
                    {{
                      message.read_by_client
                        ? 'Leído por el cliente'
                        : 'Enviado'
                    }}
                  </div>
                </div>
              </div>
            </div>

            <div
              v-if="selectedConversation.notifications?.length"
              class="chat-notifications"
            >
              <div class="chat-notifications-header">
                <div>
                  <div class="fw-semibold">
                    Historial de notificaciones
                  </div>

                  <div class="small text-muted">
                    Avisos generados por respuestas de Martini Cell.
                  </div>
                </div>

                <span class="badge text-bg-light">
                  {{ selectedConversation.notifications.length }}
                </span>
              </div>

              <div class="chat-notification-list">
                <div
                  v-for="notification in selectedConversation.notifications"
                  :key="notification.id"
                  class="chat-notification-item"
                >
                  <div
                    class="d-flex flex-wrap justify-content-between align-items-start gap-2"
                  >
                    <div>
                      <div class="fw-semibold">
                        {{
                          notification.channel_display ||
                          notificationChannelLabel(
                            notification.channel,
                          )
                        }}
                      </div>

                      <div class="small text-muted">
                        {{ formatDate(notification.created_at) }}
                        <span
                          v-if="notification.triggered_by_username"
                        >
                          · {{ notification.triggered_by_username }}
                        </span>
                      </div>
                    </div>

                    <span
                      class="badge"
                      :class="
                        notificationBadgeClass(
                          notification.status,
                        )
                      "
                    >
                      {{
                        notification.status_display ||
                        notificationStatusLabel(
                          notification.status,
                        )
                      }}
                    </span>
                  </div>

                  <div
                    v-if="notification.detail"
                    class="small mt-2"
                  >
                    {{ notification.detail }}
                  </div>

                  <div
                    v-if="notification.destination"
                    class="small text-muted mt-1"
                  >
                    Destino: {{ notification.destination }}
                  </div>

                  <a
                    v-if="
                      notification.status === 'PREPARED' &&
                      notification.action_url
                    "
                    :href="notification.action_url"
                    class="btn btn-sm btn-outline-success mt-2"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <i class="bi bi-whatsapp me-1"></i>
                    Abrir WhatsApp
                  </a>
                </div>
              </div>
            </div>

            <div
              v-if="selectedIsClosed"
              class="chat-closed-note"
            >
              <i class="bi bi-lock me-1"></i>
              Esta conversación está cerrada.
              El historial se conserva y puede reabrirse.
            </div>

            <form
              v-else
              class="chat-composer"
              @submit.prevent="sendMessage"
            >
              <label
                for="staff-chat-message"
                class="form-label fw-semibold"
              >
                Responder al cliente
              </label>

              <textarea
                id="staff-chat-message"
                v-model="messageBody"
                class="form-control"
                rows="3"
                maxlength="2000"
                placeholder="Escribe tu respuesta..."
                :disabled="sendingMessage"
                required
              ></textarea>

              <div
                class="d-flex flex-wrap justify-content-between align-items-center gap-2 mt-2"
              >
                <span class="small text-muted">
                  {{ messageBody.length }}/2000
                </span>

                <button
                  type="submit"
                  class="btn btn-primary"
                  :disabled="
                    sendingMessage ||
                    !messageBody.trim()
                  "
                >
                  <span
                    v-if="sendingMessage"
                    class="spinner-border spinner-border-sm me-1"
                    aria-hidden="true"
                  ></span>

                  <i
                    v-else
                    class="bi bi-send me-1"
                    aria-hidden="true"
                  ></i>

                  {{ sendingMessage ? 'Enviando...' : 'Enviar respuesta' }}
                </button>
              </div>
            </form>

            <div class="chat-poll-note">
              <i class="bi bi-arrow-repeat me-1"></i>
              La bandeja se actualiza automáticamente cada 5 segundos.
            </div>
          </template>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.chat-workspace {
  min-height: 620px;
}

.chat-inbox-card,
.chat-detail-card {
  height: 100%;
  overflow: hidden;
}

.chat-inbox-header,
.chat-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  border-bottom: 1px solid #e2e8ee;
}

.chat-unread-filter {
  min-height: 38px;
  display: flex;
  align-items: center;
}

.chat-conversation-list {
  max-height: 670px;
  overflow-y: auto;
}

.chat-conversation-card {
  width: 100%;
  padding: 0.9rem 1rem;
  border: 0;
  border-bottom: 1px solid #e8edf2;
  border-left: 4px solid transparent;
  background: #ffffff;
  color: inherit;
  text-align: left;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.chat-conversation-card:hover {
  background: #f8fbfd;
}

.chat-conversation-card.active {
  background: #eef5ff;
  border-left-color: #0d6efd;
}

.chat-card-new {
  border-left-color: #0d6efd;
}

.chat-card-pending {
  border-left-color: #ffc107;
}

.chat-card-answered {
  border-left-color: #198754;
}

.chat-card-closed {
  border-left-color: #6c757d;
}

.chat-conversation-card.active.chat-card-pending {
  border-left-color: #ffc107;
}

.chat-conversation-card.active.chat-card-answered {
  border-left-color: #198754;
}

.chat-conversation-card.active.chat-card-closed {
  border-left-color: #6c757d;
}

.chat-last-message {
  display: -webkit-box;
  overflow: hidden;
  color: #586979;
  font-size: 0.86rem;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.chat-time {
  color: #748493;
  font-size: 0.72rem;
}

.chat-state {
  padding: 2rem 1rem;
}

.chat-detail-card {
  display: flex;
  flex-direction: column;
  min-height: 620px;
}

.chat-detail-empty {
  flex: 1;
  display: grid;
  place-items: center;
  align-content: center;
  padding: 3rem 1rem;
  text-align: center;
}

.chat-messages {
  flex: 1;
  min-height: 280px;
  max-height: 520px;
  overflow-y: auto;
  padding: 1rem;
  background: #f7fafc;
}

.chat-message-row {
  display: flex;
  margin-bottom: 0.8rem;
}

.chat-message-row:last-child {
  margin-bottom: 0;
}

.chat-message-client {
  justify-content: flex-start;
}

.chat-message-staff {
  justify-content: flex-end;
}

.chat-bubble {
  max-width: min(78%, 640px);
  padding: 0.75rem 0.9rem;
  border-radius: 0.9rem;
  box-shadow: 0 1px 2px rgba(24, 39, 56, 0.08);
}

.chat-message-client .chat-bubble {
  background: #ffffff;
  border: 1px solid #dbe4ec;
  border-bottom-left-radius: 0.3rem;
}

.chat-message-staff .chat-bubble {
  background: #0d6efd;
  color: #ffffff;
  border-bottom-right-radius: 0.3rem;
}

.chat-message-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.3rem;
  font-size: 0.72rem;
}

.chat-message-client .chat-message-meta {
  color: #6c757d;
}

.chat-message-staff .chat-message-meta {
  color: rgba(255, 255, 255, 0.82);
}

.chat-message-body {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.chat-read-state {
  margin-top: 0.35rem;
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.7rem;
  text-align: right;
}

.chat-notifications {
  border-top: 1px solid #e2e8ee;
  background: #ffffff;
}

.chat-notifications-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #edf1f4;
}

.chat-notification-list {
  max-height: 220px;
  overflow-y: auto;
}

.chat-notification-item {
  padding: 0.8rem 1rem;
  border-bottom: 1px solid #edf1f4;
}

.chat-notification-item:last-child {
  border-bottom: 0;
}

.chat-composer {
  padding: 1rem;
  border-top: 1px solid #e2e8ee;
  background: #ffffff;
}

.chat-composer textarea {
  min-height: 86px;
  resize: vertical;
}

.chat-closed-note {
  padding: 0.85rem 1rem;
  border-top: 1px solid #e2e8ee;
  background: #f3f5f7;
  color: #5e6872;
  font-size: 0.9rem;
}

.chat-poll-note {
  padding: 0.65rem 1rem;
  border-top: 1px solid #edf1f4;
  color: #748493;
  font-size: 0.75rem;
  background: #ffffff;
}

.min-w-0 {
  min-width: 0;
}

@media (max-width: 991.98px) {
  .chat-workspace {
    min-height: auto;
  }

  .chat-conversation-list {
    max-height: 420px;
  }

  .chat-detail-card {
    min-height: 560px;
  }
}

@media (max-width: 575.98px) {
  .chat-inbox-header,
  .chat-detail-header {
    flex-direction: column;
  }

  .chat-bubble {
    max-width: 92%;
  }

  .chat-messages {
    max-height: 430px;
  }
}
</style>
