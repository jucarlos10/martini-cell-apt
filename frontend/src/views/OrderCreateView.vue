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
  received_accessories: '',
  deposit_amount: '',
})

// HU-34: comprobante y entrega.
const receipt = ref(null)
const receiptLoading = ref(false)
const receiptError = ref('')
const deliveryMethod = ref('')
const deliveringReceipt = ref(false)
const deliverySuccess = ref('')
const deliveryError = ref('')

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

function formatDateTime(value) {
  if (!value) return 'Sin información'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleString('es-CL')
}

function formatMoney(value) {
  const number = Number(value || 0)

  if (!Number.isFinite(number)) {
    return '$0'
  }

  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(number)
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

const receiptSnapshot = computed(() =>
  receipt.value?.snapshot || null
)

const receiptOrder = computed(() =>
  receiptSnapshot.value?.order || {}
)

const receiptClient = computed(() =>
  receiptSnapshot.value?.client || {}
)

const receiptEquipment = computed(() =>
  receiptSnapshot.value?.equipment || {}
)

const receiptReception = computed(() =>
  receiptSnapshot.value?.reception || {}
)

const receiptTracking = computed(() =>
  receiptSnapshot.value?.tracking || {}
)

const clientHasEmail = computed(() =>
  Boolean(String(selectedClient.value?.email || '').trim())
)

const clientHasPhone = computed(() =>
  Boolean(String(selectedClient.value?.phone || '').trim())
)

const printNotificationNotice = computed(() => {
  if (!createdOrder.value || clientHasEmail.value) {
    return ''
  }

  if (clientHasPhone.value) {
    return (
      'Este cliente no tiene correo registrado. ' +
      'Si eliges Impreso, WhatsApp quedará como canal ' +
      'para las notificaciones posteriores de esta orden.'
    )
  }

  return (
    'Este cliente no tiene correo ni teléfono registrado. ' +
    'Debes actualizar sus datos de contacto antes de confirmar ' +
    'una entrega impresa.'
  )
})

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

    const deposit = Number(order.value.deposit_amount || 0)

    if (!Number.isFinite(deposit) || deposit < 0) {
      error.value =
        'El abono debe ser un monto igual o mayor a cero.'
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

function chooseDefaultDeliveryMethod() {
  if (clientHasEmail.value) {
    deliveryMethod.value = 'EMAIL'
    return
  }

  if (clientHasPhone.value) {
    deliveryMethod.value = 'WHATSAPP'
    return
  }

  deliveryMethod.value = 'PRINT'
}

// HU-34: generar o recuperar el comprobante inmutable de recepción.
async function generateReceipt() {
  if (!createdOrder.value?.id) return

  receiptLoading.value = true
  receiptError.value = ''

  try {
    const response = await authenticatedFetch(
      `/api/orders/${createdOrder.value.id}/reception-receipt/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(formatApiErrors(data))
    }

    receipt.value = data

  } catch (err) {
    receiptError.value =
      err.message ||
      'La orden fue creada, pero no fue posible generar el comprobante.'

  } finally {
    receiptLoading.value = false
  }
}

async function refreshReceipt() {
  if (!createdOrder.value?.id) return

  try {
    const response = await authenticatedFetch(
      `/api/orders/${createdOrder.value.id}/reception-receipt/`
    )

    if (!response.ok) return

    receipt.value = await response.json()

  } catch {
    // No interrumpir el flujo por una actualización secundaria.
  }
}

// Para una entrega impresa sin correo, dejar WhatsApp como canal
// alternativo antes de registrar la impresión.
async function ensurePrintNotificationChannel() {
  if (clientHasEmail.value) {
    return true
  }

  if (!clientHasPhone.value) {
    throw new Error(
      'El cliente no tiene correo ni teléfono registrado. ' +
      'Actualiza sus datos antes de registrar la impresión.'
    )
  }

  const response = await authenticatedFetch(
    `/api/orders/${createdOrder.value.id}/`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        preferred_notification_channel: 'WHATSAPP',
      }),
    }
  )

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(formatApiErrors(data))
  }

  createdOrder.value = data

  return true
}

// HU-34: registrar entrega por correo, WhatsApp o impresión.
async function deliverReceipt(method) {
  if (
    deliveringReceipt.value ||
    !createdOrder.value?.id ||
    !receipt.value
  ) {
    return
  }

  deliverySuccess.value = ''
  deliveryError.value = ''
  deliveringReceipt.value = true

  try {
    if (method === 'PRINT') {
      await ensurePrintNotificationChannel()
    }

    const response = await authenticatedFetch(
      `/api/orders/${createdOrder.value.id}/reception-receipt/deliver/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          delivery_method: method,
        }),
      }
    )

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(formatApiErrors(data))
    }

    if (data?.preferred_notification_channel) {
      createdOrder.value = {
        ...createdOrder.value,
        preferred_notification_channel:
          data.preferred_notification_channel,
      }
    }

    deliverySuccess.value =
      data?.detail || 'Comprobante procesado correctamente.'

    if (method === 'WHATSAPP' && data?.whatsapp_url) {
      window.open(
        data.whatsapp_url,
        '_blank',
        'noopener,noreferrer'
      )
    }

    await refreshReceipt()

    if (method === 'PRINT') {
      printReceipt()
    }

  } catch (err) {
    deliveryError.value =
      err.message || 'No fue posible procesar el comprobante.'

  } finally {
    deliveringReceipt.value = false
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

// Crear una versión limpia para imprimir o guardar como PDF desde el navegador.
function printReceipt() {
  if (!receiptSnapshot.value) return

  const snapshot = receiptSnapshot.value
  const orderData = snapshot.order || {}
  const clientData = snapshot.client || {}
  const equipmentData = snapshot.equipment || {}
  const receptionData = snapshot.reception || {}
  const trackingData = snapshot.tracking || {}

  const printWindow = window.open('', '_blank')

  if (!printWindow) {
    deliveryError.value =
      'El navegador bloqueó la ventana de impresión. Permite ventanas emergentes e inténtalo nuevamente.'
    return
  }

  const identifier = equipmentData.identifier
    ? `
      <div class="row">
        <span>${escapeHtml(
          equipmentData.identifier_label || 'Identificador'
        )}</span>
        <strong>${escapeHtml(equipmentData.identifier)}</strong>
      </div>
    `
    : ''

  printWindow.document.write(`
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>Comprobante ${escapeHtml(orderData.tracking_code)}</title>
        <style>
          * { box-sizing: border-box; }
          body {
            font-family: Arial, sans-serif;
            color: #111;
            margin: 32px;
            line-height: 1.4;
          }
          .header {
            display: flex;
            justify-content: space-between;
            gap: 24px;
            border-bottom: 2px solid #111;
            padding-bottom: 16px;
            margin-bottom: 20px;
          }
          h1 { margin: 0; font-size: 24px; }
          h2 { font-size: 16px; margin: 22px 0 10px; }
          .code { font-size: 20px; font-weight: 700; }
          .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px 24px;
          }
          .row {
            display: flex;
            flex-direction: column;
            border-bottom: 1px solid #ddd;
            padding: 7px 0;
          }
          .row span { color: #555; font-size: 12px; }
          .box {
            border: 1px solid #bbb;
            padding: 12px;
            min-height: 56px;
            white-space: pre-wrap;
          }
          .confirmation {
            margin-top: 22px;
            border: 1px solid #111;
            padding: 14px;
          }
          .signatures {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 50px;
            margin-top: 70px;
          }
          .signature {
            border-top: 1px solid #111;
            text-align: center;
            padding-top: 6px;
          }
          .small { font-size: 12px; color: #555; }
          @media print {
            body { margin: 15mm; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div>
            <h1>${escapeHtml(snapshot.business?.name || 'Martini Cell')}</h1>
            <div>Comprobante de recepción</div>
          </div>
          <div>
            <div class="small">Código de orden y seguimiento</div>
            <div class="code">${escapeHtml(orderData.tracking_code)}</div>
          </div>
        </div>

        <div class="grid">
          <div class="row">
            <span>Fecha y hora de recepción</span>
            <strong>${escapeHtml(formatDateTime(orderData.received_at))}</strong>
          </div>
          <div class="row">
            <span>Recibido por</span>
            <strong>${escapeHtml(receptionData.received_by || 'Martini Cell')}</strong>
          </div>
        </div>

        <h2>Cliente</h2>
        <div class="grid">
          <div class="row">
            <span>Nombre</span>
            <strong>${escapeHtml(clientData.name)}</strong>
          </div>
          <div class="row">
            <span>Teléfono</span>
            <strong>${escapeHtml(clientData.phone || 'No registrado')}</strong>
          </div>
          <div class="row">
            <span>Correo</span>
            <strong>${escapeHtml(clientData.email || 'No registrado')}</strong>
          </div>
        </div>

        <h2>Equipo recibido</h2>
        <div class="grid">
          <div class="row">
            <span>Tipo</span>
            <strong>${escapeHtml(
              equipmentData.type_display || equipmentData.type
            )}</strong>
          </div>
          <div class="row">
            <span>Marca</span>
            <strong>${escapeHtml(equipmentData.brand)}</strong>
          </div>
          <div class="row">
            <span>Modelo</span>
            <strong>${escapeHtml(equipmentData.model)}</strong>
          </div>
          <div class="row">
            <span>Color</span>
            <strong>${escapeHtml(equipmentData.color || 'No registrado')}</strong>
          </div>
          ${identifier}
        </div>

        <h2>Recepción</h2>
        <div class="small">Falla o problema informado</div>
        <div class="box">${escapeHtml(receptionData.reported_issue)}</div>

        <div class="small" style="margin-top:12px;">Condición / observaciones iniciales</div>
        <div class="box">${escapeHtml(
          receptionData.initial_observations || 'Sin observaciones adicionales'
        )}</div>

        <div class="small" style="margin-top:12px;">Accesorios entregados</div>
        <div class="box">${escapeHtml(
          receptionData.received_accessories || 'Sin accesorios registrados'
        )}</div>

        <div class="row" style="margin-top:12px;">
          <span>Abono recibido</span>
          <strong>${escapeHtml(formatMoney(receptionData.deposit_amount))}</strong>
        </div>

        <div class="confirmation">
          <strong>${escapeHtml(
            receptionData.confirmation ||
            'Martini Cell confirma la recepción del equipo descrito.'
          )}</strong>
          <div class="small" style="margin-top:8px;">
            ${escapeHtml(trackingData.instructions || '')}
          </div>
        </div>

        <div class="signatures">
          <div class="signature">Firma cliente</div>
          <div class="signature">Firma recepción Martini Cell</div>
        </div>
      </body>
    </html>
  `)

  printWindow.document.close()
  printWindow.focus()

  setTimeout(() => {
    printWindow.print()
  }, 250)
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

  const deposit = Number(order.value.deposit_amount || 0)

  if (!Number.isFinite(deposit) || deposit < 0) {
    error.value =
      'El abono debe ser un monto igual o mayor a cero.'
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
        received_accessories:
          order.value.received_accessories.trim(),
        deposit_amount: deposit,
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)

      throw new Error(formatApiErrors(data))
    }

    // Django devuelve el ID y el mismo código utilizado para seguimiento.
    createdOrder.value = await response.json()
    chooseDefaultDeliveryMethod()

    // Generar inmediatamente la vista previa de recepción.
    await generateReceipt()

  } catch (err) {
    error.value =
      err.message || 'No fue posible crear la orden.'

  } finally {
    saving.value = false
  }
}

function restart() {
  createdOrder.value = null
  receipt.value = null

  step.value = 1
  clientId.value = ''
  equipmentId.value = ''
  clientSearch.value = ''

  order.value = {
    reported_issue: '',
    initial_observations: '',
    received_accessories: '',
    deposit_amount: '',
  }

  receiptLoading.value = false
  receiptError.value = ''
  deliveryMethod.value = ''
  deliveringReceipt.value = false
  deliverySuccess.value = ''
  deliveryError.value = ''

  error.value = ''
}

onMounted(loadData)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Nueva orden de servicio

      <template #subtitle>
        Registro de recepción y comprobante para el cliente.
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

    <!-- HU-34: orden creada + comprobante de recepción -->
    <div
      v-else-if="createdOrder"
      class="d-flex flex-column gap-3"
    >
      <div class="mc-card p-4">
        <div class="alert alert-success" role="status">
          <i class="bi bi-check-circle me-2"></i>
          Orden de servicio creada correctamente.
        </div>

        <div class="d-flex flex-wrap justify-content-between gap-3">
          <div>
            <div class="small text-muted">
              Código único de orden y seguimiento
            </div>

            <h3 class="mb-1">
              {{ createdOrder.tracking_code }}
            </h3>

            <div class="text-muted">
              La orden y el seguimiento utilizan el mismo código.
            </div>
          </div>

          <div class="text-md-end">
            <div>
              <strong>Cliente:</strong>
              {{ createdOrder.client_name }}
            </div>

            <div>
              <strong>Equipo:</strong>
              {{ createdOrder.equipment_description }}
            </div>

            <div>
              <strong>Fecha:</strong>
              {{ formatDateTime(createdOrder.received_at) }}
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="receiptLoading"
        class="mc-card p-4 text-center"
      >
        <div
          class="spinner-border text-primary mb-2"
          role="status"
        ></div>

        <div class="text-muted">
          Generando comprobante de recepción...
        </div>
      </div>

      <div
        v-else-if="receiptError"
        class="mc-card p-4"
      >
        <div class="alert alert-warning mb-3">
          {{ receiptError }}
        </div>

        <button
          type="button"
          class="btn btn-primary"
          @click="generateReceipt"
        >
          Reintentar generar comprobante
        </button>
      </div>

      <template v-else-if="receipt">
        <!-- Vista previa -->
        <div class="mc-card p-4">
          <div
            class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4"
          >
            <div>
              <h4 class="mb-1">
                Comprobante de recepción
              </h4>

              <div class="text-muted">
                Vista previa antes de entregar al cliente.
              </div>
            </div>

            <div class="text-end">
              <div class="small text-muted">
                Código de orden y seguimiento
              </div>

              <strong class="fs-5">
                {{ receiptOrder.tracking_code }}
              </strong>
            </div>
          </div>

          <div class="row g-3">
            <div class="col-lg-6">
              <div class="border rounded p-3 h-100">
                <h6>Recepción</h6>

                <div class="mb-2">
                  <span class="text-muted">Fecha y hora:</span><br>
                  <strong>
                    {{ formatDateTime(receiptOrder.received_at) }}
                  </strong>
                </div>

                <div class="mb-2">
                  <span class="text-muted">Recibido por:</span><br>
                  <strong>
                    {{ receiptReception.received_by || 'Martini Cell' }}
                  </strong>
                </div>

                <div>
                  <span class="text-muted">Estado inicial:</span><br>
                  <strong>
                    {{
                      receiptOrder.status_display ||
                      receiptOrder.status
                    }}
                  </strong>
                </div>
              </div>
            </div>

            <div class="col-lg-6">
              <div class="border rounded p-3 h-100">
                <h6>Cliente</h6>

                <div class="mb-2">
                  <strong>{{ receiptClient.name }}</strong>
                </div>

                <div class="small">
                  <strong>Teléfono:</strong>
                  {{ receiptClient.phone || 'No registrado' }}
                </div>

                <div class="small">
                  <strong>Correo:</strong>
                  {{ receiptClient.email || 'No registrado' }}
                </div>
              </div>
            </div>

            <div class="col-lg-6">
              <div class="border rounded p-3 h-100">
                <h6>Equipo recibido</h6>

                <div>
                  <strong>
                    {{
                      receiptEquipment.type_display ||
                      receiptEquipment.type
                    }}
                    ·
                    {{ receiptEquipment.brand }}
                    {{ receiptEquipment.model }}
                  </strong>
                </div>

                <div
                  v-if="receiptEquipment.color"
                  class="small mt-2"
                >
                  <strong>Color:</strong>
                  {{ receiptEquipment.color }}
                </div>

                <div
                  v-if="receiptEquipment.identifier"
                  class="small"
                >
                  <strong>
                    {{ receiptEquipment.identifier_label }}:
                  </strong>
                  {{ receiptEquipment.identifier }}
                </div>
              </div>
            </div>

            <div class="col-lg-6">
              <div class="border rounded p-3 h-100">
                <h6>Información de ingreso</h6>

                <div class="small text-muted">
                  Falla reportada
                </div>

                <div class="mb-3">
                  {{ receiptReception.reported_issue }}
                </div>

                <div class="small text-muted">
                  Condición / observaciones iniciales
                </div>

                <div class="mb-3">
                  {{
                    receiptReception.initial_observations ||
                    'Sin observaciones adicionales'
                  }}
                </div>

                <div class="small text-muted">
                  Accesorios entregados
                </div>

                <div class="mb-3">
                  {{
                    receiptReception.received_accessories ||
                    'Sin accesorios registrados'
                  }}
                </div>

                <div class="small text-muted">
                  Abono recibido
                </div>

                <strong>
                  {{ formatMoney(receiptReception.deposit_amount) }}
                </strong>
              </div>
            </div>
          </div>

          <div class="alert alert-light border mt-3 mb-0">
            <strong>
              {{
                receiptReception.confirmation ||
                'Martini Cell confirma la recepción del equipo descrito.'
              }}
            </strong>

            <div class="small text-muted mt-2">
              {{ receiptTracking.instructions }}
            </div>
          </div>
        </div>

        <!-- Medio de entrega -->
        <div class="mc-card p-4">
          <h5>Entregar comprobante al cliente</h5>

          <p class="text-muted">
            El medio digital elegido quedará como canal preferido
            para las futuras notificaciones de esta orden.
          </p>

          <div
            v-if="deliverySuccess"
            class="alert alert-success"
            role="status"
          >
            {{ deliverySuccess }}
          </div>

          <div
            v-if="deliveryError"
            class="alert alert-danger"
            role="alert"
          >
            {{ deliveryError }}
          </div>

          <div class="row g-3 mb-3">
            <div class="col-md-4">
              <label class="border rounded p-3 d-block h-100">
                <div class="form-check">
                  <input
                    v-model="deliveryMethod"
                    class="form-check-input"
                    type="radio"
                    name="receipt-delivery"
                    value="EMAIL"
                    :disabled="!clientHasEmail || deliveringReceipt"
                  >

                  <span class="form-check-label fw-semibold">
                    <i class="bi bi-envelope me-1"></i>
                    Correo
                  </span>
                </div>

                <div class="small text-muted mt-2">
                  {{
                    clientHasEmail
                      ? selectedClient.email
                      : 'El cliente no tiene correo registrado.'
                  }}
                </div>
              </label>
            </div>

            <div class="col-md-4">
              <label class="border rounded p-3 d-block h-100">
                <div class="form-check">
                  <input
                    v-model="deliveryMethod"
                    class="form-check-input"
                    type="radio"
                    name="receipt-delivery"
                    value="WHATSAPP"
                    :disabled="!clientHasPhone || deliveringReceipt"
                  >

                  <span class="form-check-label fw-semibold">
                    <i class="bi bi-whatsapp me-1"></i>
                    WhatsApp
                  </span>
                </div>

                <div class="small text-muted mt-2">
                  {{
                    clientHasPhone
                      ? selectedClient.phone
                      : 'El cliente no tiene teléfono registrado.'
                  }}
                </div>

                <div class="small text-muted mt-1">
                  Primera versión: se abrirá WhatsApp con
                  el mensaje preparado para envío manual.
                </div>
              </label>
            </div>

            <div class="col-md-4">
              <label class="border rounded p-3 d-block h-100">
                <div class="form-check">
                  <input
                    v-model="deliveryMethod"
                    class="form-check-input"
                    type="radio"
                    name="receipt-delivery"
                    value="PRINT"
                    :disabled="deliveringReceipt"
                  >

                  <span class="form-check-label fw-semibold">
                    <i class="bi bi-printer me-1"></i>
                    Impreso
                  </span>
                </div>

                <div class="small text-muted mt-2">
                  Abre una versión limpia para imprimir
                  o guardar como PDF.
                </div>
              </label>
            </div>
          </div>

          <div
            v-if="deliveryMethod === 'PRINT' && printNotificationNotice"
            class="alert"
            :class="
              clientHasPhone || clientHasEmail
                ? 'alert-info'
                : 'alert-warning'
            "
          >
            {{ printNotificationNotice }}
          </div>

          <div class="d-flex flex-wrap gap-2">
            <button
              type="button"
              class="btn btn-primary"
              :disabled="
                deliveringReceipt ||
                !deliveryMethod ||
                (
                  deliveryMethod === 'EMAIL' &&
                  !clientHasEmail
                ) ||
                (
                  deliveryMethod === 'WHATSAPP' &&
                  !clientHasPhone
                ) ||
                (
                  deliveryMethod === 'PRINT' &&
                  !clientHasEmail &&
                  !clientHasPhone
                )
              "
              @click="deliverReceipt(deliveryMethod)"
            >
              <span
                v-if="deliveringReceipt"
                class="spinner-border spinner-border-sm me-2"
                aria-hidden="true"
              ></span>

              {{
                deliveringReceipt
                  ? 'Procesando...'
                  : deliveryMethod === 'EMAIL'
                    ? 'Enviar por correo'
                    : deliveryMethod === 'WHATSAPP'
                      ? 'Preparar WhatsApp'
                      : 'Registrar e imprimir'
              }}
            </button>

            <button
              type="button"
              class="btn btn-outline-secondary"
              :disabled="deliveringReceipt"
              @click="printReceipt"
            >
              <i class="bi bi-printer me-1"></i>
              Vista de impresión
            </button>
          </div>

          <div
            v-if="receipt.deliveries?.length"
            class="mt-4"
          >
            <h6>Historial de entrega</h6>

            <div class="table-responsive">
              <table class="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th>Medio</th>
                    <th>Estado</th>
                    <th>Destino</th>
                    <th>Fecha</th>
                  </tr>
                </thead>

                <tbody>
                  <tr
                    v-for="item in receipt.deliveries"
                    :key="item.id"
                  >
                    <td>
                      {{
                        item.delivery_method_display ||
                        item.delivery_method
                      }}
                    </td>

                    <td>
                      {{
                        item.status_display ||
                        item.status
                      }}
                    </td>

                    <td>
                      {{ item.destination || '—' }}
                    </td>

                    <td>
                      {{ formatDateTime(item.created_at) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="d-flex flex-wrap gap-2">
          <router-link
            :to="`/ordenes/${createdOrder.id}`"
            class="btn btn-outline-secondary"
          >
            Ver detalle de la orden
          </router-link>

          <button
            type="button"
            class="btn btn-outline-primary"
            @click="restart"
          >
            Crear otra orden
          </button>
        </div>
      </template>
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
                <strong>Tipo:</strong>
                {{
                  selectedEquipment.equipment_type_display ||
                  selectedEquipment.equipment_type
                }}
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
          Condición y observaciones iniciales
        </label>

        <textarea
          id="initial-observations"
          v-model="order.initial_observations"
          class="form-control mb-3"
          rows="3"
          placeholder="Ej.: pantalla quebrada, rayas, carcasa marcada, equipo no enciende."
        ></textarea>

        <label
          for="received-accessories"
          class="form-label"
        >
          Accesorios entregados
        </label>

        <textarea
          id="received-accessories"
          v-model="order.received_accessories"
          class="form-control mb-3"
          rows="2"
          placeholder="Ej.: cargador, funda, cable. Si no entrega accesorios, puede quedar vacío."
        ></textarea>

        <label
          for="deposit-amount"
          class="form-label"
        >
          Abono recibido
        </label>

        <div class="input-group mb-3">
          <span class="input-group-text">$</span>

          <input
            id="deposit-amount"
            v-model="order.deposit_amount"
            type="number"
            min="0"
            step="1"
            class="form-control"
            placeholder="0"
          >
        </div>

        <div class="form-text">
          Django registrará automáticamente la fecha,
          hora y usuario que recibe el equipo.
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

              <div class="small text-muted">
                Teléfono:
                {{ selectedClient?.phone || 'No registrado' }}
              </div>

              <div class="small text-muted">
                Correo:
                {{ selectedClient?.email || 'No registrado' }}
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

              <div class="mb-2">
                {{
                  order.initial_observations ||
                  'Sin observaciones adicionales'
                }}
              </div>

              <div class="small text-muted">
                Accesorios
              </div>

              <div class="mb-2">
                {{
                  order.received_accessories ||
                  'Sin accesorios registrados'
                }}
              </div>

              <div class="small text-muted">
                Abono
              </div>

              <strong>
                {{ formatMoney(order.deposit_amount) }}
              </strong>
            </div>
          </div>
        </div>

        <div class="alert alert-info mt-3 mb-0">
          Al confirmar, Django generará el código único de la orden.
          Después podrás revisar el comprobante y elegir si entregarlo
          por correo, WhatsApp o impreso.
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
