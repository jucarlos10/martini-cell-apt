<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'

defineProps({
  order: { type: Object, required: true },
})

const visible = ref(false)
const closeButton = ref(null)
const printButton = ref(null)
const issuedAt = ref(null)
const consultationUrl = `${window.location.origin}/consulta`
let previousFocus = null

function formatDate(value) {
  if (!value) return 'No disponible'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'No disponible'

  return new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(date)
}

async function openReceipt() {
  previousFocus = document.activeElement
  issuedAt.value = new Date()
  visible.value = true
  document.body.classList.add('intake-receipt-visible')
  await nextTick()
  closeButton.value?.focus()
}

async function closeReceipt() {
  visible.value = false
  document.body.classList.remove('intake-receipt-visible')
  await nextTick()
  previousFocus?.focus?.()
}

function trapFocus(event) {
  const buttons = [closeButton.value, printButton.value]
    .filter(Boolean)
  if (!buttons.length) return

  const first = buttons[0]
  const last = buttons[buttons.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

function printReceipt() {
  window.print()
}

onBeforeUnmount(() => {
  document.body.classList.remove('intake-receipt-visible')
})
</script>

<template>
  <button type="button" class="btn btn-outline-primary" @click="openReceipt">
    <i class="bi bi-printer me-1" aria-hidden="true"></i>
    Comprobante de recepción
  </button>

  <Teleport to="body">
    <div
      v-if="visible"
      class="intake-receipt-overlay"
      role="presentation"
      @click.self="closeReceipt"
      @keydown.esc.prevent="closeReceipt"
      @keydown.tab="trapFocus"
    >
      <div
        class="intake-receipt-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="intake-receipt-title"
      >
        <div class="intake-receipt-actions">
          <div>
            <strong>Vista previa</strong>
            <div class="small text-muted">Entregar el comprobante solo al cliente correspondiente.</div>
          </div>
          <div class="d-flex flex-wrap gap-2">
            <button ref="closeButton" type="button" class="btn btn-outline-secondary" @click="closeReceipt">
              Cerrar
            </button>
            <button ref="printButton" type="button" class="btn btn-primary" @click="printReceipt">
              Imprimir o guardar PDF
            </button>
          </div>
        </div>

        <article class="intake-receipt-sheet">
          <header class="intake-receipt-header">
            <div>
              <div class="intake-receipt-brand">MARTINI CELL</div>
              <h1 id="intake-receipt-title">Comprobante de recepción</h1>
              <p>Resumen de la orden al momento de emitir este comprobante.</p>
            </div>
            <div class="intake-receipt-code">
              <span>Código de seguimiento</span>
              <strong>{{ order.tracking_code }}</strong>
            </div>
          </header>

          <dl class="intake-receipt-details">
            <div><dt>Orden</dt><dd>#{{ order.id }}</dd></div>
            <div><dt>Fecha de ingreso</dt><dd>{{ formatDate(order.received_at) }}</dd></div>
            <div><dt>Cliente</dt><dd>{{ order.client_name }}</dd></div>
            <div><dt>Equipo recibido</dt><dd>{{ order.equipment_description }}</dd></div>
          </dl>

          <section class="intake-receipt-description">
            <h2>Falla informada por el cliente</h2>
            <p>{{ order.reported_issue }}</p>
            <h2>Observaciones al ingreso</h2>
            <p>{{ order.initial_observations || 'Sin observaciones registradas.' }}</p>
          </section>

          <footer class="intake-receipt-footer">
            <strong>Consulta el estado de tu equipo</strong>
            <p>Ingresa el código de seguimiento en {{ consultationUrl }}</p>
            <p>La falla informada al ingreso no constituye un diagnóstico técnico.</p>
            <small>Emitido el {{ formatDate(issuedAt) }}. Este comprobante no acredita un pago ni una autorización de reparación.</small>
          </footer>
        </article>
      </div>
    </div>
  </Teleport>
</template>

<style>
.intake-receipt-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  overflow: auto;
  background: rgba(16, 42, 67, .75);
  padding: 24px;
}

.intake-receipt-dialog {
  max-width: 780px;
  margin: 0 auto;
  border-radius: 10px;
  background: white;
  box-shadow: 0 20px 60px rgba(0, 0, 0, .2);
}

.intake-receipt-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid #d9e1e8;
}

.intake-receipt-sheet {
  padding: 36px;
  color: #102a43;
  overflow-wrap: anywhere;
}

.intake-receipt-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 2px solid #102a43;
  padding-bottom: 24px;
}

.intake-receipt-brand { font-weight: 800; letter-spacing: .08em; }
.intake-receipt-header h1 { font-size: 1.45rem; margin: 12px 0 6px; }
.intake-receipt-header p { margin: 0; color: #475569; }
.intake-receipt-code { display: grid; align-content: center; gap: 4px; }
.intake-receipt-code span, .intake-receipt-details dt { color: #475569; font-size: .85rem; }
.intake-receipt-code strong { font-size: 1.3rem; }
.intake-receipt-details { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin: 28px 0; }
.intake-receipt-details dd { margin: 4px 0 0; font-weight: 600; }
.intake-receipt-description { border-top: 1px solid #d9e1e8; padding-top: 20px; }
.intake-receipt-description h2 { font-size: 1rem; font-weight: 700; }
.intake-receipt-description p { white-space: pre-wrap; margin-bottom: 20px; }
.intake-receipt-footer { border-top: 1px solid #d9e1e8; padding-top: 20px; }
.intake-receipt-footer p { margin: 8px 0 16px; }
.intake-receipt-footer small { color: #475569; }

@media (max-width: 600px) {
  .intake-receipt-overlay { padding: 12px; }
  .intake-receipt-sheet { padding: 22px; }
  .intake-receipt-details { grid-template-columns: 1fr; gap: 12px; }
}

@media print {
  body.intake-receipt-visible { background: white; }
  body.intake-receipt-visible > :not(.intake-receipt-overlay) { display: none !important; }
  .intake-receipt-overlay { position: static; overflow: visible; background: none; padding: 0; }
  .intake-receipt-dialog { max-width: none; border-radius: 0; box-shadow: none; }
  .intake-receipt-actions { display: none !important; }
  .intake-receipt-sheet { padding: 0; }
  .intake-receipt-details { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
