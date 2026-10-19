const STORAGE_KEY = 'campus-connect-auth'

// Rôles autorisés dans l'espace admin
export const ADMIN_ROLES = ['responsable', 'intervenant']

export function isAdmin(user) {
  return Boolean(user) && ADMIN_ROLES.includes(user.role)
}

/**
 * Connexion.
 * POST /api/auth/login  { username, password }
 *   username = e-mail (compte créé) ou identifiant (compte admin)
 *   → { token, username, role, display_name, expires_in }
 */
export async function login(username, password) {
  const data = await postJson('/api/auth/login', { username, password })
  return saveUser(data)
}

/**
 * Création d'un compte étudiant.
 * POST /api/auth/register  { email, display_name, password }
 *   → même réponse que /login (l'utilisateur est connecté directement)
 */
export async function register(email, displayName, password) {
  const data = await postJson('/api/auth/register', {
    email,
    display_name: displayName,
    password,
  })
  return saveUser(data)
}

export function logout() {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignoré */
  }
}

// Utilisateur connecté (null si absent ou jeton expiré)
export function getStoredUser() {
  try {
    const user = JSON.parse(sessionStorage.getItem(STORAGE_KEY))
    if (user?.token && user.expiresAt > Date.now()) return user
  } catch {
    /* sessionStorage indisponible */
  }
  return null
}

async function postJson(url, body) {
  let response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error('Impossible de joindre le serveur. Vérifiez votre connexion.')
  }

  if (response.ok) return response.json()

  const payload = await response.json().catch(() => null)
  const detail = payload?.detail

  if (response.status === 422) {
    throw new Error('Certaines informations sont invalides. Vérifiez l’e-mail et le mot de passe (8 caractères minimum).')
  }
  if (response.status === 503) {
    throw new Error('La connexion n’est pas encore activée sur le serveur.')
  }
  if (detail?.message) {
    throw new Error(detail.message)
  }
  throw new Error(`Erreur serveur (${response.status})`)
}

function saveUser(data) {
  const user = {
    token: data.token,
    username: data.username,
    role: data.role,
    displayName: data.display_name,
    expiresAt: Date.now() + data.expires_in * 1000,
  }
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user))
  } catch {
    /* ignoré */
  }
  return user
}
