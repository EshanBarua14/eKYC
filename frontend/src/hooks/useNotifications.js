import { useState, useEffect, useRef, useCallback } from "react"
import { toast } from "react-hot-toast"

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"
const POLL_MS = 15000

function getColor(n) {
  if (n.status === "SUCCESS") return "green"
  if (n.status === "FAILED")  return "red"
  if (n.risk_grade === "HIGH") return "yellow"
  return "blue"
}

function formatTime(ts) {
  if (!ts) return ""
  try {
    const diff = (Date.now() - new Date(ts)) / 1000
    if (diff < 60)    return "just now"
    if (diff < 3600)  return Math.floor(diff / 60) + "m ago"
    if (diff < 86400) return Math.floor(diff / 3600) + "h ago"
    return new Date(ts).toLocaleDateString()
  } catch { return "" }
}

function getMsg(n) {
  if (n.message) return n.message
  if (n.full_name) return "KYC " + (n.status || "update") + " - " + n.full_name
  return "New notification"
}

export function useNotifications(userRole) {
  const [notifications, setNotifications] = useState([])
  const [unread, setUnread]               = useState(0)
  const seenIds  = useRef(new Set())
  const pollRef  = useRef(null)
  const firstRun = useRef(true)

  const fetchNotifs = useCallback(async () => {
    if (!userRole) return
    const token = localStorage.getItem("ekyc_token") ||
                  localStorage.getItem("ekyc_admin_token") || ""
    if (!token) return
    try {
      const r = await fetch(API + "/api/v1/notify/log?limit=20", {
        headers: { Authorization: "Bearer " + token }
      })
      if (!r.ok) return
      const data = await r.json()
      const items = (data.logs || data.notifications || []).map((n, i) => ({
        id:    n.id || n.session_id || String(i),
        msg:   getMsg(n),
        time:  formatTime(n.timestamp || n.sent_at || n.created_at),
        color: getColor(n),
      }))
      let newCount = 0
      items.forEach(n => {
        if (!seenIds.current.has(n.id)) {
          if (!firstRun.current) {
            newCount++
            toast((n.color === "red" ? "[!] " : "[+] ") + n.msg, {
              duration: 5000,
              style: { background: "var(--bg2)", color: "var(--text)",
                       border: "1px solid var(--border)", fontSize: 12 }
            })
          }
          seenIds.current.add(n.id)
        }
      })
      firstRun.current = false
      setNotifications(items)
      if (newCount > 0) setUnread(prev => prev + newCount)
    } catch {}
  }, [userRole])

  useEffect(() => {
    if (!userRole) return
    fetchNotifs()
    pollRef.current = setInterval(fetchNotifs, POLL_MS)
    return () => clearInterval(pollRef.current)
  }, [userRole, fetchNotifs])

  const markRead = useCallback(() => setUnread(0), [])
  return { notifications, unread, markRead }
}
