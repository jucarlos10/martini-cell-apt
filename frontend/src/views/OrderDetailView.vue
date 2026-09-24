<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { authenticatedFetch, getCurrentUser } from '../services/auth'

const route = useRoute()
const currentUser = getCurrentUser()
const canEditReport = ['ADMIN', 'TECH'].includes(currentUser?.role)

const order = ref(null)
const history = ref([])
const technicalReport = ref(null)
const times = ref(null)

// HU-09: informe técnico real y sus revisiones.
const technicalReportHistory = ref([])
const reportHistoryLoading = ref(false)
const reportHistoryError = ref('')
const reportSaving = ref(false)
const reportFormError = ref('')
const reportSuccess = ref('')
const technicians = ref([])
const techniciansLoading = ref(false)
const techniciansError = ref('')

const emptyReportForm = () => ({
  diagnosis: '',
  repair_actions: '',
  repair_observations: '',
  parts_description: '',
  result: '',
  technician: '',
})
const reportForm = ref(emptyReportForm())

const reportResults = [
  { value: 'REPARADO', label: 'Reparado' },
  { value: 'PARCIAL', label: 'Reparado parcialmente' },
  { value: 'NO_REPARABLE', label: 'No reparable' },
  { value: 'SIN_FALLA', label: 'Sin falla detectada' },
]

const tab = ref('resumen')
const loading = ref(true)
const error = ref('')
const historyError = ref('')
const reportError = ref('')
const timesError = ref('')

// HU-08: evidencias fotográficas asociadas a la orden real.
const evidences = ref([])
const evidenceLoading = ref(false)
const evidenceError = ref('')
const uploadingEvidence = ref(false)
const uploadError = ref('')
const uploadSuccess = ref('')
const evidenceStage = ref('RECEPCION')
const evidenceDescription = ref('')
const evidenceFile = ref(null)
const evidenceInput = ref(null)
const imageUrls = ref({})
const imageLoading = ref({})
const imageErrors = ref({})

const evidenceStages = [
  { value: 'RECEPCION', label: 'Recepción' },
  { value: 'DIAGNOSTICO', label: 'Diagnóstico' },
  { value: 'REPARACION', label: 'Reparación' },
  { value: 'ENTREGA', label: 'Entrega' },
  { value: 'OTRO', label: 'Otro' },
]

const maxEvidenceSize = 20 * 1024 * 1024
let evidenceRequestId = 0


// Conservamos la estructura de pestañas del prototipo.
// Las secciones pendientes se habilitarán al integrar sus historias.
const tabs = [
  { key: 'resumen', label: 'Resumen', enabled: true },
  { key: 'diagnostico', label: 'Diagnóstico', enabled: true },
  { key: 'linea', label: 'Línea de tiempo', enabled: true },
  { key: 'evidencias', label: 'Evidencias', enabled: true },
  { key: 'repuestos', label: 'Repuestos y costos', enabled: false },
  { key: 'garantia', label: 'Garantía', enabled: false },
  { key: 'viabilidad', label: 'Índice de viabilidad', enabled: false },
]

function formatDate(value) {
  if (!value) return 'No disponible'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Fecha no disponible'

  return date.toLocaleString('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

async function getResponse(url) {
  const response = await authenticatedFetch(url)
  const data = await response.json().catch(() => null)

  return {
    ok: response.ok,
    status: response.status,
    data,
  }
}



function stageLabel(value) {
  return evidenceStages.find((item) => item.value === value)?.label || value
}

function releaseImageUrls() {
  Object.values(imageUrls.value).forEach((url) => URL.revokeObjectURL(url))
  imageUrls.value = {}
  imageLoading.value = {}
  imageErrors.value = {}
}

function resetEvidence() {
  ++evidenceRequestId
  releaseImageUrls()
  evidences.value = []
  evidenceLoading.value = false
  evidenceError.value = ''
  uploadingEvidence.value = false
  uploadError.value = ''
  uploadSuccess.value = ''
  evidenceStage.value = 'RECEPCION'
  evidenceDescription.value = ''
  evidenceFile.value = null
  if (evidenceInput.value) evidenceInput.value.value = ''
}

function evidenceApiError(data, fallback) {
  if (typeof data?.detail === 'string') return data.detail
  if (!data || typeof data !== 'object') return fallback
  return Object.entries(data).map(([field, messages]) => {
    const message = Array.isArray(messages) ? messages.join(' ') : String(messages)
    return `${field}: ${message}`
  }).join(' ') || fallback
}

async function loadEvidences() {
  if (!order.value) return
  const orderId = order.value.id
  const requestId = ++evidenceRequestId
  evidenceLoading.value = true
  evidenceError.value = ''
  releaseImageUrls()

  try {
    const response = await authenticatedFetch(`/api/orders/${orderId}/evidence/`)
    const data = await response.json().catch(() => null)
    if (requestId !== evidenceRequestId) return
    if (!response.ok) {
      throw new Error(evidenceApiError(data, 'No fue posible cargar las evidencias.'))
    }
    evidences.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (err) {
    if (requestId === evidenceRequestId) {
      evidences.value = []
      evidenceError.value = err?.message || 'Error al cargar las evidencias.'
    }
  } finally {
    if (requestId === evidenceRequestId) evidenceLoading.value = false
  }
}

function selectTab(key) {
  tab.value = key
  if (key === 'evidencias' && order.value) loadEvidences()
}

function selectEvidenceFile(event) {
  evidenceFile.value = event.target.files?.[0] || null
  uploadError.value = ''
  uploadSuccess.value = ''
}

async function uploadEvidence() {
  if (uploadingEvidence.value || !order.value) return
  uploadError.value = ''
  uploadSuccess.value = ''
  const file = evidenceFile.value

  if (!file) {
    uploadError.value = 'Selecciona una fotografía.'
    return
  }
  if (!/\.(jpe?g|png|webp)$/i.test(file.name)) {
    uploadError.value = 'Formato no permitido. Usa JPG, JPEG, PNG o WEBP.'
    return
  }
  if (file.size > maxEvidenceSize) {
    uploadError.value = 'La fotografía no puede superar los 20 MB.'
    return
  }

  const orderId = order.value.id
  const requestId = evidenceRequestId
  const formData = new FormData()
  formData.append('stage', evidenceStage.value)
  formData.append('description', evidenceDescription.value.trim())
  formData.append('image', file)
  uploadingEvidence.value = true

  try {
    // No establecer Content-Type: el navegador agrega el boundary de multipart/form-data.
    const response = await authenticatedFetch(`/api/orders/${orderId}/evidence/`, {
      method: 'POST',
      body: formData,
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(evidenceApiError(data, 'No fue posible adjuntar la fotografía.'))
    }
    if (requestId !== evidenceRequestId) return
    uploadSuccess.value = 'Evidencia registrada correctamente en Django.'
    evidenceFile.value = null
    evidenceDescription.value = ''
    evidenceStage.value = 'RECEPCION'
    if (evidenceInput.value) evidenceInput.value.value = ''
    uploadingEvidence.value = false
    await loadEvidences()
  } catch (err) {
    if (requestId === evidenceRequestId) {
      uploadError.value = err?.message || 'Error al subir la fotografía.'
    }
  } finally {
    if (order.value?.id === orderId) uploadingEvidence.value = false
  }
}

async function toggleEvidenceImage(item) {
  const id = item.id
  if (imageUrls.value[id]) {
    URL.revokeObjectURL(imageUrls.value[id])
    const urls = { ...imageUrls.value }
    delete urls[id]
    imageUrls.value = urls
    return
  }
  if (imageLoading.value[id] || !order.value) return

  const orderId = order.value.id
  const requestId = evidenceRequestId
  imageLoading.value = { ...imageLoading.value, [id]: true }
  imageErrors.value = { ...imageErrors.value, [id]: '' }

  try {
    // La URL privada requiere Authorization; un <img src="/api/..."> no envía el JWT.
    const response = await authenticatedFetch(
      `/api/orders/${orderId}/evidence/${id}/download/`
    )
    if (!response.ok) throw new Error('No fue posible recuperar la fotografía.')
    const blob = await response.blob()
    if (!blob.type.startsWith('image/')) {
      throw new Error('El servidor no devolvió una imagen válida.')
    }
    if (requestId !== evidenceRequestId) return
    imageUrls.value = { ...imageUrls.value, [id]: URL.createObjectURL(blob) }
  } catch (err) {
    if (requestId === evidenceRequestId) {
      imageErrors.value = { ...imageErrors.value, [id]: err?.message || 'Error al abrir la imagen.' }
    }
  } finally {
    if (requestId === evidenceRequestId) {
      imageLoading.value = { ...imageLoading.value, [id]: false }
    }
  }
}

onBeforeUnmount(() => {
  ++evidenceRequestId
  releaseImageUrls()
})


// Administradores pueden asignar técnicos activos; un técnico puede
// registrar el trabajo a su nombre sin acceder a la API de usuarios.
async function loadTechnicians(sequence) {
  technicians.value = []
  techniciansError.value = ''
  if (!canEditReport) return

  if (currentUser?.role === 'TECH') {
    technicians.value = [{
      id: currentUser.id,
      username: currentUser.username,
      is_active: true,
    }]
    return
  }

  techniciansLoading.value = true
  try {
    const response = await getResponse('/api/users/')
    if (sequence !== loadSequence) return
    if (!response.ok) throw new Error('No fue posible consultar los técnicos activos.')

    const users = Array.isArray(response.data)
      ? response.data
      : (response.data?.results || [])
    technicians.value = users.filter((user) => user.role === 'TECH' && user.is_active)
  } catch (err) {
    if (sequence === loadSequence) {
      techniciansError.value = err?.message || 'Error al cargar los técnicos.'
    }
  } finally {
    if (sequence === loadSequence) techniciansLoading.value = false
  }
}

// Conservar el técnico previamente asignado al visualizar un informe
// aunque ya no aparezca en la lista de técnicos activos.
function availableTechnicians() {
  const list = [...technicians.value]
  const assigned = technicalReport.value
  if (assigned?.technician && !list.some((user) => Number(user.id) === Number(assigned.technician))) {
    list.push({
      id: assigned.technician,
      username: `${assigned.technician_username || 'Técnico anterior'} (asignado anteriormente)`,
    })
  }
  return list
}

function resetReportForm() {
  const report = technicalReport.value
  reportForm.value = report
    ? {
        diagnosis: report.diagnosis || '',
        repair_actions: report.repair_actions || '',
        repair_observations: report.repair_observations || '',
        parts_description: report.parts_description || '',
        result: report.result || '',
        technician: report.technician || '',
      }
    : {
        ...emptyReportForm(),
        technician: currentUser?.role === 'TECH' ? currentUser.id : '',
      }
  reportFormError.value = ''
}

async function loadTechnicalReportHistory(orderId, sequence) {
  reportHistoryLoading.value = true
  reportHistoryError.value = ''
  try {
    const response = await getResponse(`/api/orders/${orderId}/technical-report/history/`)
    if (sequence !== loadSequence) return
    if (!response.ok) throw new Error('No fue posible cargar las revisiones del informe.')
    technicalReportHistory.value = Array.isArray(response.data)
      ? response.data
      : (response.data?.results || [])
  } catch (err) {
    if (sequence === loadSequence) {
      reportHistoryError.value = err?.message || 'Error al cargar el historial del informe.'
    }
  } finally {
    if (sequence === loadSequence) reportHistoryLoading.value = false
  }
}

// POST para el primer informe; PATCH para modificarlo sin perder las
// revisiones históricas que registra Django.
async function saveTechnicalReport() {
  if (reportSaving.value || !order.value || !canEditReport) return
  const orderId = order.value.id
  const sequence = loadSequence
  const isEditing = Boolean(technicalReport.value)
  reportFormError.value = ''
  reportSuccess.value = ''

  const payload = {
    diagnosis: reportForm.value.diagnosis.trim(),
    repair_actions: reportForm.value.repair_actions.trim(),
    repair_observations: reportForm.value.repair_observations.trim(),
    parts_description: reportForm.value.parts_description.trim(),
    result: reportForm.value.result,
  }

  if (!payload.diagnosis || !payload.repair_actions || !payload.result) {
    reportFormError.value = 'Completa diagnóstico, reparación y resultado.'
    return
  }

  if (!isEditing || Number(reportForm.value.technician) !== Number(technicalReport.value.technician)) {
    if (!Number(reportForm.value.technician)) {
      reportFormError.value = 'Selecciona un técnico responsable.'
      return
    }
    payload.technician = Number(reportForm.value.technician)
  }

  reportSaving.value = true
  try {
    const response = await authenticatedFetch(`/api/orders/${orderId}/technical-report/`, {
      method: isEditing ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(evidenceApiError(data, 'No fue posible guardar el informe técnico.'))
    }
    if (sequence !== loadSequence) return

    technicalReport.value = data
    reportError.value = ''
    resetReportForm()
    reportSuccess.value = isEditing
      ? 'Informe actualizado y revisión registrada cuando hubo cambios.'
      : 'Informe técnico registrado correctamente.'
    await loadTechnicalReportHistory(orderId, sequence)
  } catch (err) {
    if (sequence === loadSequence) {
      reportFormError.value = err?.message || 'Error al guardar el informe técnico.'
    }
  } finally {
    if (sequence === loadSequence) reportSaving.value = false
  }
}

let loadSequence = 0

async function loadOrder() {
  const sequence = ++loadSequence
  const orderId = String(route.params.id ?? '')

  loading.value = true
  error.value = ''
  historyError.value = ''
  reportError.value = ''
  timesError.value = ''
  technicalReportHistory.value = []
  reportHistoryLoading.value = false
  reportHistoryError.value = ''
  reportSaving.value = false
  reportSuccess.value = ''
  reportFormError.value = ''
  technicians.value = []
  techniciansError.value = ''
  techniciansLoading.value = false
  resetEvidence()

  order.value = null
  history.value = []
  technicalReport.value = null
  times.value = null
  resetReportForm()
  tab.value = 'resumen'

  if (!/^[1-9]\d*$/.test(orderId)) {
    error.value = 'El ID de la orden no es válido.'
    loading.value = false
    return
  }

  try {
    const orderResponse = await getResponse(`/api/orders/${orderId}/`)
    if (sequence !== loadSequence) return

    if (!orderResponse.ok) {
      error.value = orderResponse.status === 404
        ? 'La orden solicitada no existe.'
        : 'No fue posible cargar la orden de servicio.'
      return
    }

    order.value = orderResponse.data

    // Estas consultas son de lectura. Si alguna falla, conservamos
    // el detalle principal y mostramos el problema en su sección.
    const [historyResult, reportResult, timesResult] = await Promise.allSettled([
      getResponse(`/api/orders/${orderId}/status/history/`),
      getResponse(`/api/orders/${orderId}/technical-report/`),
      getResponse(`/api/orders/${orderId}/times/`),
    ])

    if (sequence !== loadSequence) return

    if (
      historyResult.status === 'fulfilled' &&
      historyResult.value.ok &&
      Array.isArray(historyResult.value.data)
    ) {
      history.value = historyResult.value.data
    } else {
      historyError.value = 'No fue posible cargar la línea de tiempo.'
    }

    if (reportResult.status === 'fulfilled') {
      if (reportResult.value.ok) {
        technicalReport.value = reportResult.value.data
      } else if (reportResult.value.status !== 404) {
        reportError.value = 'No fue posible consultar el informe técnico.'
      }
    } else {
      reportError.value = 'No fue posible consultar el informe técnico.'
    }
    resetReportForm()

    // Las revisiones y los técnicos se consultan separadamente.
    // Fallar en una de estas consultas no oculta el detalle principal.
    await Promise.allSettled([
      loadTechnicians(sequence),
      ...(technicalReport.value ? [loadTechnicalReportHistory(orderId, sequence)] : []),
    ])
    if (sequence !== loadSequence) return

    if (timesResult.status === 'fulfilled') {
      if (timesResult.value.ok) {
        times.value = timesResult.value.data
      } else {
        timesError.value = timesResult.value.status === 409
          ? (timesResult.value.data?.detail || 'El historial no permite calcular los tiempos.')
          : 'No fue posible calcular los tiempos del servicio.'
      }
    } else {
      timesError.value = 'No fue posible calcular los tiempos del servicio.'
    }
  } catch (err) {
    if (sequence === loadSequence) {
      error.value = err?.message || 'No fue posible cargar la orden de servicio.'
    }
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

// Permite cambiar entre /ordenes/1 y /ordenes/2 sin mostrar datos antiguos.
watch(() => route.params.id, loadOrder, { immediate: true })
</script>

<template>
  <AdminLayout>
    <div v-if="loading" class="mc-card p-4 text-center">
      <div class="spinner-border text-primary mb-2" role="status"></div>
      <div class="text-muted">Cargando orden de servicio...</div>
    </div>

    <div v-else-if="error" class="alert alert-warning" role="alert">
      {{ error }}
      <div class="mt-3">
        <router-link to="/ordenes" class="btn btn-outline-secondary btn-sm">
          Volver a órdenes
        </router-link>
        <button type="button" class="btn btn-outline-primary btn-sm ms-2" @click="loadOrder">
          Reintentar
        </button>
      </div>
    </div>

    <template v-else-if="order">
      <PageHeader>
        {{ order.tracking_code }}
        <StatusBadge
          :status="order.status"
          :label="order.status_display || order.status"
        />

        <template #subtitle>
          {{ order.equipment_description }} · Cliente: {{ order.client_name }}
          · Registrado por: {{ order.created_by_username || 'No disponible' }}
        </template>

        <template #actions>
          <router-link to="/ordenes" class="btn btn-outline-secondary">
            Volver a órdenes
          </router-link>
        </template>
      </PageHeader>

      <div class="section-tabs mb-4">
        <button
          v-for="item in tabs"
          :key="item.key"
          type="button"
          :class="{ active: tab === item.key }"
          :disabled="!item.enabled"
          :title="item.enabled ? item.label : `${item.label}: integración pendiente`"
          @click="selectTab(item.key)"
        >
          {{ item.label }}
          <span v-if="!item.enabled" class="small">(pendiente)</span>
        </button>
      </div>

      <!-- RESUMEN: información real de la orden y sus tiempos -->
      <section v-if="tab === 'resumen'" class="row g-3">
        <div class="col-lg-8">
          <div class="mc-card p-4 h-100">
            <h5>Información general</h5>
            <div class="row g-3 mt-1">
              <div class="col-md-6">
                <div class="mc-muted small">Equipo</div>
                <strong>{{ order.equipment_description }}</strong>
                <div class="small text-muted">Equipo #{{ order.equipment }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Estado actual</div>
                <StatusBadge
                  :status="order.status"
                  :label="order.status_display || order.status"
                />
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Falla reportada</div>
                <div>{{ order.reported_issue }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Observaciones iniciales</div>
                <div>{{ order.initial_observations || 'Sin observaciones adicionales' }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Ingreso</div>
                <div>{{ formatDate(order.received_at) }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Última actualización</div>
                <div>{{ formatDate(order.updated_at) }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Diagnóstico actual</div>
                <div>{{ technicalReport?.diagnosis || (reportError || 'Pendiente') }}</div>
              </div>

              <div class="col-md-6">
                <div class="mc-muted small">Trabajo realizado</div>
                <div>{{ technicalReport?.repair_actions || (reportError || 'Pendiente') }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-4">
          <div class="mc-card p-4">
            <h5>Tiempos del servicio</h5>
            <div v-if="timesError" class="alert alert-warning small mb-0">
              {{ timesError }}
            </div>
            <table v-else-if="times" class="table small mb-0">
              <tbody>
                <tr>
                  <td>Tiempo técnico</td>
                  <td class="text-end fw-semibold">{{ times.technical_display }}</td>
                </tr>
                <tr>
                  <td>Tiempo de espera</td>
                  <td class="text-end">{{ times.waiting_display }}</td>
                </tr>
                <tr class="fw-bold">
                  <td>Total</td>
                  <td class="text-end">{{ times.total_display }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="text-muted">Sin datos disponibles.</div>
            <div v-if="times" class="small text-muted mt-2">
              Calculado al consultar la orden. Los tiempos pueden seguir aumentando.
            </div>
          </div>
        </div>
      </section>

      <!-- HU-09: diagnóstico, reparación e historial real -->
      <section v-if="tab === 'diagnostico'" class="row g-3">
        <div class="col-lg-7">
          <div class="mc-card p-4">
            <h5>Diagnóstico y reparación</h5>
            <div class="small text-muted mb-3">
              Orden #{{ order.id }} · {{ order.equipment_description }} · Cliente: {{ order.client_name }}
            </div>

            <div v-if="reportError" class="alert alert-warning" role="alert">
              {{ reportError }}
            </div>
            <div v-else-if="!technicalReport" class="alert alert-info">
              Esta orden aún no tiene informe técnico. El formulario registra el diagnóstico,
              la reparación y el resultado en una sola operación.
            </div>
            <div v-else class="alert alert-light border small">
              Informe registrado por {{ technicalReport.created_by_username || 'usuario no disponible' }}
              el {{ formatDate(technicalReport.created_at) }}.
              Última actualización: {{ formatDate(technicalReport.updated_at) }}.
            </div>

            <div v-if="reportSuccess" class="alert alert-success" role="status">
              {{ reportSuccess }}
            </div>
            <div v-if="reportFormError" class="alert alert-danger" role="alert">
              {{ reportFormError }}
            </div>

            <form
              v-if="canEditReport && !['DELIVERED', 'CLOSED'].includes(order.status) && !reportError"
              @submit.prevent="saveTechnicalReport"
            >
              <label for="report-technician" class="form-label">Técnico responsable</label>
              <select
                id="report-technician"
                v-model.number="reportForm.technician"
                class="form-select mb-2"
                :disabled="reportSaving || techniciansLoading"
                required
              >
                <option value="">Seleccionar técnico...</option>
                <option
                  v-for="user in availableTechnicians()"
                  :key="user.id"
                  :value="user.id"
                >
                  {{ user.username }}
                </option>
              </select>
              <div v-if="techniciansLoading" class="form-text mb-2">Cargando técnicos...</div>
              <div v-if="techniciansError" class="alert alert-warning small" role="alert">
                {{ techniciansError }}
                <button type="button" class="btn btn-sm btn-outline-secondary ms-2" @click="loadTechnicians(loadSequence)">
                  Reintentar
                </button>
              </div>
              <div v-if="!techniciansLoading && !availableTechnicians().length" class="form-text mb-3">
                No hay técnicos disponibles. Registra o activa uno desde Usuarios.
              </div>
              <div v-else class="mb-3"></div>

              <label for="report-diagnosis" class="form-label">Diagnóstico definitivo</label>
              <textarea
                id="report-diagnosis"
                v-model="reportForm.diagnosis"
                class="form-control mb-3"
                rows="3"
                :disabled="reportSaving"
                required
              ></textarea>

              <label for="report-actions" class="form-label">Acciones de reparación</label>
              <textarea
                id="report-actions"
                v-model="reportForm.repair_actions"
                class="form-control mb-3"
                rows="3"
                :disabled="reportSaving"
                required
              ></textarea>

              <label for="report-observations" class="form-label">Observaciones de reparación (opcional)</label>
              <textarea
                id="report-observations"
                v-model="reportForm.repair_observations"
                class="form-control mb-3"
                rows="2"
                :disabled="reportSaving"
              ></textarea>

              <label for="report-parts" class="form-label">Descripción de repuestos (opcional)</label>
              <textarea
                id="report-parts"
                v-model="reportForm.parts_description"
                class="form-control mb-3"
                rows="2"
                :disabled="reportSaving"
                placeholder="Si no se utilizaron repuestos, deja este campo vacío."
              ></textarea>
              <div class="form-text mb-3">
                La vinculación con catálogo y proveedores se integrará en HU-13.
              </div>

              <label for="report-result" class="form-label">Resultado del servicio</label>
              <select
                id="report-result"
                v-model="reportForm.result"
                class="form-select mb-3"
                :disabled="reportSaving"
                required
              >
                <option value="">Seleccionar resultado...</option>
                <option v-for="result in reportResults" :key="result.value" :value="result.value">
                  {{ result.label }}
                </option>
              </select>

              <button type="submit" class="btn btn-primary" :disabled="reportSaving || techniciansLoading">
                <span v-if="reportSaving" class="spinner-border spinner-border-sm me-2"></span>
                {{ reportSaving ? 'Guardando...' : technicalReport ? 'Guardar cambios' : 'Registrar informe técnico' }}
              </button>
              <button
                v-if="technicalReport"
                type="button"
                class="btn btn-outline-secondary ms-2"
                :disabled="reportSaving"
                @click="resetReportForm"
              >
                Descartar cambios
              </button>
            </form>
            <div v-else-if="!canEditReport" class="alert alert-secondary mb-0">
              Tu rol permite consultar el informe, pero no modificarlo.
            </div>
            <div v-else-if="['DELIVERED', 'CLOSED'].includes(order.status)" class="alert alert-secondary mb-0">
              La orden ya fue entregada o cerrada. El informe se conserva para consulta.
            </div>

            <div v-if="technicalReport && (!canEditReport || ['DELIVERED', 'CLOSED'].includes(order.status))" class="mt-3">
              <div class="mb-2"><strong>Técnico:</strong> {{ technicalReport.technician_username }}</div>
              <div class="mb-2"><strong>Diagnóstico:</strong> {{ technicalReport.diagnosis }}</div>
              <div class="mb-2"><strong>Reparación:</strong> {{ technicalReport.repair_actions }}</div>
              <div class="mb-2"><strong>Observaciones:</strong> {{ technicalReport.repair_observations || 'Sin observaciones' }}</div>
              <div class="mb-2"><strong>Repuestos:</strong> {{ technicalReport.parts_description || 'Sin repuestos descritos' }}</div>
              <div><strong>Resultado:</strong> {{ technicalReport.result_display || technicalReport.result }}</div>
            </div>
          </div>
        </div>

        <div class="col-lg-5">
          <div class="mc-card p-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
              <h5 class="mb-0">Historial del informe</h5>
              <button
                v-if="technicalReport"
                type="button"
                class="btn btn-sm btn-outline-secondary"
                :disabled="reportHistoryLoading"
                @click="loadTechnicalReportHistory(order.id, loadSequence)"
              >
                Actualizar
              </button>
            </div>
            <div v-if="reportHistoryLoading" class="text-muted">Cargando revisiones...</div>
            <div v-else-if="reportHistoryError" class="alert alert-warning" role="alert">{{ reportHistoryError }}</div>
            <div v-else-if="!technicalReport" class="text-muted small">
              Las revisiones aparecerán cuando se registre el primer informe.
            </div>
            <div v-else-if="!technicalReportHistory.length" class="text-muted small">
              No hay revisiones disponibles.
            </div>
            <div v-else class="d-flex flex-column gap-3">
              <div
                v-for="revision in [...technicalReportHistory].reverse()"
                :key="revision.id"
                class="border rounded p-3"
              >
                <div class="fw-semibold">Revisión #{{ revision.revision }}</div>
                <div class="small text-muted mb-2">
                  {{ formatDate(revision.changed_at) }} ·
                  {{ revision.changed_by_username || 'Usuario no disponible' }}
                </div>
                <div class="small"><strong>Técnico:</strong> {{ revision.technician_username }}</div>
                <div class="small mt-1"><strong>Diagnóstico:</strong> {{ revision.diagnosis }}</div>
                <div class="small mt-1"><strong>Reparación:</strong> {{ revision.repair_actions }}</div>
                <div v-if="revision.repair_observations" class="small mt-1">
                  <strong>Observaciones:</strong> {{ revision.repair_observations }}
                </div>
                <div v-if="revision.parts_description" class="small mt-1">
                  <strong>Repuestos:</strong> {{ revision.parts_description }}
                </div>
                <div class="small mt-1">
                  <strong>Resultado:</strong> {{ revision.result_display || revision.result }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- LÍNEA DE TIEMPO: historial persistido en PostgreSQL -->
      <section v-if="tab === 'linea'" class="row g-4">
        <div class="col-lg-7">
          <div class="mc-card p-4">
            <h5>Línea de tiempo</h5>
            <div v-if="historyError" class="alert alert-warning mt-3">
              {{ historyError }}
            </div>
            <div v-else-if="!history.length" class="text-muted mt-3">
              No hay eventos registrados para esta orden.
            </div>
            <div v-else class="timeline mt-4">
              <div
                v-for="event in [...history].reverse()"
                :key="event.id"
                class="timeline-item"
              >
                <div class="fw-semibold">
                  {{ event.to_status_display || event.to_status }}
                </div>
                <div class="small text-muted">
                  {{ formatDate(event.changed_at) }}
                  · {{ event.changed_by_username || 'Usuario no disponible' }}
                </div>
                <div v-if="event.note" class="mt-1">{{ event.note }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-5">
          <div class="mc-card p-4">
            <h5>Estado de la orden</h5>
            <StatusBadge
              :status="order.status"
              :label="order.status_display || order.status"
            />
            <p class="small text-muted mt-3 mb-0">
              Esta línea de tiempo utiliza el historial real de Django.
              La actualización de estados se conectará al integrar HU-10;
              no se guardarán cambios ficticios en el navegador.
            </p>
          </div>
        </div>
      </section>

      <!-- HU-08: evidencias fotográficas privadas de esta orden -->
      <section v-if="tab === 'evidencias'" class="row g-3">
        <div class="col-lg-5">
          <div class="mc-card p-4">
            <h5>Adjuntar evidencia</h5>
            <div class="alert alert-info small mb-3" role="status">
              <div class="fw-semibold mb-1">Esta fotografía se asociará a:</div>
              <div><strong>Orden:</strong> #{{ order.id }} · {{ order.tracking_code }}</div>
              <div><strong>Cliente:</strong> {{ order.client_name }}</div>
              <div><strong>Equipo:</strong> {{ order.equipment_description }} · Equipo #{{ order.equipment }}</div>
              <div class="mt-1">La asociación se realiza automáticamente con la orden abierta.</div>
            </div>
            <p class="small text-muted">
              Usa fotografías ficticias o sin datos identificatorios. Antes de publicar
              imágenes en presentaciones o repositorios, oculta los datos personales
              y los identificadores del equipo.
            </p>

            <div v-if="uploadError" class="alert alert-danger" role="alert">{{ uploadError }}</div>
            <div v-if="uploadSuccess" class="alert alert-success" role="status">{{ uploadSuccess }}</div>

            <form @submit.prevent="uploadEvidence">
              <label for="evidence-stage" class="form-label">Etapa del servicio</label>
              <select
                id="evidence-stage"
                v-model="evidenceStage"
                class="form-select mb-3"
                :disabled="uploadingEvidence"
                required
              >
                <option v-for="stage in evidenceStages" :key="stage.value" :value="stage.value">
                  {{ stage.label }}
                </option>
              </select>

              <label for="evidence-description" class="form-label">Descripción (opcional)</label>
              <textarea
                id="evidence-description"
                v-model="evidenceDescription"
                class="form-control mb-3"
                maxlength="250"
                rows="2"
                :disabled="uploadingEvidence"
                placeholder="Ej.: Estado del equipo al ingresar."
              ></textarea>

              <label for="evidence-file" class="form-label">Fotografía</label>
              <input
                id="evidence-file"
                ref="evidenceInput"
                type="file"
                accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                class="form-control mb-2"
                :disabled="uploadingEvidence"
                required
                @change="selectEvidenceFile"
              >
              <div class="form-text mb-3">JPG, JPEG, PNG o WEBP; máximo 20 MB por archivo.</div>

              <button
                type="submit"
                class="btn btn-primary"
                :disabled="uploadingEvidence || !evidenceFile"
              >
                <span v-if="uploadingEvidence" class="spinner-border spinner-border-sm me-2"></span>
                {{ uploadingEvidence ? 'Subiendo...' : 'Guardar evidencia' }}
              </button>
            </form>
          </div>
        </div>

        <div class="col-lg-7">
          <div class="mc-card p-4">
            <div class="d-flex justify-content-between gap-2 align-items-center mb-3">
              <h5 class="mb-0">Evidencias registradas</h5>
              <button
                type="button"
                class="btn btn-sm btn-outline-secondary"
                :disabled="evidenceLoading"
                @click="loadEvidences"
              >
                Actualizar
              </button>
            </div>
            <div v-if="evidenceLoading" class="text-muted">Cargando evidencias...</div>
            <div v-else-if="evidenceError" class="alert alert-danger" role="alert">
              {{ evidenceError }}
            </div>
            <div v-else-if="!evidences.length" class="text-muted">
              Esta orden todavía no tiene evidencias fotográficas.
            </div>
            <div v-else class="d-flex flex-column gap-3">
              <div v-for="item in evidences" :key="item.id" class="border rounded p-3">
                <div class="d-flex flex-wrap justify-content-between gap-2">
                  <strong>{{ stageLabel(item.stage) }} · Evidencia #{{ item.id }}</strong>
                  <span class="small text-muted">{{ formatDate(item.created_at) }}</span>
                </div>
                <div class="small mt-1">Registrada por: {{ item.uploaded_by_username || 'No disponible' }}</div>
                <div v-if="item.description" class="mt-2">{{ item.description }}</div>

                <div v-if="imageErrors[item.id]" class="alert alert-warning small mt-2 mb-0">
                  {{ imageErrors[item.id] }}
                </div>
                <div class="d-flex flex-wrap gap-2 mt-3">
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-primary"
                    :disabled="imageLoading[item.id]"
                    @click="toggleEvidenceImage(item)"
                  >
                    {{ imageLoading[item.id] ? 'Cargando imagen...' : imageUrls[item.id] ? 'Ocultar fotografía' : 'Ver fotografía' }}
                  </button>
                  <a
                    v-if="imageUrls[item.id]"
                    :href="imageUrls[item.id]"
                    :download="`evidencia-${item.id}`"
                    class="btn btn-sm btn-outline-secondary"
                  >
                    Descargar
                  </a>
                </div>
                <img
                  v-if="imageUrls[item.id]"
                  :src="imageUrls[item.id]"
                  :alt="`Evidencia ${item.id}: ${stageLabel(item.stage)}`"
                  class="img-fluid rounded border mt-3"
                  style="max-height: 360px; object-fit: contain;"
                >
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </AdminLayout>
</template>
