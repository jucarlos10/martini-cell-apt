
<script setup>
import { computed, onMounted, ref } from 'vue'

import AdminLayout from '../layouts/AdminLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { authenticatedFetch, getCurrentUser } from '../services/auth'

const currentUser = getCurrentUser()
const canManage = ['ADMIN', 'TECH'].includes(currentUser?.role)

const tab = ref('parts')

const suppliers = ref([])
const parts = ref([])

// Búsqueda local entre los proveedores recibidos desde Django.
const supplierSearch = ref('')
const filteredSuppliers = computed(() => {
  const term = supplierSearch.value.trim().toLowerCase()

  if (!term) return suppliers.value

  return suppliers.value.filter((supplier) =>
    [
      supplier.name,
      supplier.contact_name,
      supplier.phone,
      supplier.email,
    ]
      .join(' ')
      .toLowerCase()
      .includes(term)
  )
})

const loading = ref(true)
const saving = ref(false)

const error = ref('')
const formError = ref('')
const success = ref('')

const editingSupplierId = ref(null)
const editingPartId = ref(null)

const emptySupplierForm = () => ({
  name: '',
  contact_name: '',
  phone: '',
  email: '',
  is_active: true,
})

const emptyPartForm = () => ({
  name: '',
  description: '',
  supplier: '',
  unit_cost: '0.00',
  stock: 0,
  is_active: true,
})

const supplierForm = ref(emptySupplierForm())
const partForm = ref(emptyPartForm())

const hasActiveSuppliers = computed(() =>
  suppliers.value.some((supplier) => supplier.is_active)
)

function formatMoney(value) {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(Number(value) || 0)
}

function formatApiError(data, fallback) {
  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (!data || typeof data !== 'object') {
    return fallback
  }

  return Object.entries(data)
    .map(([field, messages]) => {
      const message = Array.isArray(messages)
        ? messages.join(' ')
        : String(messages)

      return `${field}: ${message}`
    })
    .join(' ') || fallback
}

function asList(data) {
  return Array.isArray(data)
    ? data
    : (data?.results || [])
}

async function loadInventory() {
  loading.value = true
  error.value = ''

  try {
    const [supplierResponse, partResponse] = await Promise.all([
      authenticatedFetch('/api/inventory/suppliers/'),
      authenticatedFetch('/api/inventory/parts/'),
    ])

    const supplierData = await supplierResponse.json().catch(() => null)
    const partData = await partResponse.json().catch(() => null)

    if (!supplierResponse.ok) {
      throw new Error(
        formatApiError(
          supplierData,
          'No fue posible cargar los proveedores.'
        )
      )
    }

    if (!partResponse.ok) {
      throw new Error(
        formatApiError(
          partData,
          'No fue posible cargar los repuestos.'
        )
      )
    }

    suppliers.value = asList(supplierData)
    parts.value = asList(partData)

  } catch (err) {
    error.value = err?.message || 'Error al cargar el inventario.'

  } finally {
    loading.value = false
  }
}

function changeTab(nextTab) {
  tab.value = nextTab
  formError.value = ''
  success.value = ''
}

function resetSupplierForm() {
  editingSupplierId.value = null
  supplierForm.value = emptySupplierForm()
  formError.value = ''
}

function editSupplier(supplier) {
  editingSupplierId.value = supplier.id

  supplierForm.value = {
    name: supplier.name || '',
    contact_name: supplier.contact_name || '',
    phone: supplier.phone || '',
    email: supplier.email || '',
    is_active: supplier.is_active,
  }

  formError.value = ''
  success.value = ''
}

async function saveSupplier() {
  if (!canManage || saving.value) return

  formError.value = ''
  success.value = ''

  if (!supplierForm.value.name.trim()) {
    formError.value = 'Ingresa el nombre del proveedor.'
    return
  }

  const isEditing = editingSupplierId.value !== null

  const url = isEditing
    ? `/api/inventory/suppliers/${editingSupplierId.value}/`
    : '/api/inventory/suppliers/'

  const payload = {
    name: supplierForm.value.name.trim(),
    contact_name: supplierForm.value.contact_name.trim(),
    phone: supplierForm.value.phone.trim(),
    email: supplierForm.value.email.trim(),
    is_active: supplierForm.value.is_active,
  }

  saving.value = true

  try {
    const response = await authenticatedFetch(url, {
      method: isEditing ? 'PATCH' : 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(
        formatApiError(data, 'No fue posible guardar el proveedor.')
      )
    }

    resetSupplierForm()
    await loadInventory()

    if (!error.value) {
      success.value = isEditing
        ? 'Proveedor actualizado correctamente.'
        : 'Proveedor registrado correctamente.'
    }

  } catch (err) {
    formError.value =
      err?.message || 'Error al guardar el proveedor.'

  } finally {
    saving.value = false
  }
}

function resetPartForm() {
  editingPartId.value = null
  partForm.value = emptyPartForm()
  formError.value = ''
}

function editPart(part) {
  editingPartId.value = part.id

  partForm.value = {
    name: part.name || '',
    description: part.description || '',
    supplier: part.supplier,
    unit_cost: String(part.unit_cost ?? '0.00'),
    stock: part.stock,
    is_active: part.is_active,
  }

  formError.value = ''
  success.value = ''
}

async function savePart() {
  if (!canManage || saving.value) return

  formError.value = ''
  success.value = ''

  const name = partForm.value.name.trim()
  const supplierId = Number(partForm.value.supplier)
  const unitCost = String(partForm.value.unit_cost).trim()
  const stock = Number(partForm.value.stock)

  if (!name) {
    formError.value = 'Ingresa el nombre del repuesto.'
    return
  }

  if (!Number.isInteger(supplierId) || supplierId <= 0) {
    formError.value = 'Selecciona un proveedor.'
    return
  }

  if (!/^\d+(\.\d{1,2})?$/.test(unitCost)) {
    formError.value =
      'Ingresa un costo válido, con un máximo de dos decimales.'
    return
  }

  if (!Number.isInteger(stock) || stock < 0) {
    formError.value = 'El stock debe ser un número entero igual o mayor que cero.'
    return
  }

  const isEditing = editingPartId.value !== null

  const url = isEditing
    ? `/api/inventory/parts/${editingPartId.value}/`
    : '/api/inventory/parts/'

  const payload = {
    name,
    description: partForm.value.description.trim(),
    supplier: supplierId,
    unit_cost: unitCost,
    stock,
    is_active: partForm.value.is_active,
  }

  saving.value = true

  try {
    const response = await authenticatedFetch(url, {
      method: isEditing ? 'PATCH' : 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(
        formatApiError(data, 'No fue posible guardar el repuesto.')
      )
    }

    resetPartForm()
    await loadInventory()

    if (!error.value) {
      success.value = isEditing
        ? 'Repuesto actualizado correctamente.'
        : 'Repuesto registrado correctamente.'
    }

  } catch (err) {
    formError.value =
      err?.message || 'Error al guardar el repuesto.'

  } finally {
    saving.value = false
  }
}

onMounted(loadInventory)
</script>

<template>
  <AdminLayout>
    <PageHeader>
      Repuestos y proveedores

      <template #subtitle>
        Catálogo conectado a la base de datos de Martini Cell.
      </template>

      <template #actions>
        <button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="loading || saving"
          @click="loadInventory"
        >
          <i class="bi bi-arrow-clockwise me-1"></i>
          Actualizar
        </button>
      </template>
    </PageHeader>

    <div v-if="error" class="alert alert-danger" role="alert">
      {{ error }}

      <button
        type="button"
        class="btn btn-sm btn-outline-danger ms-2"
        :disabled="loading"
        @click="loadInventory"
      >
        Reintentar
      </button>
    </div>

    <div v-if="success" class="alert alert-success" role="status">
      {{ success }}
    </div>

    <div class="section-tabs mb-3">
      <button
        type="button"
        :class="{ active: tab === 'parts' }"
        :aria-pressed="tab === 'parts'"
        @click="changeTab('parts')"
      >
        Repuestos
      </button>

      <button
        type="button"
        :class="{ active: tab === 'suppliers' }"
        :aria-pressed="tab === 'suppliers'"
        @click="changeTab('suppliers')"
      >
        Proveedores
      </button>
    </div>

    <!-- REPUESTOS -->
    <section v-if="tab === 'parts'" class="row g-3">
      <div class="col-lg-8">
        <div class="mc-card p-3">
          <h5>Catálogo de repuestos</h5>

          <div v-if="loading" class="text-center py-4">
            <div class="spinner-border text-primary mb-2" role="status"></div>
            <div class="text-muted">Cargando repuestos...</div>
          </div>

          <div v-else class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Repuesto</th>
                  <th>Proveedor</th>
                  <th>Costo ref.</th>
                  <th>Stock</th>
                  <th>Estado</th>
                  <th v-if="canManage">Acción</th>
                </tr>
              </thead>

              <tbody>
                <tr v-if="parts.length === 0">
                  <td
                    :colspan="canManage ? 6 : 5"
                    class="text-center text-muted py-4"
                  >
                    No hay repuestos registrados.
                  </td>
                </tr>

                <tr v-for="item in parts" :key="item.id">
                  <td>
                    <strong>{{ item.name }}</strong>
                    <div v-if="item.description" class="small text-muted">
                      {{ item.description }}
                    </div>
                  </td>

                  <td>{{ item.supplier_name }}</td>
                  <td>{{ formatMoney(item.unit_cost) }}</td>
                  <td>{{ item.stock }}</td>

                  <td>
                    <span
                      class="badge"
                      :class="item.is_active ? 'bg-success' : 'bg-secondary'"
                    >
                      {{ item.is_active ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>

                  <td v-if="canManage">
                    <button
                      type="button"
                      class="btn btn-sm btn-outline-primary"
                      :disabled="saving"
                      @click="editPart(item)"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="canManage" class="col-lg-4">
        <div class="mc-card p-3">
          <h5>
            {{ editingPartId !== null ? 'Editar repuesto' : 'Nuevo repuesto' }}
          </h5>

          <div
            v-if="!hasActiveSuppliers"
            class="alert alert-info small"
          >
            Primero registra un proveedor activo en la pestaña
            «Proveedores».
          </div>

          <div v-if="formError" class="alert alert-danger" role="alert">
            {{ formError }}
          </div>

          <form @submit.prevent="savePart">
            <label for="part-name" class="form-label">Nombre del repuesto</label>
            <input
              id="part-name"
              v-model.trim="partForm.name"
              class="form-control mb-3"
              maxlength="150"
              required
              :disabled="saving"
            >

            <label for="part-description" class="form-label">
              Descripción
            </label>
            <textarea
              id="part-description"
              v-model="partForm.description"
              class="form-control mb-3"
              rows="2"
              :disabled="saving"
            ></textarea>

            <label for="part-supplier" class="form-label">
              Proveedor
            </label>
            <select
              id="part-supplier"
              v-model.number="partForm.supplier"
              class="form-select mb-3"
              required
              :disabled="saving"
            >
              <option value="">Seleccionar proveedor...</option>

              <option
                v-for="item in suppliers"
                :key="item.id"
                :value="item.id"
                :disabled="!item.is_active && item.id !== partForm.supplier"
              >
                {{ item.name }}{{ item.is_active ? '' : ' (inactivo)' }}
              </option>
            </select>

            <label for="part-cost" class="form-label">
              Costo unitario referencial
            </label>
            <input
              id="part-cost"
              v-model="partForm.unit_cost"
              type="number"
              min="0"
              step="0.01"
              class="form-control mb-3"
              required
              :disabled="saving"
            >

            <label for="part-stock" class="form-label">
              Stock disponible
            </label>
            <input
              id="part-stock"
              v-model.number="partForm.stock"
              type="number"
              min="0"
              step="1"
              class="form-control mb-3"
              required
              :disabled="saving"
            >

            <div class="form-check mb-3">
              <input
                id="part-active"
                v-model="partForm.is_active"
                type="checkbox"
                class="form-check-input"
                :disabled="saving"
              >
              <label for="part-active" class="form-check-label">
                Repuesto activo
              </label>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="saving || !hasActiveSuppliers"
              >
                {{ saving ? 'Guardando...' : (editingPartId !== null ? 'Guardar cambios' : 'Registrar repuesto') }}
              </button>

              <button
                v-if="editingPartId !== null"
                type="button"
                class="btn btn-outline-secondary"
                :disabled="saving"
                @click="resetPartForm"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>

    <!-- PROVEEDORES -->
    <section v-else class="row g-3">
      <div class="col-lg-8">
        <div class="mc-card p-3">
          <h5>Proveedores registrados</h5>

          <div class="mb-3">
            <label for="supplier-search" class="form-label">
              Buscar proveedor
            </label>
            <input
              id="supplier-search"
              v-model="supplierSearch"
              type="search"
              class="form-control"
              placeholder="Buscar por nombre, contacto, teléfono o correo..."
              aria-label="Buscar proveedores"
            >
          </div>

          <div v-if="loading" class="text-center py-4">
            <div class="spinner-border text-primary mb-2" role="status"></div>
            <div class="text-muted">Cargando proveedores...</div>
          </div>

          <div v-else class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Proveedor</th>
                  <th>Contacto</th>
                  <th>Teléfono</th>
                  <th>Correo</th>
                  <th>Estado</th>
                  <th v-if="canManage">Acción</th>
                </tr>
              </thead>

              <tbody>
                <tr v-if="filteredSuppliers.length === 0">
                  <td
                    :colspan="canManage ? 6 : 5"
                    class="text-center text-muted py-4"
                  >
                    {{
                      suppliers.length === 0
                        ? 'No hay proveedores registrados.'
                        : 'No se encontraron proveedores con esa búsqueda.'
                    }}
                  </td>
                </tr>

                <tr v-for="item in filteredSuppliers" :key="item.id">
                  <td><strong>{{ item.name }}</strong></td>
                  <td>{{ item.contact_name || '—' }}</td>
                  <td>{{ item.phone || '—' }}</td>
                  <td>{{ item.email || '—' }}</td>

                  <td>
                    <span
                      class="badge"
                      :class="item.is_active ? 'bg-success' : 'bg-secondary'"
                    >
                      {{ item.is_active ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>

                  <td v-if="canManage">
                    <button
                      type="button"
                      class="btn btn-sm btn-outline-primary"
                      :disabled="saving"
                      @click="editSupplier(item)"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="canManage" class="col-lg-4">
        <div class="mc-card p-3">
          <h5>
            {{ editingSupplierId !== null ? 'Editar proveedor' : 'Nuevo proveedor' }}
          </h5>

          <div v-if="formError" class="alert alert-danger" role="alert">
            {{ formError }}
          </div>

          <form @submit.prevent="saveSupplier">
            <label for="supplier-name" class="form-label">
              Nombre del proveedor
            </label>
            <input
              id="supplier-name"
              v-model.trim="supplierForm.name"
              class="form-control mb-3"
              maxlength="150"
              required
              :disabled="saving"
            >

            <label for="supplier-contact" class="form-label">
              Persona de contacto
            </label>
            <input
              id="supplier-contact"
              v-model.trim="supplierForm.contact_name"
              class="form-control mb-3"
              maxlength="150"
              :disabled="saving"
            >

            <label for="supplier-phone" class="form-label">
              Teléfono
            </label>
            <input
              id="supplier-phone"
              v-model.trim="supplierForm.phone"
              type="tel"
              class="form-control mb-3"
              maxlength="30"
              :disabled="saving"
            >

            <label for="supplier-email" class="form-label">
              Correo electrónico
            </label>
            <input
              id="supplier-email"
              v-model.trim="supplierForm.email"
              type="email"
              class="form-control mb-3"
              :disabled="saving"
            >

            <div class="form-check mb-3">
              <input
                id="supplier-active"
                v-model="supplierForm.is_active"
                type="checkbox"
                class="form-check-input"
                :disabled="saving"
              >
              <label for="supplier-active" class="form-check-label">
                Proveedor activo
              </label>
            </div>

            <div class="d-flex gap-2 flex-wrap">
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="saving"
              >
                {{ saving ? 'Guardando...' : (editingSupplierId !== null ? 'Guardar cambios' : 'Registrar proveedor') }}
              </button>

              <button
                v-if="editingSupplierId !== null"
                type="button"
                class="btn btn-outline-secondary"
                :disabled="saving"
                @click="resetSupplierForm"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  </AdminLayout>
</template>