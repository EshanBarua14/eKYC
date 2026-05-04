const host = window.location.hostname
export const API = host === "localhost" || host === "127.0.0.1"
  ? "https://103.244.247.217"
  : `https://${host}`

const TOKEN_KEY       = "ekyc_token"
const ADMIN_TOKEN_KEY = "ekyc_admin_token"

export const getToken   = () => localStorage.getItem(TOKEN_KEY) || ""
export const setToken   = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export const authHeaders = (extra = {}) => ({
  "Content-Type": "application/json",
  ...(getToken() ? { "Authorization": `Bearer ${getToken()}` } : {}),
  ...extra,
})

function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp < Math.floor(Date.now() / 1000) + 30
  } catch { return true }
}

const DEMO_EMAIL    = "agent@demo.ekyc"
const DEMO_PASSWORD = "DemoAgent@2026"
const DEMO_PHONE    = "01700000001"
const DEMO_NAME     = "Demo Agent"

export const ensureDemoToken = async () => {
  const existing = getToken()
  if (existing && !isTokenExpired(existing)) return existing

  try {
    await fetch(`${API}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: DEMO_EMAIL, phone: DEMO_PHONE,
        full_name: DEMO_NAME, role: "agent",
        password: DEMO_PASSWORD, institution_id: "inst-demo-001" })
    })
  } catch (_) {}

  try {
    const r = await fetch(`${API}/api/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: DEMO_EMAIL, password: DEMO_PASSWORD })
    })
    if (r.ok) {
      const data = await r.json()
      const token = data.access_token || data.token || ""
      if (token) { setToken(token); return token }
    }
  } catch (_) {}
  return ""
}

export const getAdminToken = () => localStorage.getItem(ADMIN_TOKEN_KEY) || getToken()
export const setAdminToken = (t) => { localStorage.setItem(ADMIN_TOKEN_KEY, t); setToken(t) }

const ADMIN_EMAIL    = "admin@demo.ekyc"
const ADMIN_PASSWORD = "AdminDemo@2026"
const ADMIN_PHONE    = "01700000002"
const ADMIN_NAME     = "Demo Admin"

export const ensureAdminToken = async () => {
  // Use cached token if still valid
  const existing = localStorage.getItem(ADMIN_TOKEN_KEY)
  if (existing && !isTokenExpired(existing)) { setToken(existing); return existing }

  // Register (ignore 409)
  try {
    await fetch(`${API}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: ADMIN_EMAIL, phone: ADMIN_PHONE,
        full_name: ADMIN_NAME, role: "admin",
        password: ADMIN_PASSWORD, institution_id: "inst-demo-001" })
    })
  } catch (_) {}

  // Login
  try {
    const r = await fetch(`${API}/api/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD })
    })
    if (r.ok) {
      const data = await r.json()
      const token = data.access_token || data.token || ""
      if (token) { setAdminToken(token); return token }
    }
  } catch (_) {}

  return await ensureDemoToken()
}
