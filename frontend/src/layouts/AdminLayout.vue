<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { closeSession, getCurrentUser } from '../services/auth'

const router = useRouter()

const user = computed(() => getCurrentUser() || {})

function logout() {
  closeSession()
  router.push('/login')
}
</script>

<template>
  <div>
    <aside class="sidebar">
      <div class="brand">
        <i class="bi bi-tools me-2"></i>
        <span>MARTINI CELL</span>
      </div>

      <nav>
        <router-link to="/panel">
          <i class="bi bi-house"></i>
          <span>Panel</span>
        </router-link>

        <router-link to="/ordenes">
          <i class="bi bi-clipboard2-check"></i>
          <span>Órdenes</span>
        </router-link>

        <router-link to="/clientes">
          <i class="bi bi-people"></i>
          <span>Clientes y equipos</span>
        </router-link>

        <router-link
          v-if="user.role !== 'HELPER'"
          to="/repuestos"
        >
          <i class="bi bi-box-seam"></i>
          <span>Repuestos</span>
        </router-link>

        <router-link
          v-if="user.role !== 'HELPER'"
          to="/garantias"
        >
          <i class="bi bi-shield-check"></i>
          <span>Garantías</span>
        </router-link>

        <router-link
          v-if="user.role !== 'HELPER'"
          to="/indicadores"
        >
          <i class="bi bi-bar-chart"></i>
          <span>Indicadores</span>
        </router-link>

        <router-link
          v-if="user.role === 'ADMIN'"
          to="/usuarios"
        >
          <i class="bi bi-person-gear"></i>
          <span>Usuarios y roles</span>
        </router-link>
      </nav>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <div class="d-flex align-items-center gap-3">
          <div class="small text-end">
            <strong>
              {{
                [user.first_name, user.last_name]
                  .filter(Boolean)
                  .join(' ') || user.username
              }}
            </strong>

            <div class="text-muted">
              {{ user.role_display || user.role }}
            </div>
          </div>

          <button
            class="btn btn-sm btn-outline-secondary"
            @click="logout"
            title="Cerrar sesión"
          >
            <i class="bi bi-box-arrow-right"></i>
          </button>
        </div>
      </header>

      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>