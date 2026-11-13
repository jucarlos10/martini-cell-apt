
const ACCESS_KEY = 'martini_access_token'
const REFRESH_KEY = 'martini_refresh_token'
const USER_KEY = 'martini_auth_user'
let sessionVersion = 0
let pendingSessionCheck = null
let pendingTokenRefresh = null
const SESSION_EXPIRED_MESSAGE = 'Tu sesión ha expirado. Vuelve a iniciar sesión.'

function sessionExpired() {
  return new Error(SESSION_EXPIRED_MESSAGE)
}

// Una sola renovación sirve a las vistas y a las solicitudes que reciban 401
// después de haber verificado la sesión. Nunca reponer una sesión ya cerrada.
async function refreshAccessToken(version, failedAccess) {
  if (version !== sessionVersion) return null

  const currentAccess = sessionStorage.getItem(ACCESS_KEY)
  if (currentAccess && currentAccess !== failedAccess) return currentAccess
  if (pendingTokenRefresh) return pendingTokenRefresh

  const refresh = sessionStorage.getItem(REFRESH_KEY)
  if (!refresh) {
    closeSession()
    return null
  }

  const pending = (async () => {
    const response = await fetch('/api/auth/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })

    if (version !== sessionVersion) return null

    if (response.status === 400 || response.status === 401) {
      closeSession()
      return null
    }
    if (!response.ok) {
      throw new Error('No fue posible renovar la sesión. Reintenta.')
    }

    const tokens = await response.json().catch(() => null)
    if (version !== sessionVersion) return null

    if (!tokens?.access) {
      closeSession()
      return null
    }

    sessionStorage.setItem(ACCESS_KEY, tokens.access)
    if (tokens.refresh) sessionStorage.setItem(REFRESH_KEY, tokens.refresh)
    return tokens.access
  })()

  pendingTokenRefresh = pending
  try {
    return await pending
  } finally {
    if (pendingTokenRefresh === pending) pendingTokenRefresh = null
  }
}

// Iniciar sesión con las credenciales reales de Django.
export async function startSession(username, password) {
  closeSession()
  const version = sessionVersion

  const response = await fetch('/api/auth/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Usuario o contraseña incorrectos.')
    }

    throw new Error('No fue posible iniciar sesión.')
  }

  const tokens = await response.json()

  if (!tokens.access || !tokens.refresh) {
    throw new Error('La respuesta de autenticación está incompleta.')
  }

  // Obtener el usuario y su rol desde el backend.
  const profileResponse = await fetch('/api/auth/me/', {
    headers: {
      Authorization: `Bearer ${tokens.access}`,
    },
  })

  if (!profileResponse.ok) {
    throw new Error('No fue posible verificar el usuario.')
  }

  const user = await profileResponse.json()

  // Un cierre de sesión posterior al envío no debe restaurar sus tokens.
  if (version !== sessionVersion) {
    throw new Error('El inicio de sesión fue cancelado.')
  }

  // Guardamos la sesión solo después de verificar el usuario.
  sessionStorage.setItem(ACCESS_KEY, tokens.access)
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh)
  sessionStorage.setItem(USER_KEY, JSON.stringify(user))

  return user
}

// Recuperar los datos del usuario de la sesión actual.
export function getCurrentUser() {
  try {
    return JSON.parse(sessionStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

// Verificar una sola vez cuando varias vistas solicitan datos al mismo tiempo.
async function verifySession(version) {
  let access = sessionStorage.getItem(ACCESS_KEY)

  if (!access) {
    return null
  }

  let response = await fetch('/api/auth/me/', {
    headers: {
      Authorization: `Bearer ${access}`,
    },
  })

  if (version !== sessionVersion) return null

  if (response.status === 401) {
    access = await refreshAccessToken(version, access)
    if (!access) return null

    response = await fetch('/api/auth/me/', {
      headers: {
        Authorization: `Bearer ${access}`,
      },
    })

    if (version !== sessionVersion) return null
  }

  if (!response.ok) {
    if (response.status === 401) {
      closeSession()
      return null
    }
    throw new Error('No fue posible comprobar la sesión. Reintenta.')
  }

  const user = await response.json()
  if (version !== sessionVersion) return null
  sessionStorage.setItem(USER_KEY, JSON.stringify(user))

  return user
}

// Compartir la comprobación en curso, incluida una eventual renovación.
export function getAuthenticatedUser() {
  if (pendingSessionCheck) return pendingSessionCheck

  const pending = verifySession(sessionVersion)
  pendingSessionCheck = pending
  const clearPending = () => {
    if (pendingSessionCheck === pending) pendingSessionCheck = null
  }
  pending.then(clearPending, clearPending)
  return pending
}

// Cerrar la sesión del navegador.
export function closeSession() {
  sessionVersion += 1
  pendingSessionCheck = null
  pendingTokenRefresh = null
  sessionStorage.removeItem(ACCESS_KEY)
  sessionStorage.removeItem(REFRESH_KEY)
  sessionStorage.removeItem(USER_KEY)
}

// Realizar solicitudes a las API que requieren autenticación.
export async function authenticatedFetch(url, options = {}) {
  const version = sessionVersion
  const user = await getAuthenticatedUser()

  if (!user || version !== sessionVersion) throw sessionExpired()

  const token = sessionStorage.getItem(ACCESS_KEY)
  if (!token) throw sessionExpired()
  const headers = new Headers(options.headers || {})

  headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (response.status !== 401) return response

  // El token puede vencer entre /me/ y una operación, incluso durante una
  // demostración. El backend rechaza esa solicitud antes de ejecutarla.
  const access = await refreshAccessToken(version, token)
  if (!access) throw sessionExpired()

  headers.set('Authorization', `Bearer ${access}`)
  const retry = await fetch(url, { ...options, headers })
  if (retry.status === 401) {
    if (version === sessionVersion) closeSession()
    throw sessionExpired()
  }
  return retry
}
