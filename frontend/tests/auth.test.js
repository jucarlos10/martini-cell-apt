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
