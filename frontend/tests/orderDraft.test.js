import assert from 'node:assert/strict'
import { test } from 'node:test'

import { clearOrderDraft, loadOrderDraft, saveOrderDraft } from '../src/services/orderDraft.js'

function storage() {
  const entries = new Map()
  return {
    getItem: (key) => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, String(value)),
    removeItem: (key) => entries.delete(key),
    entries,
  }
}

const reception = {
  step: 2,
  clientId: '12',
  equipmentId: '43',
  order: {
    reported_issue: 'Carga intermitente',
    initial_observations: 'Rayón inferior',
    received_accessories: 'Funda',
    deposit_amount: '0',
  },
}

test('recupera la recepción luego de volver a iniciar sesión sin mezclar usuarios', () => {
  const tab = storage()
  saveOrderDraft(1, reception, tab)

  assert.deepEqual(loadOrderDraft(1, tab), reception)
  assert.equal(loadOrderDraft(2, tab), null)

  clearOrderDraft(1, tab)
  assert.equal(loadOrderDraft(1, tab), null)
})

test('descarta un borrador vacío o demasiado antiguo', () => {
  const tab = storage()
  saveOrderDraft(1, reception, tab)
  const key = [...tab.entries.keys()][0]
  const old = JSON.parse(tab.getItem(key))
  old.savedAt = Date.now() - 8 * 24 * 60 * 60 * 1000
  tab.setItem(key, JSON.stringify(old))
  assert.equal(loadOrderDraft(1, tab), null)

  saveOrderDraft(1, reception, tab)
  saveOrderDraft(1, {
    ...reception,
    clientId: '',
    equipmentId: '',
    order: Object.fromEntries(Object.keys(reception.order).map((field) => [field, ''])),
  }, tab)
  assert.equal(loadOrderDraft(1, tab), null)
})
