import { createRouter, createWebHistory } from 'vue-router'
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

const routes=[
  {path:'/',redirect:'/panel'},
  {path:'/login',component:Login,meta:{public:true}},
  {path:'/consulta',component:PublicTracking,meta:{public:true}},
  {path:'/panel',component:Dashboard},
  {path:'/ordenes',component:Orders},
  {path:'/ordenes/nueva',component:OrderCreate},
  {path:'/ordenes/:id',component:OrderDetail},
  {path:'/clientes',component:Clients},
  {path:'/repuestos',component:Parts,meta:{technical:true}},
  {path:'/garantias',component:Warranties,meta:{technical:true}},
  {path:'/indicadores',component:Indicators,meta:{technical:true}},
  {path:'/usuarios',component:Users,meta:{admin:true}}
]

const router=createRouter({history:createWebHistory(),routes})
router.beforeEach(to=>{
  if(!to.meta.public && !localStorage.getItem('martini_demo_session')) return '/login'
  const user=JSON.parse(localStorage.getItem('martini_demo_user')||'{}')
  if(to.meta.admin && user.role!=='ADMIN') return '/panel'
  if(to.meta.technical && !['ADMIN','TECH'].includes(user.role)) return '/panel'
})
export default router
