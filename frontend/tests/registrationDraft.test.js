import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  clearRegistrationDraft,
  loadRegistrationDraft,
  saveRegistrationDraft,
} from '../src/services/registrationDraft.js'

function storage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
    values,
  }
}

test('recupera cliente y equipo para el mismo usuario y cliente después de una pausa', () => {
  const tab = storage()
  const client = {
    identification_type: 'RUT', rut: '12.345.678-5', name: 'Ana',
    phone: '+56912345678', email: '', document_number: '',
  }
  const equipment = {
    equipment_type: 'CELULAR', brand: 'Samsung', model: 'A14',
    imei: '', serial_number: '', color: '', observations: 'Pantalla con rayas',
  }
  saveRegistrationDraft(1, 'client', { form: client }, tab)
  saveRegistrationDraft(1, 'equipment', { clientId: 42, form: equipment }, tab)

  assert.deepEqual(loadRegistrationDraft(1, 'client', tab), { form: client })
  assert.deepEqual(loadRegistrationDraft(1, 'equipment', tab), { clientId: 42, form: equipment })
  assert.equal(loadRegistrationDraft(2, 'client', tab), null)
  assert.equal(loadRegistrationDraft(1, 'other', tab), null)

  clearRegistrationDraft(1, 'client', tab)
  assert.equal(loadRegistrationDraft(1, 'client', tab), null)
  assert.deepEqual(loadRegistrationDraft(1, 'equipment', tab), { clientId: 42, form: equipment })
})

test('descarta formularios vacíos y borradores antiguos', () => {
  const tab = storage()
  saveRegistrationDraft(1, 'client', { form: { identification_type: 'RUT' } }, tab)
  assert.equal(loadRegistrationDraft(1, 'client', tab), null)

  saveRegistrationDraft(1, 'client', { form: { name: 'Ana' } }, tab)
  const key = [...tab.values.keys()][0]
  const draft = JSON.parse(tab.getItem(key))
  draft.savedAt = Date.now() - 8 * 24 * 60 * 60 * 1000
  tab.setItem(key, JSON.stringify(draft))
  assert.equal(loadRegistrationDraft(1, 'client', tab), null)
})
