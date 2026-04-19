const host = window.location.hostname
export const API = host === "localhost" || host === "127.0.0.1"
  ? "http://localhost:8000"
  : `http://${host}:8000`

// ── Token management ─────────────────────────────────────────────────────
const TOKEN_KEY = "ekyc_token"

export const getToken  = () => localStorage.getItem(TOKEN_KEY) || ""
export const setToken  = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

// Auth headers — include in every API call
export const authHeaders = (extra = {}) => ({
  "Content-Type": "application/json",
  ...(getToken() ? { "Authorization": `Bearer ${getToken()}` } : {}),
  ...extra,
})

// Demo agent credentials
const DEMO_EMAIL    = "agent@demo.ekyc"
const DEMO_PASSWORD = "DemoAgent@2026"
const DEMO_PHONE    = "01700000001"
const DEMO_NAME     = "Demo Agent"

// Auto-register + login if no token stored
export const ensureDemoToken = async () => {
  if (getToken()) return getToken()

  // Step 1: register demo agent (silently ignore 409 if already exists)
  try {
    await fetch(`${API}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email:          DEMO_EMAIL,
        phone:          DEMO_PHONE,
        full_name:      DEMO_NAME,
        role:           "agent",
        password:       DEMO_PASSWORD,
        institution_id: "inst-demo-001",
      })
    })
  } catch (_) {}

  // Step 2: login
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
