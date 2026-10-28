<script setup>
import { computed, nextTick, ref } from 'vue'

import { buildTrackingShare } from '../utils/trackingShare'

const props = defineProps({
  trackingCode: { type: String, required: true },
})

const share = computed(() => buildTrackingShare(props.trackingCode, window.location.origin))
const notice = ref('')
const fallbackVisible = ref(false)
const fallbackText = ref(null)

async function copyMessage() {
  notice.value = ''
  fallbackVisible.value = false

  try {
    if (!navigator.clipboard?.writeText) throw new Error('Portapapeles no disponible')
    await navigator.clipboard.writeText(share.value.message)
    notice.value = 'Instrucciones copiadas. Verifica el destinatario antes de enviarlas.'
  } catch {
    fallbackVisible.value = true
    notice.value = 'Selecciona y copia el texto para entregarlo al cliente.'
    await nextTick()
    fallbackText.value?.select()
  }
}
</script>

<template>
  <div class="mc-card p-3 p-sm-4" aria-label="Entregar seguimiento al cliente">
    <h5 class="mb-2">Entregar seguimiento al cliente</h5>
    <p class="small text-muted mb-3">
      El cliente puede consultar el estado con su código. Si su teléfono está en
      reparación, entrega el comprobante impreso o utiliza su correo.
    </p>

    <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
      <strong class="text-break">{{ trackingCode }}</strong>
      <span class="text-muted" aria-hidden="true">·</span>
      <a :href="share.consultationUrl" target="_blank" rel="noopener noreferrer">
        Abrir consulta pública
      </a>
    </div>

    <div class="d-flex flex-wrap gap-2">
      <button type="button" class="btn btn-outline-primary btn-sm" @click="copyMessage">
        Copiar instrucciones
      </button>
      <a class="btn btn-outline-secondary btn-sm" :href="share.emailUrl">
        Preparar correo
      </a>
      <a
        class="btn btn-outline-secondary btn-sm"
        :href="share.whatsappUrl"
        target="_blank"
        rel="noopener noreferrer"
      >
        Abrir WhatsApp
      </a>
    </div>

    <p class="small text-muted mt-3 mb-0">
      El correo y WhatsApp se abren con un borrador. Revisa el destinatario y
      envía el mensaje desde esa aplicación; Martini Cell no lo envía automáticamente.
    </p>

    <div v-if="notice" class="small mt-3" role="status">{{ notice }}</div>
    <textarea
      v-if="fallbackVisible"
      ref="fallbackText"
      :value="share.message"
      class="form-control mt-2"
      rows="5"
      readonly
      aria-label="Texto para copiar y entregar al cliente"
      @focus="$event.target.select()"
    ></textarea>
  </div>
</template>
