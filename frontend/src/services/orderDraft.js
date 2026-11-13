const DRAFT_PREFIX = 'martini_order_draft_v1_'
const MAX_DRAFT_AGE = 7 * 24 * 60 * 60 * 1000

function draftKey(userId) {
  const id = Number(userId)
  return Number.isSafeInteger(id) && id > 0 ? `${DRAFT_PREFIX}${id}` : null
}

export function loadOrderDraft(userId, storage = sessionStorage) {
  const key = draftKey(userId)
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
      !draft.order || typeof draft.order !== 'object'
    ) {
      storage.removeItem(key)
      return null
    }

    return {
      step: [1, 2, 3].includes(draft.step) ? draft.step : 1,
      clientId: String(draft.clientId || ''),
      equipmentId: String(draft.equipmentId || ''),
      order: {
        reported_issue: String(draft.order.reported_issue || ''),
        initial_observations: String(draft.order.initial_observations || ''),
        received_accessories: String(draft.order.received_accessories || ''),
        deposit_amount: String(draft.order.deposit_amount || ''),
      },
    }
  } catch {
    return null
  }
}

export function clearOrderDraft(userId, storage = sessionStorage) {
  const key = draftKey(userId)
  if (!key) return
  try {
    storage.removeItem(key)
  } catch {
    // Puede estar deshabilitado el almacenamiento de esta pestaña.
  }
}

export function saveOrderDraft(userId, draft, storage = sessionStorage) {
  const key = draftKey(userId)
  if (!key) return

  const order = draft.order
  if (
    !draft.clientId && !draft.equipmentId &&
    !Object.values(order).some((value) => String(value || '').trim())
  ) {
    clearOrderDraft(userId, storage)
    return
  }

  try {
    storage.setItem(key, JSON.stringify({
      savedAt: Date.now(),
      step: draft.step,
      clientId: draft.clientId,
      equipmentId: draft.equipmentId,
      order,
    }))
  } catch {
    // La recepción sigue disponible en pantalla si el almacenamiento falla.
  }
}
