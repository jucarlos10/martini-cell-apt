<script setup>
import { computed } from 'vue'; import { useRouter } from 'vue-router'; import { resetDemo } from '../mockStore'
const router=useRouter(); const user=computed(()=>JSON.parse(localStorage.getItem('martini_demo_user')||'{}'))
function logout(){localStorage.removeItem('martini_demo_session');localStorage.removeItem('martini_demo_user');router.push('/login')}
function reset(){if(confirm('¿Restablecer los datos ficticios del prototipo?')){resetDemo();location.reload()}}
</script>
<template>
<div>
  <aside class="sidebar">
    <div class="brand"><i class="bi bi-tools me-2"></i><span>MARTINI CELL</span></div>
    <div class="demo-pill"><i class="bi bi-bezier2 me-1"></i><span>Prototipo frontend</span></div>
    <nav>
      <router-link to="/panel"><i class="bi bi-house"></i><span>Panel</span></router-link>
      <router-link to="/ordenes"><i class="bi bi-clipboard2-check"></i><span>Órdenes</span></router-link>
      <router-link to="/clientes"><i class="bi bi-people"></i><span>Clientes y equipos</span></router-link>
      <router-link v-if="user.role!=='HELPER'" to="/repuestos"><i class="bi bi-box-seam"></i><span>Repuestos</span></router-link>
      <router-link v-if="user.role!=='HELPER'" to="/garantias"><i class="bi bi-shield-check"></i><span>Garantías</span></router-link>
      <router-link v-if="user.role!=='HELPER'" to="/indicadores"><i class="bi bi-bar-chart"></i><span>Indicadores</span></router-link>
      <router-link v-if="user.role==='ADMIN'" to="/usuarios"><i class="bi bi-person-gear"></i><span>Usuarios y roles</span></router-link>
    </nav>
  </aside>
  <div class="main-shell">
    <header class="topbar">
      <div class="d-flex align-items-center gap-3">
        <button class="btn btn-sm btn-outline-secondary" @click="reset" title="Restablecer demo"><i class="bi bi-arrow-counterclockwise"></i></button>
        <div class="small text-end"><strong>{{user.name||user.username}}</strong><div class="text-muted">{{user.roleLabel}}</div></div>
        <button class="btn btn-sm btn-outline-secondary" @click="logout" title="Cerrar sesión"><i class="bi bi-box-arrow-right"></i></button>
      </div>
    </header>
    <main class="content"><slot /></main>
  </div>
</div>
</template>
