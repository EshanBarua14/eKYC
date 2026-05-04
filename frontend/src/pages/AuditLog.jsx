import { useEffect, useState } from "react"
import { Download, RefreshCw } from "lucide-react"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import Badge from "../components/ui/Badge"
import { api } from "../hooks/useApi"
import { notify } from "../components/ui/Toast"

function toBDTime(ts) {
  if (!ts) return "—"
  try {
    return new Date(ts).toLocaleString("en-BD", {
      timeZone: "Asia/Dhaka",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false
    })
  } catch { return ts }
}

const SEV_COLOR = { INFO:"blue", WARNING:"amber", ERROR:"red", CRITICAL:"red" }
const LIMIT = 20

export default function AuditLog() {
  const [logs, setLogs]       = useState([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal]     = useState(0)
  const [page, setPage]       = useState(1)
  const [filter, setFilter]   = useState("")
  const [sev, setSev]         = useState("ALL")

  const load = async (p = page) => {
    setLoading(true)
    try {
      const offset = (p - 1) * LIMIT
      const res = await api.get(`/api/v1/admin/audit-logs?limit=${LIMIT}&offset=${offset}`)
      const d = res.data
      const entries = d?.logs || d?.items || d?.entries || (Array.isArray(d) ? d : [])
      setLogs(entries)
      setTotal(d?.total ?? entries.length)
    } catch { notify.error("Failed to load audit logs") }
    finally { setLoading(false) }
  }

  useEffect(() => { load(page) }, [page])

  const exportJSON = async () => {
    try {
      const res = await api.get("/api/v1/admin/audit-logs?limit=1000")
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" })
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob)
      a.download = `audit-${new Date().toISOString().split("T")[0]}.json`; a.click()
    } catch { notify.error("Export failed") }
  }

  const filtered = logs.filter(l => {
    const matchFilter = !filter ||
      l.event_type?.toLowerCase().includes(filter.toLowerCase()) ||
      l.actor_role?.toLowerCase().includes(filter.toLowerCase())
    const meta = typeof l.metadata === "string"
      ? (() => { try { return JSON.parse(l.metadata) } catch { return {} } })()
      : (l.metadata || {})
    const severity = meta?.severity || "INFO"
    const matchSev = sev === "ALL" || severity === sev
    return matchFilter && matchSev
  })

  const pages = Math.ceil(total / LIMIT)

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">Audit Logs</h2>
          <p className="text-sm text-gray-400 mt-1">
            Immutable Audit Trail · BFIU §5.1 · {total} entries · BST (UTC+6)
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" icon={<RefreshCw size={14}/>} onClick={() => load(page)}>Refresh</Button>
          <Button variant="outline"   icon={<Download size={14}/>}  onClick={exportJSON}>JSON</Button>
        </div>
      </div>

      <div className="flex gap-3 items-center">
        <input className="input max-w-xs" placeholder="Filter by event or role..."
          value={filter} onChange={e => setFilter(e.target.value)}/>
        <div className="flex gap-1">
          {["ALL","INFO","WARNING","ERROR"].map(s => (
            <button key={s} onClick={() => setSev(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
                ${sev===s?"bg-brand-500 text-white border-brand-500":"border-gray-200 dark:border-gray-700 text-gray-500"}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      <Card className="p-0 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading audit trail...</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <p className="font-medium">No audit events</p>
            <p className="text-xs mt-1">Events are recorded automatically</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50 dark:divide-gray-800">
            {filtered.map((log, i) => {
              const meta = typeof log.metadata === "string"
                ? (() => { try { return JSON.parse(log.metadata) } catch { return {} } })()
                : (log.metadata || {})
              const severity = meta?.severity || "INFO"
              const message = meta?.message || log.description || log.action || ""
              const ts = log.timestamp || log.created_at
              return (
                <div key={log.id || i} className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                  <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0
                    ${severity==="WARNING"?"bg-amber-400":severity==="ERROR"?"bg-red-500":"bg-blue-400"}`}/>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs font-semibold text-gray-800 dark:text-gray-200">{log.event_type}</span>
                      <Badge color={SEV_COLOR[severity]||"blue"}>{severity}</Badge>
                      {log.actor_role && <Badge color="gray">{log.actor_role}</Badge>}
                    </div>
                    {message && <p className="text-xs text-gray-400 mt-0.5 truncate">{message}</p>}
                    {log.actor_id && <p className="text-xs text-gray-300 dark:text-gray-600 mt-0.5 font-mono">actor: {log.actor_id}</p>}
                  </div>
                  <div className="text-xs text-gray-400 flex-shrink-0 text-right">
                    <div>{toBDTime(ts)}</div>
                    {log.ip_address && <div className="text-gray-300 dark:text-gray-600">{log.ip_address}</div>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{total} total entries</span>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>← Prev</Button>
            <span className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs">Page {page} of {pages}</span>
            <Button variant="secondary" size="sm" disabled={page>=pages} onClick={()=>setPage(p=>p+1)}>Next →</Button>
          </div>
        </div>
      )}
    </div>
  )
}
