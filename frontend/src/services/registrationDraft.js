const DRAFT_PREFIX = 'martini_registration_draft_v1_'
const MAX_DRAFT_AGE = 7 * 24 * 60 * 60 * 1000

const fields = {
  client: ['identification_type', 'rut', 'document_number', 'name', 'phone', 'email'],
  equipment: ['equipment_type', 'brand', 'model', 'imei', 'serial_number', 'color', 'observations'],
}

function draftKey(userId, kind) {
  const id = Number(userId)
  if (!Number.isSafeInteger(id) || id <= 0 || !fields[kind]) return null
  return `${DRAFT_PREFIX}${id}_${kind}`
}

export function clearRegistrationDraft(userId, kind, storage = sessionStorage) {
  const key = draftKey(userId, kind)
  if (!key) return
  try {
    storage.removeItem(key)
  } catch {
    // El navegador puede impedir el almacenamiento de esta pestaña.
  }
}

export function loadRegistrationDraft(userId, kind, storage = sessionStorage) {
  const key = draftKey(userId, kind)
  if (!key) return null

  try {
    const stored = storage.getItem(key)
    if (!stored) return null
    const draft = JSON.parse(stored)
    if (
      !draft ||
      !Number.isFinite(draft.savedAt) ||
      draft.savedAt > Date.now() ||
      Date.now() - draft.savedAt > MAX_DRAFT_AGE ||
      !draft.form || typeof draft.form !== 'object'
    ) {
      clearRegistrationDraft(userId, kind, storage)
      return null
    }

    const form = Object.fromEntries(fields[kind].map((field) => [
      field,
      String(draft.form[field] || ''),
    ]))
    return kind === 'equipment'
      ? { clientId: Number(draft.clientId), form }
      : { form }
  } catch {
    return null
  }
}

export function saveRegistrationDraft(userId, kind, draft, storage = sessionStorage) {
  const key = draftKey(userId, kind)
  if (!key) return

  const form = Object.fromEntries(fields[kind].map((field) => [
    field,
    String(draft.form[field] || ''),
  ]))
  const identifyingFields = kind === 'client'
    ? ['rut', 'document_number', 'name', 'phone', 'email']
    : ['brand', 'model', 'imei', 'serial_number', 'color', 'observations']
  if (!identifyingFields.some((field) => form[field].trim())) {
    clearRegistrationDraft(userId, kind, storage)
    return
  }

  try {
    storage.setItem(key, JSON.stringify({
      savedAt: Date.now(),
      clientId: kind === 'equipment' ? Number(draft.clientId) : undefined,
      form,
    }))
  } catch {
    // El formulario permanece editable aunque no se pueda guardar un borrador.
  }
}
