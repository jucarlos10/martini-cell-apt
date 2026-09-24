
import { createRouter, createWebHistory } from 'vue-router'

import { getAuthenticatedUser, closeSession } from './services/auth'

import Login from './views/LoginView.vue'
import Dashboard from './views/DashboardView.vue'
import Orders from './views/OrdersView.vue'
import OrderCreate from './views/OrderCreateView.vue'
import OrderDetail from './views/OrderDetailView.vue'
import Clients from './views/ClientsView.vue'
import Parts from './views/PartsView.vue'
import Warranties from './views/WarrantiesView.vue'
import Indicators from './views/IndicatorsView.vue'
import Users from './views/UsersView.vue'
import PublicTracking from './views/PublicTrackingView.vue'

const routes = [
  { path: '/', redirect: '/panel' },

  { path: '/login', component: Login, meta: { public: true } },
  { path: '/consulta', component: PublicTracking, meta: { public: true } },

  { path: '/panel', component: Dashboard },
  { path: '/ordenes', component: Orders },
  { path: '/ordenes/nueva', component: OrderCreate },
  { path: '/ordenes/:id', component: OrderDetail },
  { path: '/clientes', component: Clients },

  {
    path: '/repuestos',
    component: Parts,
    meta: { technical: true },
  },
  {
    path: '/garantias',
    component: Warranties,
    meta: { technical: true },
  },
  {
    path: '/indicadores',
    component: Indicators,
    meta: { technical: true },
  },
  {
    path: '/usuarios',
    component: Users,
    meta: { admin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  // El login y la consulta pública no requieren autenticación.
  if (to.meta.public) {
    return true
  }

  let user

  try {
    // Verifica la sesión con Django y renueva el token
    // cuando corresponde.
    user = await getAuthenticatedUser()
  } catch {
    closeSession()
    return '/login'
  }

  if (!user) {
    return '/login'
  }

  // Rutas reservadas para administradores.
  if (to.meta.admin && user.role !== 'ADMIN') {
    return '/panel'
  }

  // Rutas reservadas para administradores y técnicos.
  if (
    to.meta.technical &&
    !['ADMIN', 'TECH'].includes(user.role)
  ) {
    return '/panel'
  }

  return true
})

export default router