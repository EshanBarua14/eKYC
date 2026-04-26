/**
 * KYC Lifecycle Manager — BFIU §5.7
 * Periodic review, upgrade, closure
 * Endpoints: /api/v1/lifecycle/*
 */
import { useState, useEffect } from "react"
import { toast } from "react-hot-toast"
import { API, getToken } from "../../config"
import { RefreshCw, TrendingUp, Clock, XCircle, AlertTriangle } from "lucide-react"

const token = () => getToken() || localStorage.getItem("ekyc_admin_token") || ""
const apiFetch = (path, opts={}) => fetch(`${API}${path}`, {
  ...opts,
  headers: { "Content-Type":"application/json", Authorization:`Bearer ${token()}`, ...(opts.headers||{}) }
}).then(r => r.json())

export default function LifecycleManager() {
  const [dueReviews, setDueReviews] = useState([])
  const [loading, setLoading]       = useState(true)
  const [sessionId, setSessionId]   = useState("")
  const [activeAction, setActiveAction] = useState(null)

  useEffect(() => { loadDue() }, [])

  const loadDue = async () => {
    setLoading(true)
    try {
      const d = await apiFetch("/api/v1/lifecycle/due-reviews")
      setDueReviews(d.due_reviews || d.reviews || [])
    } catch { setDueReviews([]) }
    finally { setLoading(false) }
  }

  const initiateUpgrade = async () => {
    if (!sessionId) { toast.error("Session ID required"); return }
    try {
      await apiFetch("/api/v1/lifecycle/upgrade/initiate", {
        method:"POST", body: JSON.stringify({ session_id: sessionId })
      })
      toast.success("Simplified → Regular upgrade initiated ✓ (BFIU §5.7)")
    } catch(e) { toast.error("Upgrade initiation failed") }
  }

  const completeUpgrade = async () => {
    if (!sessionId) { toast.error("Session ID required"); return }
    try {
      await apiFetch("/api/v1/lifecycle/upgrade/complete", {
        method:"POST", body: JSON.stringify({ session_id: sessionId })
      })
      toast.success("KYC upgrade completed ✓")
    } catch { toast.error("Upgrade completion failed") }
  }

  const closeAccount = async () => {
    if (!sessionId) { toast.error("Session ID required"); return }
    try {
      await apiFetch("/api/v1/lifecycle/close", {
        method:"POST", body: JSON.stringify({ session_id: sessionId, reason:"Customer request" })
      })
      toast.success("Account closure initiated ✓ (5-year retention applies)")
    } catch { toast.error("Closure failed") }
  }

  const riskMap = { HIGH:"badge-red", MEDIUM:"badge-yellow", LOW:"badge-green" }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">KYC Lifecycle Manager</div>
        <div className="page-subtitle">Periodic review · Upgrade · Closure · BFIU §5.7</div>
      </div>

      {/* Review intervals info */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:20 }}>
        {[
          { risk:"HIGH",   interval:"Annual",    color:"var(--red)",    icon:"🔴" },
          { risk:"MEDIUM", interval:"2 years",   color:"var(--yellow)", icon:"🟡" },
          { risk:"LOW",    interval:"5 years",   color:"var(--green)",  icon:"🟢" },
        ].map(r => (
          <div key={r.risk} className="stat-card" style={{ textAlign:"center" }}>
            <div style={{ fontSize:24 }}>{r.icon}</div>
            <div style={{ fontSize:14, fontWeight:800, color:r.color, marginTop:6 }}>{r.risk} RISK</div>
            <div style={{ fontSize:11, color:"var(--text3)", marginTop:2 }}>Review every {r.interval}</div>
            <div style={{ fontSize:10, color:"var(--text4)", marginTop:2 }}>BFIU §5.7</div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="data-card" style={{ marginBottom:16 }}>
        <div className="data-card-header">
          <span className="data-card-title">Lifecycle Actions</span>
        </div>
        <div className="data-card-body">
          <div style={{ marginBottom:12 }}>
            <label className="input-label">Session ID</label>
            <input className="glass-input" value={sessionId}
              onChange={e=>setSessionId(e.target.value)}
              placeholder="Enter KYC session ID"/>
          </div>
          <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
            <button className="btn btn-ghost btn-sm" onClick={initiateUpgrade}>
              <TrendingUp size={12}/> Initiate Upgrade (Simplified→Regular)
            </button>
            <button className="btn btn-ghost btn-sm" onClick={completeUpgrade}>
              <RefreshCw size={12}/> Complete Upgrade
            </button>
            <button className="btn btn-danger btn-sm" onClick={closeAccount}>
              <XCircle size={12}/> Close Account
            </button>
          </div>
        </div>
      </div>

      {/* Due reviews */}
      <div className="data-card" style={{ padding:0, overflow:"hidden" }}>
        <div className="data-card-header">
          <span className="data-card-title"><Clock size={14}/> Due Reviews ({dueReviews.length})</span>
          <button className="btn btn-outline btn-sm" onClick={loadDue}>Refresh</button>
        </div>
        {dueReviews.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">✅</div>
            <div className="empty-title">No reviews due</div>
            <div className="empty-desc">All KYC profiles are within review schedule</div>
          </div>
        ) : (
          <table className="glass-table">
            <thead><tr>
              <th>Session</th><th>Customer</th><th>Risk Grade</th>
              <th>Last Review</th><th>Due Date</th><th>Status</th>
            </tr></thead>
            <tbody>
              {dueReviews.map((r,i) => (
                <tr key={i}>
                  <td className="font-mono" style={{ fontSize:11 }}>{r.session_id}</td>
                  <td style={{ fontWeight:600, color:"var(--text)" }}>{r.full_name||"—"}</td>
                  <td><span className={`badge ${riskMap[r.risk_grade]||"badge-gray"}`}>{r.risk_grade}</span></td>
                  <td style={{ fontSize:11, color:"var(--text3)" }}>{r.last_review_date||"Never"}</td>
                  <td style={{ fontSize:11, color: r.is_overdue?"var(--red)":"var(--text3)" }}>
                    {r.next_review_date||"—"}
                    {r.is_overdue && " ⚠️"}
                  </td>
                  <td><span className={`badge ${r.is_overdue?"badge-red":"badge-yellow"}`}>
                    {r.is_overdue?"OVERDUE":"DUE"}
                  </span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
