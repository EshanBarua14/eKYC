import { create } from "zustand"
import { persist } from "zustand/middleware"

function decodeToken(token) {
  try {
    if (!token) return null
    const p = JSON.parse(atob(token.split(".")[1]))
    if (p.exp < Math.floor(Date.now() / 1000)) return null
    return p
  } catch { return null }
}

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      role: null,
      theme: "light",

      login: (token) => {
        const payload = decodeToken(token)
        if (!payload) return false
        localStorage.setItem("ekyc_token", token)
        localStorage.setItem("ekyc_admin_token", token)
        set({
          token,
          role: (payload.role || "").toUpperCase(),
          user: {
            id:           payload.user_id || payload.sub,
            institution:  payload.sub,
            schema:       payload.tenant_schema,
            role:         (payload.role || "").toUpperCase(),
          }
        })
        return true
      },

      logout: () => {
        localStorage.removeItem("ekyc_token")
        localStorage.removeItem("ekyc_admin_token")
        set({ token: null, user: null, role: null })
      },

      toggleTheme: () => set(s => {
        const next = s.theme === "light" ? "dark" : "light"
        document.documentElement.classList.toggle("dark", next === "dark")
        return { theme: next }
      }),

      setTheme: (theme) => {
        document.documentElement.classList.toggle("dark", theme === "dark")
        set({ theme })
      },
    }),
    { name: "ekyc-auth", partialize: s => ({ token: s.token, theme: s.theme }) }
  )
)
