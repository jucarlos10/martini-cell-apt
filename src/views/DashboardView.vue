<script setup>
import { computed } from 'vue'; import AdminLayout from '../layouts/AdminLayout.vue'; import PageHeader from '../components/PageHeader.vue'; import StatusBadge from '../components/StatusBadge.vue'; import {store,statusLabels} from '../mockStore'
const open=computed(()=>store.orders.filter(o=>!['CLOSED','REJECTED'].includes(o.status)).length)
const auth=computed(()=>store.orders.filter(o=>o.status==='AUTHORIZATION').length)
const part=computed(()=>store.orders.filter(o=>o.status==='PART').length)
const ready=computed(()=>store.orders.filter(o=>o.status==='READY').length)
const recent=computed(()=>[...store.orders].sort((a,b)=>new Date(b.updated_at)-new Date(a.updated_at)).slice(0,5))
</script>
<template><AdminLayout>
<PageHeader>Panel principal<template #subtitle>Resumen de la actividad actual de Martini Cell.</template><template #actions><router-link to="/ordenes/nueva" class="btn btn-primary"><i class="bi bi-plus-lg me-1"></i>Nueva orden</router-link></template></PageHeader>
<div class="mock-note mb-4"><i class="bi bi-info-circle me-1"></i>Datos de demostración. Esta versión no se conecta a API ni base de datos.</div>
<div class="row g-3 mb-4">
  <div class="col-6 col-xl-3" v-for="m in [{l:'Órdenes abiertas',v:open},{l:'Espera autorización',v:auth},{l:'Espera repuesto',v:part},{l:'Listas para entrega',v:ready}]" :key="m.l"><div class="mc-card metric"><div class="value">{{m.v}}</div><div class="mc-muted">{{m.l}}</div></div></div>
</div>
<div class="row g-3">
  <div class="col-xl-8"><div class="mc-card p-3"><div class="d-flex justify-content-between mb-3"><h5 class="mb-0">Órdenes recientes</h5><router-link to="/ordenes">Ver todas</router-link></div><div class="table-responsive"><table class="table mb-0"><thead><tr><th>Código</th><th>Equipo</th><th>Estado</th><th>Responsable</th><th>Actualización</th></tr></thead><tbody><tr v-for="o in recent" :key="o.id"><td><router-link :to="`/ordenes/${o.id}`" class="fw-semibold">{{o.code}}</router-link></td><td>{{o.device_name}}</td><td><StatusBadge :status="o.status" :label="statusLabels[o.status]"/></td><td>{{o.assigned_name}}</td><td>{{new Date(o.updated_at).toLocaleString('es-CL')}}</td></tr></tbody></table></div></div></div>
  <div class="col-xl-4"><div class="mc-card p-4 h-100"><h5>Flujo del servicio</h5><div class="small text-muted mb-3">Vista conceptual del proceso principal.</div><div v-for="s in ['Ingreso','Diagnóstico','Autorización','Repuesto','Reparación','Pruebas','Entrega']" class="d-flex align-items-center gap-2 py-2 border-bottom"><span class="badge rounded-pill text-bg-primary">{{s}}</span></div></div></div>
</div>
</AdminLayout></template>
