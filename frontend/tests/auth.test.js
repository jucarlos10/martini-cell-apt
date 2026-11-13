import assert from 'node:assert/strict'
import { afterEach, beforeEach, test } from 'node:test'

import {
  authenticatedFetch,
  closeSession,
  getAuthenticatedUser,
  getCurrentUser,
  startSession,
} from '../src/services/auth.js'

const ACCESS_KEY = 'martini_access_token'
const REFRESH_KEY = 'martini_refresh_token'
const USER_KEY = 'martini_auth_user'
const originalFetch = globalThis.fetch
const originalSessionStorage = globalThis.sessionStorage

function response(status, data) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => data,
  }
}

function deferred() {
  let resolve
  const promise = new Promise((done) => { resolve = done })
  return { promise, resolve }
}

beforeEach(() => {
  const entries = new Map()
  globalThis.sessionStorage = {
    getItem: (key) => entries.get(key) ?? null,
    setItem: (key, value) => entries.set(key, String(value)),
    removeItem: (key) => entries.delete(key),
  }
  closeSession()
})

afterEach(() => {
  closeSession()
  globalThis.fetch = originalFetch
  globalThis.sessionStorage = originalSessionStorage
})

test('las solicitudes paralelas comparten la verificación del usuario', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'vigente')
  const profile = deferred()
  const calls = []
  globalThis.fetch = (url, options) => {
    calls.push({ url, authorization: options?.headers?.get?.('Authorization') ?? options?.headers?.Authorization })
    if (url === '/api/auth/me/') return profile.promise
    return Promise.resolve(response(200, []))
  }

  const requests = [
    authenticatedFetch('/api/orders/'),
    authenticatedFetch('/api/clients/'),
    authenticatedFetch('/api/devices/'),
  ]
  assert.equal(calls.filter(({ url }) => url === '/api/auth/me/').length, 1)

  profile.resolve(response(200, { id: 1, role: 'ADMIN' }))
  await Promise.all(requests)

  assert.equal(calls.length, 4)
  assert.deepEqual(calls.slice(1).map(({ authorization }) => authorization), [
    'Bearer vigente', 'Bearer vigente', 'Bearer vigente',
  ])
})

test('las solicitudes paralelas renuevan el token una sola vez', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'vencido')
  sessionStorage.setItem(REFRESH_KEY, 'renovable')
  const calls = []
  globalThis.fetch = async (url, options) => {
    calls.push(url)
    if (url === '/api/auth/me/') {
      return options.headers.Authorization === 'Bearer vencido'
        ? response(401, {})
        : response(200, { id: 1, role: 'TECH' })
    }
    if (url === '/api/auth/refresh/') return response(200, { access: 'nuevo' })
    return response(200, [])
  }

  await Promise.all([
    authenticatedFetch('/api/orders/'),
    authenticatedFetch('/api/clients/'),
  ])

  assert.equal(calls.filter((url) => url === '/api/auth/refresh/').length, 1)
  assert.equal(calls.filter((url) => url === '/api/auth/me/').length, 2)
  assert.equal(sessionStorage.getItem(ACCESS_KEY), 'nuevo')
})

test('una respuesta tardía no restaura la sesión tras cerrar sesión', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'vigente')
  sessionStorage.setItem(REFRESH_KEY, 'renovable')
  const profile = deferred()
  const calls = []
  globalThis.fetch = (url) => {
    calls.push(url)
    return profile.promise
  }

  const pending = authenticatedFetch('/api/orders/')
  closeSession()
  profile.resolve(response(200, { id: 1, role: 'ADMIN' }))

  await assert.rejects(pending, /sesión ha expirado/)
  assert.deepEqual(calls, ['/api/auth/me/'])
  assert.equal(getCurrentUser(), null)
  assert.equal(sessionStorage.getItem(ACCESS_KEY), null)
})

test('una verificación anterior no sustituye un nuevo inicio de sesión', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'anterior')
  const oldProfile = deferred()
  globalThis.fetch = (url, options) => {
    if (url === '/api/auth/login/') return Promise.resolve(response(200, { access: 'nuevo', refresh: 'refresco' }))
    if (options.headers.Authorization === 'Bearer anterior') return oldProfile.promise
    return Promise.resolve(response(200, { id: 2, role: 'TECH' }))
  }

  const oldCheck = getAuthenticatedUser()
  await startSession('tecnico', 'clave')
  oldProfile.resolve(response(200, { id: 1, role: 'ADMIN' }))

  assert.equal(await oldCheck, null)
  assert.deepEqual(getCurrentUser(), { id: 2, role: 'TECH' })
  assert.equal(sessionStorage.getItem(USER_KEY), JSON.stringify({ id: 2, role: 'TECH' }))
})

for (const method of ['WHATSAPP', 'EMAIL', 'PRINT']) {
  test(`renueva la sesión si vence al entregar el comprobante por ${method}`, async () => {
    sessionStorage.setItem(ACCESS_KEY, 'vigente-al-verificar')
    sessionStorage.setItem(REFRESH_KEY, 'renovable')
    const deliveries = []
    globalThis.fetch = async (url, options) => {
      if (url === '/api/auth/me/') return response(200, { id: 1, role: 'ADMIN' })
      if (url === '/api/auth/refresh/') return response(200, { access: 'renovado' })
      deliveries.push({
        authorization: options.headers.get('Authorization'),
        body: JSON.parse(options.body),
      })
      return deliveries.length === 1
        ? response(401, { detail: 'Given token not valid for any token type' })
        : response(201, { detail: 'Comprobante procesado.' })
    }

    const result = await authenticatedFetch('/api/orders/1/reception-receipt/deliver/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delivery_method: method }),
    })

    assert.equal(result.status, 201)
    assert.deepEqual(deliveries, [
      { authorization: 'Bearer vigente-al-verificar', body: { delivery_method: method } },
      { authorization: 'Bearer renovado', body: { delivery_method: method } },
    ])
  })
}

for (const { label, url, body } of [
  { label: 'cliente', url: '/api/clients/', body: { name: 'Ana', phone: '+56912345678' } },
  { label: 'equipo', url: '/api/devices/', body: { client: 1, brand: 'Samsung', model: 'A14' } },
  { label: 'orden', url: '/api/orders/', body: { client: 1, equipment: 2, reported_issue: 'Carga' } },
]) {
  test(`renueva la sesión si se tarda en registrar ${label}`, async () => {
    sessionStorage.setItem(ACCESS_KEY, 'anterior')
    sessionStorage.setItem(REFRESH_KEY, 'renovable')
    const requests = []
    globalThis.fetch = async (requestUrl, options) => {
      if (requestUrl === '/api/auth/me/') return response(200, { id: 1, role: 'ADMIN' })
      if (requestUrl === '/api/auth/refresh/') return response(200, { access: 'nuevo' })
      requests.push({ url: requestUrl, token: options.headers.get('Authorization'), body: JSON.parse(options.body) })
      return response(requests.length === 1 ? 401 : 201, {})
    }

    const result = await authenticatedFetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    assert.equal(result.status, 201)
    assert.deepEqual(requests, [
      { url, token: 'Bearer anterior', body },
      { url, token: 'Bearer nuevo', body },
    ])
  })
}

test('dos operaciones vencidas comparten una renovación y conservan sus datos', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'anterior')
  sessionStorage.setItem(REFRESH_KEY, 'renovable')
  const refresh = deferred()
  const calls = []
  globalThis.fetch = (url, options) => {
    if (url === '/api/auth/me/') return Promise.resolve(response(200, { id: 1, role: 'ADMIN' }))
    if (url === '/api/auth/refresh/') {
      calls.push('refresh')
      return refresh.promise
    }
    calls.push({ url, authorization: options.headers.get('Authorization') })
    return Promise.resolve(response(options.headers.get('Authorization') === 'Bearer anterior' ? 401 : 201, {}))
  }

  const pending = Promise.all([
    authenticatedFetch('/api/orders/1/reception-receipt/deliver/', { method: 'POST' }),
    authenticatedFetch('/api/orders/2/reception-receipt/deliver/', { method: 'POST' }),
  ])
  await new Promise((resolve) => setImmediate(resolve))
  assert.equal(calls.filter((call) => call === 'refresh').length, 1)
  refresh.resolve(response(200, { access: 'nuevo' }))

  const results = await pending
  assert.deepEqual(results.map(({ status }) => status), [201, 201])
  assert.equal(calls.filter((call) => call === 'refresh').length, 1)
  assert.equal(calls.filter((call) => call.authorization === 'Bearer nuevo').length, 2)
})

test('un refresh vencido muestra un mensaje claro sin repetir el envío', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'anterior')
  sessionStorage.setItem(REFRESH_KEY, 'vencido')
  let deliveries = 0
  globalThis.fetch = async (url) => {
    if (url === '/api/auth/me/') return response(200, { id: 1, role: 'ADMIN' })
    if (url === '/api/auth/refresh/') return response(401, { detail: 'Token is invalid or expired' })
    deliveries += 1
    return response(401, { detail: 'Given token not valid for any token type' })
  }

  await assert.rejects(
    authenticatedFetch('/api/orders/1/reception-receipt/deliver/', { method: 'POST' }),
    /Tu sesión ha expirado. Vuelve a iniciar sesión./,
  )
  assert.equal(deliveries, 1)
  assert.equal(sessionStorage.getItem(ACCESS_KEY), null)
  assert.equal(getCurrentUser(), null)
})

test('una falla del proveedor de correo no reenvía la operación', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'vigente')
  let deliveries = 0
  globalThis.fetch = async (url) => {
    if (url === '/api/auth/me/') return response(200, { id: 1, role: 'ADMIN' })
    deliveries += 1
    return response(502, { detail: 'No fue posible enviar el correo.' })
  }

  const result = await authenticatedFetch('/api/orders/1/reception-receipt/deliver/', {
    method: 'POST',
    body: JSON.stringify({ delivery_method: 'EMAIL' }),
  })
  assert.equal(result.status, 502)
  assert.equal(deliveries, 1)
})

test('un cierre de sesión durante la renovación no recupera los tokens', async () => {
  sessionStorage.setItem(ACCESS_KEY, 'anterior')
  sessionStorage.setItem(REFRESH_KEY, 'renovable')
  const refresh = deferred()
  let deliveries = 0
  globalThis.fetch = (url) => {
    if (url === '/api/auth/me/') return Promise.resolve(response(200, { id: 1, role: 'ADMIN' }))
    if (url === '/api/auth/refresh/') return refresh.promise
    deliveries += 1
    return Promise.resolve(response(401, {}))
  }

  const pending = authenticatedFetch('/api/orders/1/reception-receipt/deliver/', { method: 'POST' })
  await new Promise((resolve) => setImmediate(resolve))
  closeSession()
  refresh.resolve(response(200, { access: 'no-debe-restaurarse' }))

  await assert.rejects(pending, /sesión ha expirado/)
  assert.equal(deliveries, 1)
  assert.equal(sessionStorage.getItem(ACCESS_KEY), null)
})
