import { reactive } from 'vue'

const initialOrders = [
  {
    id: 1, code: 'MC-1047', clientId: 1, client_name: 'Carlos Pérez', device_name: 'iPhone 13',
    status: 'REPAIR', assigned_name: 'Técnico 1', created_at: '2026-09-10T16:20:00', updated_at: '2026-09-12T11:32:00',
    reported_issue: 'Pantalla no enciende', diagnosis: 'Falla en módulo de pantalla', repair_work: 'Reemplazo de pantalla en proceso',
    observations: 'Equipo recibido sin daños externos adicionales.', price: 89000, costs: 42000, margin: 47000,
    difficulty: 'MEDIA', part_availability: 'ALTA', warranty_risk: 'BAJO', estimated_technical_minutes: 160,
    times: { technical: 9300, authorization: 19200, part: 100800, client: 11400, total: 136800 },
    viability: { score: 72, label: 'Favorable', difficulty: 'Media', part: 'Alta', cost: 'Medio', margin: 'Favorable', time: 'Medio', warranty: 'Bajo' },
    history: [
      ['RECEIVED','Ingresado','2026-09-10T16:20:00','Recepción del equipo'],
      ['DIAGNOSIS','Diagnóstico','2026-09-10T18:42:00','Diagnóstico técnico registrado'],
      ['AUTHORIZATION','Autorización','2026-09-11T10:00:00','Autorización registrada por mensajería'],
      ['PART','Repuesto','2026-09-11T15:20:00','Repuesto disponible'],
      ['REPAIR','Reparación','2026-09-12T09:30:00','Inicio de reemplazo de pantalla']
    ]
  },
  {id:2,code:'MC-1046',clientId:2,client_name:'María Soto',device_name:'Notebook HP',status:'DIAGNOSIS',assigned_name:'Técnico 2',created_at:'2026-09-10T12:05:00',updated_at:'2026-09-12T10:15:00',reported_issue:'No inicia sistema',diagnosis:'En evaluación',repair_work:'',observations:'',price:0,costs:0,margin:0,times:{technical:3600,authorization:0,part:0,client:0,total:79200},viability:{score:58,label:'Revisar',difficulty:'Media',part:'Media',cost:'Medio',margin:'Por definir',time:'Medio',warranty:'Medio'},history:[['RECEIVED','Ingresado','2026-09-10T12:05:00','Equipo recibido'],['DIAGNOSIS','Diagnóstico','2026-09-12T10:15:00','Revisión inicial']]},
  {id:3,code:'MC-1045',clientId:3,client_name:'Pedro Díaz',device_name:'Samsung S23',status:'AUTHORIZATION',assigned_name:'Técnico 1',created_at:'2026-09-09T18:20:00',updated_at:'2026-09-11T18:20:00',reported_issue:'Puerto de carga intermitente',diagnosis:'Conector de carga dañado',repair_work:'',observations:'',price:65000,costs:28000,margin:37000,times:{technical:4200,authorization:64800,part:0,client:0,total:129600},viability:{score:78,label:'Favorable',difficulty:'Baja',part:'Alta',cost:'Bajo',margin:'Favorable',time:'Bajo',warranty:'Bajo'},history:[['RECEIVED','Ingresado','2026-09-09T18:20:00','Equipo recibido'],['DIAGNOSIS','Diagnóstico','2026-09-10T11:00:00','Diagnóstico registrado'],['AUTHORIZATION','Autorización','2026-09-11T18:20:00','Pendiente de respuesta']]},
  {id:4,code:'MC-1044',clientId:4,client_name:'Ana Torres',device_name:'iPad Air',status:'TESTING',assigned_name:'Técnico 2',created_at:'2026-09-08T16:10:00',updated_at:'2026-09-11T16:10:00',reported_issue:'Batería se descarga rápido',diagnosis:'Batería degradada',repair_work:'Batería reemplazada',observations:'',price:78000,costs:35000,margin:43000,times:{technical:8400,authorization:7200,part:86400,client:0,total:176400},viability:{score:81,label:'Favorable',difficulty:'Baja',part:'Alta',cost:'Medio',margin:'Favorable',time:'Bajo',warranty:'Bajo'},history:[['RECEIVED','Ingresado','2026-09-08T16:10:00','Equipo recibido'],['DIAGNOSIS','Diagnóstico','2026-09-09T10:00:00','Batería degradada'],['REPAIR','Reparación','2026-09-11T12:00:00','Batería reemplazada'],['TESTING','Pruebas','2026-09-11T16:10:00','Pruebas en curso']]},
  {id:5,code:'MC-1043',clientId:5,client_name:'Luis Rojas',device_name:'Xiaomi Redmi',status:'READY',assigned_name:'Técnico 1',created_at:'2026-09-07T14:32:00',updated_at:'2026-09-11T14:32:00',reported_issue:'Pantalla quebrada',diagnosis:'Display dañado',repair_work:'Cambio de módulo',observations:'',price:70000,costs:31000,margin:39000,times:{technical:7200,authorization:3600,part:86400,client:14400,total:180000},viability:{score:80,label:'Favorable',difficulty:'Baja',part:'Alta',cost:'Medio',margin:'Favorable',time:'Bajo',warranty:'Bajo'},history:[['RECEIVED','Ingresado','2026-09-07T14:32:00','Equipo recibido'],['REPAIR','Reparación','2026-09-10T10:20:00','Cambio de módulo'],['READY','Listo','2026-09-11T14:32:00','Disponible para retiro']]}
]

const defaultState = {
  users: [
    {id:1,username:'admin',name:'Juan Valencia',role:'ADMIN',roleLabel:'Administrador',active:true},
    {id:2,username:'tecnico',name:'Oscar Contreras',role:'TECH',roleLabel:'Técnico',active:true},
    {id:3,username:'ayudante',name:'Rafael Muñoz',role:'HELPER',roleLabel:'Ayudante',active:true}
  ],
  clients: [
    {id:1,name:'Carlos Pérez',phone:'+56 9 1234 5678',email:'carlos@example.com',devices:[{id:1,type:'Celular',brand:'Apple',model:'iPhone 13',identifier:'IMEI ****1234'}]},
    {id:2,name:'María Soto',phone:'+56 9 2345 6789',email:'maria@example.com',devices:[{id:2,type:'Computador',brand:'HP',model:'Notebook 14',identifier:'SERIE ****3344'}]},
    {id:3,name:'Pedro Díaz',phone:'+56 9 3456 7890',email:'pedro@example.com',devices:[{id:3,type:'Celular',brand:'Samsung',model:'S23',identifier:'IMEI ****8080'}]},
    {id:4,name:'Ana Torres',phone:'+56 9 4567 8901',email:'ana@example.com',devices:[{id:4,type:'Tablet',brand:'Apple',model:'iPad Air',identifier:'SERIE ****7711'}]},
    {id:5,name:'Luis Rojas',phone:'+56 9 5678 9012',email:'luis@example.com',devices:[{id:5,type:'Celular',brand:'Xiaomi',model:'Redmi Note',identifier:'IMEI ****2200'}]}
  ],
  parts: [
    {id:1,name:'Pantalla iPhone 13',supplier:'Proveedor A',cost:42000,stock:3},
    {id:2,name:'Batería iPhone 13',supplier:'Proveedor A',cost:28000,stock:6},
    {id:3,name:'Pantalla Samsung S23',supplier:'Proveedor B',cost:55000,stock:2},
    {id:4,name:'Conector de carga',supplier:'Proveedor C',cost:12000,stock:8},
    {id:5,name:'Cámara trasera',supplier:'Proveedor B',cost:35000,stock:1}
  ],
  suppliers: [
    {id:1,name:'Proveedor A',contact:'Ventas',phone:'+56 9 1111 1111',email:'ventas@proveedora.cl'},
    {id:2,name:'Proveedor B',contact:'Soporte',phone:'+56 9 2222 2222',email:'contacto@proveedorb.cl'},
    {id:3,name:'Proveedor C',contact:'Comercial',phone:'+56 9 3333 3333',email:'ventas@proveedorc.cl'}
  ],
  warranties: [
    {id:1,order:'MC-1039',state:'Vigente',dates:'01/09/2026 → 01/12/2026',part:'Pantalla Samsung',supplier:'Proveedor B',conditions:'90 días por funcionamiento del repuesto.'},
    {id:2,order:'MC-1032',state:'Vencida',dates:'12/05/2026 → 12/08/2026',part:'Batería',supplier:'Proveedor A',conditions:'90 días por defecto de fabricación.'}
  ],
  orders: initialOrders
}

function clone(v){ return JSON.parse(JSON.stringify(v)) }
function loadState(){
  try {
    const saved = localStorage.getItem('martini_demo_data')
    return saved ? {...clone(defaultState), ...JSON.parse(saved)} : clone(defaultState)
  } catch { return clone(defaultState) }
}

export const store = reactive(loadState())
export const statusLabels = {RECEIVED:'Ingresado',DIAGNOSIS:'Diagnóstico',AUTHORIZATION:'Autorización',PART:'Repuesto',REPAIR:'Reparación',TESTING:'Pruebas',READY:'Listo',DELIVERED:'Entregado',CLOSED:'Cerrado',REJECTED:'No reparado/rechazado'}
export const statusOrder = ['RECEIVED','DIAGNOSIS','AUTHORIZATION','PART','REPAIR','TESTING','READY','DELIVERED','CLOSED']

export function persist(){
  localStorage.setItem('martini_demo_data', JSON.stringify({orders:store.orders,clients:store.clients,parts:store.parts,suppliers:store.suppliers,warranties:store.warranties,users:store.users}))
}
export function resetDemo(){
  const fresh = clone(defaultState)
  Object.keys(fresh).forEach(k => store[k] = fresh[k])
  persist()
}
export function getOrder(idOrCode){
  return store.orders.find(o => String(o.id) === String(idOrCode) || o.code.toLowerCase() === String(idOrCode).toLowerCase())
}
export function createOrder(payload){
  const id = Math.max(0,...store.orders.map(o=>o.id))+1
  const code = `MC-${1047 + id}`
  const now = new Date().toISOString()
  const o = {
    id, code, clientId: payload.clientId, client_name: payload.client_name, device_name: payload.device_name,
    status:'RECEIVED', assigned_name:payload.assigned_name||'Sin asignar', created_at:now, updated_at:now,
    reported_issue:payload.reported_issue, diagnosis:'', repair_work:'', observations:payload.observations||'', price:0,costs:0,margin:0,
    times:{technical:0,authorization:0,part:0,client:0,total:0},
    viability:{score:0,label:'Pendiente',difficulty:'Por definir',part:'Por definir',cost:'Por definir',margin:'Por definir',time:'Por definir',warranty:'Por definir'},
    history:[['RECEIVED','Ingresado',now,'Orden creada desde el prototipo frontend']]
  }
  store.orders.unshift(o); persist(); return o
}
export function updateOrderStatus(order, status, note=''){
  order.status=status; order.updated_at=new Date().toISOString(); order.history.push([status,statusLabels[status],order.updated_at,note||'Estado actualizado']); persist()
}
