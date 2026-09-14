<script setup>
import { ref } from 'vue'; import { useRouter } from 'vue-router'; import { store } from '../mockStore'
const username=ref('admin'),password=ref('Admin123!'),error=ref(''),router=useRouter()
const creds={admin:'Admin123!',tecnico:'Tecnico123!',ayudante:'Ayudante123!'}
function login(){
  const u=store.users.find(x=>x.username===username.value && x.active)
  if(!u || creds[username.value]!==password.value){error.value='Credenciales demo incorrectas.';return}
  localStorage.setItem('martini_demo_session','1');localStorage.setItem('martini_demo_user',JSON.stringify(u));router.push('/panel')
}
function fill(u,p){username.value=u;password.value=p;error.value=''}
</script>
<template>
<div class="login-wrap">
  <section class="login-panel">
    <form class="login-form" @submit.prevent="login">
      <div class="mb-4"><div class="fs-4 fw-bold" style="color:var(--mc-navy)"><i class="bi bi-tools me-2"></i>MARTINI CELL</div><div class="mc-muted">Gestión de servicios técnicos</div></div>
      <div class="mock-note mb-3 text-center"><strong>Versión frontend!!</strong></div>
      <div v-if="error" class="alert alert-danger py-2">{{error}}</div>
      <label class="form-label">Usuario</label><input v-model="username" class="form-control mb-3" required>
      <label class="form-label">Contraseña</label><input v-model="password" type="password" class="form-control mb-3" required>
      <button class="btn btn-primary w-100">Iniciar sesión</button>
      <div class="text-center my-3 text-muted">o</div>
      <router-link to="/consulta" class="btn btn-outline-primary w-100"><i class="bi bi-search me-2"></i>Consultar reparación</router-link>
      <div class="small text-muted mt-4">Accesos demo:</div>
      <div class="d-flex flex-wrap gap-2 mt-2">
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="fill('admin','Admin123!')">Administrador</button>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="fill('tecnico','Tecnico123!')">Técnico</button>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="fill('ayudante','Ayudante123!')">Ayudante</button>
      </div>
    </form>
  </section>
  <section class="login-hero"><h2 class="display-6 fw-bold">Reparamos.<br>Conectamos.<br>Acompañamos.</h2><p class="opacity-75">Prototipo navegable para validación UX/UI.</p></section>
</div>
</template>
