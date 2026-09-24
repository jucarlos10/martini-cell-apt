
const ACCESS_KEY = 'martini_access_token'
const REFRESH_KEY = 'martini_refresh_token'
const USER_KEY = 'martini_auth_user'

// Iniciar sesión con las credenciales reales de Django.
export async function startSession(username, password) {
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

// Comprobar la sesión y renovar el token si ha expirado.
export async function getAuthenticatedUser() {
  let access = sessionStorage.getItem(ACCESS_KEY)

  if (!access) {
    return null
  }

  let response = await fetch('/api/auth/me/', {
    headers: {
      Authorization: `Bearer ${access}`,
    },
  })

  if (response.status === 401) {
    const refresh = sessionStorage.getItem(REFRESH_KEY)

    if (!refresh) {
      closeSession()
      return null
    }

    const refreshResponse = await fetch('/api/auth/refresh/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh }),
    })

    if (!refreshResponse.ok) {
      closeSession()
      return null
    }

    const newTokens = await refreshResponse.json()

    if (!newTokens.access) {
      closeSession()
      return null
    }

    access = newTokens.access
    sessionStorage.setItem(ACCESS_KEY, access)

    if (newTokens.refresh) {
      sessionStorage.setItem(REFRESH_KEY, newTokens.refresh)
    }

    response = await fetch('/api/auth/me/', {
      headers: {
        Authorization: `Bearer ${access}`,
      },
    })
  }

  if (!response.ok) {
    closeSession()
    return null
  }

  const user = await response.json()
  sessionStorage.setItem(USER_KEY, JSON.stringify(user))

  return user
}

// Cerrar la sesión del navegador.
export function closeSession() {
  sessionStorage.removeItem(ACCESS_KEY)
  sessionStorage.removeItem(REFRESH_KEY)
  sessionStorage.removeItem(USER_KEY)
}

// Realizar solicitudes a las API que requieren autenticación.
export async function authenticatedFetch(url, options = {}) {
  const user = await getAuthenticatedUser()

  if (!user) {
    throw new Error('Tu sesión ha expirado. Vuelve a iniciar sesión.')
  }

  // getAuthenticatedUser ya renovó el token si era necesario.
  const token = sessionStorage.getItem(ACCESS_KEY)
  const headers = new Headers(options.headers || {})

  headers.set('Authorization', `Bearer ${token}`)

  return fetch(url, {
    ...options,
    headers,
  })
}