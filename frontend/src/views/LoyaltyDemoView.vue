<script setup>
import { computed, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import {
  addDemoVisits,
  applyDemoBenefit,
  createLoyaltyDemo,
  cycleProgress,
} from '../utils/loyaltyDemo.js'

const demo = ref(createLoyaltyDemo())
const progress = computed(() => cycleProgress(demo.value))
const remaining = computed(() => Math.max(0, progress.value.target - progress.value.visits))

function addVisits(amount) {
  demo.value = addDemoVisits(demo.value, amount)
}

function recordBenefit() {
  demo.value = applyDemoBenefit(demo.value)
}

function reset() {
  demo.value = createLoyaltyDemo()
}
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Simulador de beneficios
      <template #subtitle>
        Demostración universitaria del contador de ingresos.
      </template>
      <template #actions>
        <router-link to="/panel" class="btn btn-outline-secondary">Volver al panel</router-link>
      </template>
    </PageHeader>

    <div class="alert alert-info" role="note">
      Esta simulación no guarda clientes, RUT, órdenes ni descuentos. Se reinicia al salir de la página.
    </div>

    <div class="row g-3">
      <div class="col-lg-7">
        <section class="mc-card p-4 h-100" aria-label="Ciclo de beneficios simulado">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
            <h5 class="mb-0">Ciclo {{ demo.completedCycles + 1 }}</h5>
            <span class="badge text-bg-secondary">{{ demo.totalVisits }} ingresos históricos de prueba</span>
          </div>

          <p class="mt-3 mb-2">
            <strong>{{ progress.visits }} de {{ progress.target }} ingresos</strong> para este beneficio.
          </p>
          <div
            class="progress mb-3"
            role="progressbar"
            :aria-valuenow="Math.min(progress.visits, progress.target)"
            :aria-valuemax="progress.target"
            aria-valuemin="0"
            aria-label="Avance del ciclo"
          >
            <div class="progress-bar" :style="{ width: `${Math.min(100, progress.visits / progress.target * 100)}%` }"></div>
          </div>

          <div v-if="progress.pending" class="alert alert-warning" role="status">
            Meta alcanzada. Queda pendiente registrar el beneficio simulado.
            Los ingresos adicionales se conservarán para el próximo ciclo.
          </div>
          <p v-else class="text-muted small">
            Faltan {{ remaining }} ingresos para el aviso de este ciclo.
          </p>

          <div class="d-flex flex-wrap gap-2">
            <button type="button" class="btn btn-outline-primary" @click="addVisits(1)">
              Sumar un ingreso de prueba
            </button>
            <button
              type="button"
              class="btn btn-outline-primary"
              :disabled="progress.pending"
              @click="addVisits(remaining)"
            >
              Completar ciclo
            </button>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!progress.pending"
              @click="recordBenefit"
            >
              Registrar beneficio simulado
            </button>
            <button type="button" class="btn btn-link" @click="reset">
              Reiniciar demostración
            </button>
          </div>
        </section>
      </div>

      <div class="col-lg-5">
        <section class="mc-card p-4 h-100" aria-label="Historial simulado">
          <h5>Historial de la demostración</h5>
          <p v-if="!demo.history.length" class="text-muted mb-0">
            Todavía no se ha registrado un beneficio de prueba.
          </p>
          <ol v-else class="mb-0">
            <li v-for="entry in demo.history" :key="entry.cycle" class="mb-2">
              Ciclo {{ entry.cycle }}: beneficio tras {{ entry.target }} ingresos
              ({{ entry.milestone }} en total).
            </li>
          </ol>
        </section>
      </div>
    </div>
  </AdminLayout>
</template>
