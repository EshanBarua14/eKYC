/**
 * Fallback KYC — BFIU §3.2 Step 4
 * When biometric fails → document-based fallback
 * Endpoint: /api/v1/fallback/*
 */
import { useState, useEffect } from "react"
import { toast } from "react-hot-toast"
import { API, getToken } from "../../config"
import { Upload, FileText, CheckCircle, Clock, Eye, ChevronRight } from "lucide-react"

const token = () => getToken() || localStorage.getItem("ekyc_admin_token") || ""
const apiFetch = (path, opts={}) => fetch(`${API}${path}`, {
  ...opts,
  headers: { "Content-Type":"application/json", Authorization:`Bearer ${token()}`, ...(opts.headers||{}) }
}).then(r => r.json())

export default function FallbackKYC() {
  const [queue, setQueue]     = useState([])
  const [loading, setLoading] = useState(true)
  const [view, setView]       = useState("queue") // queue | create | review
  const [selected, setSelected] = useState(null)
  const [form, setForm]       = useState({ session_id:"", reason:"BIOMETRIC_FAILED", notes:"" })

  useEffect(() => { loadQueue() }, [])

  const loadQueue = async () => {
    setLoading(true)
    try {
      const d = await apiFetch("/api/v1/fallback/queue/pending")
      setQueue(d.applications || d.queue || [])
    } catch { setQueue([]) }
    finally { setLoading(false) }
  }

  const createFallback = async () => {
    if (!form.session_id) { toast.error("Session ID required"); return }
    try {
      await apiFetch("/api/v1/fallback/create", {
        method:"POST",
        body: JSON.stringify({ session_id: form.session_id, reason: form.reason, notes: form.notes })
      })
      toast.success("Fallback KYC application created ✓")
      setView("queue"); loadQueue()
    } catch(e) { toast.error("Failed to create fallback") }
  }

  const startReview = async (id) => {
    try {
      await apiFetch(`/api/v1/fallback/${id}/review/start`, { method:"POST" })
      toast.success("Review started")
      loadQueue()
    } catch { toast.error("Failed to start review") }
  }

  const decide = async (id, decision) => {
    try {
      await apiFetch(`/api/v1/fallback/${id}/review/decide`, {
        method:"POST",
        body: JSON.stringify({ decision, notes: `${decision} by reviewer` })
      })
      toast.success(`Application ${decision} ✓`)
      loadQueue()
    } catch { toast.error("Decision failed") }
  }

  const statusBadge = (s) => {
    const map = { APPROVED:"badge-green", REJECTED:"badge-red", PENDING:"badge-yellow",
                  UNDER_REVIEW:"badge-blue", SUBMITTED:"badge-accent" }
    return <span className={`badge ${map[s]||"badge-gray"}`}>{s}</span>
  }

  return (
    <div>
      <div className="page-header" style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between" }}>
        <div>
          <div className="page-title">Fallback KYC</div>
          <div className="page-subtitle">Document-based KYC when biometric fails · BFIU §3.2 Step 4</div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <button className="btn btn-outline btn-sm" onClick={() => setView("queue")}>Queue</button>
          <button className="btn btn-primary btn-sm" onClick={() => setView("create")}>+ New Fallback</button>
        </div>
      </div>

      <div className="alert alert-warning" style={{ marginBottom:16 }}>
        <span>⚠️</span>
        <span>Fallback KYC is only permitted when biometric verification fails 3 consecutive sessions (BFIU §3.2). All fallback applications require Checker approval.</span>
      </div>

      {view === "create" && (
        <div className="data-card" style={{ maxWidth:560, marginBottom:20 }}>
          <div className="data-card-header">
            <span className="data-card-title"><Upload size={14}/> Create Fallback Application</span>
          </div>
          <div className="data-card-body" style={{ display:"grid", gap:14 }}>
            <div>
              <label className="input-label">Session ID *</label>
              <input className="glass-input" value={form.session_id}
                onChange={e=>setForm(p=>({...p,session_id:e.target.value}))}
                placeholder="e.g. sess_1234567890"/>
            </div>
            <div>
              <label className="input-label">Reason</label>
              <select className="glass-input" value={form.reason}
                onChange={e=>setForm(p=>({...p,reason:e.target.value}))}>
                <option value="BIOMETRIC_FAILED">Biometric Failed (3 sessions)</option>
                <option value="HARDWARE_UNAVAILABLE">Hardware Unavailable</option>
                <option value="MEDICAL_EXEMPTION">Medical Exemption</option>
                <option value="ELDERLY_CUSTOMER">Elderly Customer</option>
              </select>
            </div>
            <div>
              <label className="input-label">Notes</label>
              <textarea className="glass-input" rows={3} value={form.notes}
                onChange={e=>setForm(p=>({...p,notes:e.target.value}))}
                placeholder="Reason for fallback…" style={{ resize:"vertical" }}/>
            </div>
            <button className="btn btn-primary btn-md" onClick={createFallback}>
              <Upload size={13}/> Create Fallback Application
            </button>
          </div>
        </div>
      )}

      <div className="data-card" style={{ padding:0, overflow:"hidden" }}>
        <div className="data-card-header">
          <span className="data-card-title"><FileText size={14}/> Fallback Queue</span>
          <button className="btn btn-outline btn-sm" onClick={loadQueue}>Refresh</button>
        </div>
        {loading ? (
          <div style={{ padding:40, textAlign:"center", color:"var(--text3)" }}>Loading…</div>
        ) : queue.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <div className="empty-title">No fallback applications</div>
            <div className="empty-desc">Fallback applications appear when biometric fails</div>
          </div>
        ) : (
          <table className="glass-table">
            <thead><tr>
              <th>Session ID</th><th>Reason</th><th>Status</th>
              <th>Created</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {queue.map((a,i) => (
                <tr key={i}>
                  <td className="font-mono" style={{ fontSize:11 }}>{a.session_id||a.id}</td>
                  <td style={{ fontSize:11 }}>{a.reason||"BIOMETRIC_FAILED"}</td>
                  <td>{statusBadge(a.status)}</td>
                  <td style={{ fontSize:11, color:"var(--text3)" }}>
                    {a.created_at ? new Date(a.created_at).toLocaleDateString("en-BD") : "—"}
                  </td>
                  <td>
                    <div style={{ display:"flex", gap:6 }}>
                      {a.status === "SUBMITTED" && (
                        <button className="btn btn-ghost btn-sm" onClick={() => startReview(a.id)}>
                          <Eye size={11}/> Review
                        </button>
                      )}
                      {a.status === "UNDER_REVIEW" && (
                        <>
                          <button className="btn btn-success btn-sm" onClick={() => decide(a.id,"APPROVED")}>
                            <CheckCircle size={11}/> Approve
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => decide(a.id,"REJECTED")}>
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
