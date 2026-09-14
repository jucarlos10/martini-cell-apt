<script setup>
import { ref, computed } from 'vue'; import AdminLayout from '../layouts/AdminLayout.vue'; import PageHeader from '../components/PageHeader.vue'; import StatusBadge from '../components/StatusBadge.vue'; import {store,statusLabels} from '../mockStore'
const search=ref(''),status=ref('')
const rows=computed(()=>store.orders.filter(o=>(!status.value||o.status===status.value)&&(!search.value||`${o.code} ${o.client_name} ${o.device_name}`.toLowerCase().includes(search.value.toLowerCase()))))
const statuses=[['','Todos'],...Object.entries(statusLabels)]
</script>
<template><AdminLayout>
<PageHeader>Órdenes de servicio<template #subtitle>Gestión y consulta visual de reparaciones.</template><template #actions><router-link to="/ordenes/nueva" class="btn btn-primary"><i class="bi bi-plus-lg me-1"></i>Nueva orden</router-link></template></PageHeader>
<div class="mc-card p-3"><div class="row g-2 mb-3"><div class="col-md-8"><input v-model="search" class="form-control" placeholder="Buscar por código, cliente o equipo..."></div><div class="col-md-4"><select v-model="status" class="form-select"><option v-for="s in statuses" :value="s[0]">{{s[1]}}</option></select></div></div><div class="table-responsive"><table class="table table-hover mb-0"><thead><tr><th>Código</th><th>Cliente</th><th>Equipo</th><th>Estado</th><th>Responsable</th><th>Ingreso</th><th>Actualización</th></tr></thead><tbody><tr v-if="!rows.length"><td colspan="7" class="empty-state">No hay órdenes para los filtros seleccionados.</td></tr><tr v-for="o in rows" :key="o.id"><td><router-link :to="`/ordenes/${o.id}`" class="fw-semibold">{{o.code}}</router-link></td><td>{{o.client_name}}</td><td>{{o.device_name}}</td><td><StatusBadge :status="o.status" :label="statusLabels[o.status]"/></td><td>{{o.assigned_name}}</td><td>{{new Date(o.created_at).toLocaleDateString('es-CL')}}</td><td>{{new Date(o.updated_at).toLocaleString('es-CL')}}</td></tr></tbody></table></div></div>
</AdminLayout></template>
