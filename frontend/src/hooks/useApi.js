import { useState, useCallback } from "react"
import axios from "axios"
import { useAuthStore } from "../store/authStore"
import { notify } from "../components/ui/Toast"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem("ekyc_token") || localStorage.getItem("ekyc_admin_token")
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      notify.error("Session expired — please log in again")
    }
    return Promise.reject(err)
  }
)

export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const request = useCallback(async (method, url, data = null, opts = {}) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api({ method, url, data, ...opts })
      return res.data
    } catch (err) {
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || "Request failed"
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    loading, error,
    get:    (url, opts) => request("get", url, null, opts),
    post:   (url, data, opts) => request("post", url, data, opts),
    put:    (url, data, opts) => request("put", url, data, opts),
    patch:  (url, data, opts) => request("patch", url, data, opts),
    delete: (url, opts) => request("delete", url, null, opts),
  }
}
