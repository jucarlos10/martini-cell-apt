<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeSession, getCurrentUser } from '../services/auth'

const router = useRouter()
const route = useRoute()
const user = computed(() => getCurrentUser() || {})
const menuOpen = ref(false)

function closeMenu() {
  menuOpen.value = false
}

watch(() => route.fullPath, closeMenu)

function logout() {
  closeMenu()
  closeSession()
  router.push('/login')
}
</script>

<template>
  <div @keydown.esc="closeMenu">
    <button
      v-if="menuOpen"
      type="button"
      class="mobile-nav-backdrop"
      aria-label="Cerrar menú de navegación"
      @click="closeMenu"
    ></button>

    <aside id="mc-sidebar" class="sidebar" :class="{ 'mobile-open': menuOpen }" aria-label="Menú principal">
      <div class="brand d-flex align-items-center justify-content-between gap-2">
        <div>
          <i class="bi bi-tools me-2" aria-hidden="true"></i>
          <span>MARTINI CELL</span>
        </div>
        <button
          type="button"
          class="btn btn-sm btn-outline-light mobile-nav-close"
          aria-label="Cerrar menú"
          @click="closeMenu"
        >
          <i class="bi bi-x-lg" aria-hidden="true"></i>
        </button>
      </div>

      <nav>
        <router-link to="/panel" @click="closeMenu">
          <i class="bi bi-house" aria-hidden="true"></i>
          <span>Panel</span>
        </router-link>
        <router-link to="/ordenes" @click="closeMenu">
          <i class="bi bi-clipboard2-check" aria-hidden="true"></i>
          <span>Órdenes</span>
        </router-link>
        <router-link to="/clientes" @click="closeMenu">
          <i class="bi bi-people" aria-hidden="true"></i>
          <span>Clientes y equipos</span>
        </router-link>
        <router-link v-if="user.role !== 'HELPER'" to="/repuestos" @click="closeMenu">
          <i class="bi bi-box-seam" aria-hidden="true"></i>
          <span>Repuestos</span>
        </router-link>
        <router-link v-if="user.role !== 'HELPER'" to="/garantias" @click="closeMenu">
          <i class="bi bi-shield-check" aria-hidden="true"></i>
          <span>Garantías</span>
        </router-link>
        <router-link v-if="user.role !== 'HELPER'" to="/indicadores" @click="closeMenu">
          <i class="bi bi-bar-chart" aria-hidden="true"></i>
          <span>Indicadores</span>
        </router-link>
        <router-link v-if="user.role === 'ADMIN'" to="/usuarios" @click="closeMenu">
          <i class="bi bi-person-gear" aria-hidden="true"></i>
          <span>Usuarios y roles</span>
        </router-link>
      </nav>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <button
          type="button"
          class="btn btn-sm btn-outline-secondary mobile-nav-toggle"
          aria-label="Abrir menú de navegación"
          aria-controls="mc-sidebar"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          <i class="bi bi-list fs-5" aria-hidden="true"></i>
        </button>

        <div class="d-flex align-items-center gap-3">
          <div class="small text-end">
            <strong>{{ [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username }}</strong>
            <div class="text-muted">{{ user.role_display || user.role }}</div>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-outline-secondary"
            @click="logout"
            title="Cerrar sesión"
            aria-label="Cerrar sesión"
          >
            <i class="bi bi-box-arrow-right" aria-hidden="true"></i>
          </button>
        </div>
      </header>
      <main class="content"><slot /></main>
    </div>
  </div>
</template>

<style scoped>
.mobile-nav-toggle,
.mobile-nav-close { display: none; }
.mobile-nav-backdrop { display: none; }

@media (max-width: 600px) {
  .topbar { justify-content: space-between; }
  .mobile-nav-toggle,
  .mobile-nav-close { display: inline-flex; align-items: center; justify-content: center; }
  .mobile-nav-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    width: 100%;
    height: 100%;
    padding: 0;
    border: 0;
    background: rgb(0 0 0 / 45%);
    z-index: 1000;
  }
  .sidebar {
    display: block;
    width: min(84vw, 290px);
    height: 100dvh;
    min-height: 0;
    overflow-y: auto;
    transform: translateX(-100%);
    visibility: hidden;
    transition: transform .2s ease, visibility .2s ease;
    z-index: 1001;
    box-shadow: 4px 0 18px rgb(0 0 0 / 15%);
  }
  .sidebar.mobile-open { transform: translateX(0); visibility: visible; }
  .sidebar .brand span,
  .sidebar a span { display: inline; }
}
</style>
