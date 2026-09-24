<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { authenticatedFetch } from '../services/auth'

const route = useRoute()

const order = ref(null)
const history = ref([])
const technicalReport = ref(null)
const times = ref(null)

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

let loadSequence = 0

async function loadOrder() {
  const sequence = ++loadSequence
  const orderId = String(route.params.id ?? '')

  loading.value = true
  error.value = ''
  historyError.value = ''
  reportError.value = ''
  timesError.value = ''
  resetEvidence()

  order.value = null
  history.value = []
  technicalReport.value = null
  times.value = null
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

      <!-- DIAGNÓSTICO: lectura del informe real, cuando existe -->
      <section v-if="tab === 'diagnostico'" class="mc-card p-4">
        <h5>Diagnóstico y reparación</h5>
        <div v-if="reportError" class="alert alert-warning">{{ reportError }}</div>
        <div v-else-if="!technicalReport" class="alert alert-info mb-0">
          Esta orden todavía no tiene un informe técnico registrado.
          La edición del informe se integrará en su historia correspondiente.
        </div>
        <div v-else class="row g-3 mt-1">
          <div class="col-md-6">
            <div class="mc-muted small">Diagnóstico definitivo</div>
            <div class="fw-semibold">{{ technicalReport.diagnosis }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Reparación realizada</div>
            <div>{{ technicalReport.repair_actions }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Observaciones de reparación</div>
            <div>{{ technicalReport.repair_observations || 'Sin observaciones' }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Repuestos utilizados</div>
            <div>{{ technicalReport.parts_description || 'Sin descripción de repuestos' }}</div>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Resultado</div>
            <strong>{{ technicalReport.result_display || technicalReport.result }}</strong>
          </div>
          <div class="col-md-6">
            <div class="mc-muted small">Técnico responsable</div>
            <strong>{{ technicalReport.technician_username }}</strong>
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
