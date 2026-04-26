/**
 * Notification Center — BFIU §3.2 Step 5
 * Endpoints: /api/v1/notification/*
 */
import { useState, useEffect } from "react"
import { toast } from "react-hot-toast"
import { API, getToken } from "../../config"
import { Bell, Send, RefreshCw, CheckCircle, XCircle } from "lucide-react"

const token = () => getToken() || localStorage.getItem("ekyc_admin_token") || ""
const apiFetch = (path, opts={}) => fetch(`${API}${path}`, {
  ...opts,
  headers: { "Content-Type":"application/json", Authorization:`Bearer ${token()}`, ...(opts.headers||{}) }
}).then(r => r.json())

export default function NotificationCenter() {
  const [logs, setLogs]       = useState([])
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [form, setForm]       = useState({
    session_id:"", full_name:"", mobile:"", email:"",
    kyc_type:"SIMPLIFIED", risk_grade:"LOW", confidence: 0.85
  })

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [l, s] = await Promise.all([
        apiFetch("/api/v1/notification/log?limit=50"),
        apiFetch("/api/v1/notification/stats"),
      ])
      setLogs(l.logs || l.notifications || [])
      setStats(s)
    } catch { setLogs([]) }
    finally { setLoading(false) }
  }

  const sendSuccess = async () => {
    if (!form.session_id || !form.mobile) { toast.error("Session ID and mobile required"); return }
    try {
      await apiFetch("/api/v1/notification/kyc-success", {
        method:"POST", body: JSON.stringify(form)
      })
      toast.success("✓ KYC success notification dispatched (BFIU §3.2 Step 5)")
      loadData()
    } catch { toast.error("Notification failed") }
  }

  const sendFailure = async () => {
    if (!form.session_id || !form.mobile) { toast.error("Session ID and mobile required"); return }
    try {
      await apiFetch("/api/v1/notification/kyc-failure", {
        method:"POST",
        body: JSON.stringify({ session_id: form.session_id, mobile: form.mobile, reason:"Verification failed" })
      })
      toast.success("KYC failure notification sent")
      loadData()
    } catch { toast.error("Notification failed") }
  }

  const f = k => e => setForm(p => ({...p, [k]: e.target.value}))

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Notification Center</div>
        <div className="page-subtitle">SMS + Email dispatch · BFIU §3.2 Step 5</div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:20 }}>
          {[
            { label:"Total Sent",   value:stats.total||0,      color:"blue"  },
            { label:"SMS",          value:stats.sms_count||0,  color:"green" },
            { label:"Email",        value:stats.email_count||0,color:"accent"},
            { label:"Dev Logged",   value:stats.dev_logged||0, color:"amber" },
          ].map(s => (
            <div key={s.label} className="stat-card">
              <div className="stat-value">{s.value}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Manual send */}
      <div className="data-card" style={{ marginBottom:16 }}>
        <div className="data-card-header">
          <span className="data-card-title"><Send size={14}/> Manual Notification</span>
          <span className="badge badge-blue">BFIU §3.2 Step 5</span>
        </div>
        <div className="data-card-body">
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:14 }}>
            {[["Session ID","session_id"],["Full Name","full_name"],["Mobile","mobile"],["Email","email"]].map(([l,k]) => (
              <div key={k}>
                <label className="input-label">{l}</label>
                <input className="glass-input" value={form[k]} onChange={f(k)} placeholder={l}/>
              </div>
            ))}
          </div>
          <div style={{ display:"flex", gap:10 }}>
            <button className="btn btn-success btn-md" onClick={sendSuccess}>
              <CheckCircle size={13}/> Send Success Notification
            </button>
            <button className="btn btn-danger btn-md" onClick={sendFailure}>
              <XCircle size={13}/> Send Failure Notification
            </button>
          </div>
        </div>
      </div>

      {/* Log */}
      <div className="data-card" style={{ padding:0, overflow:"hidden" }}>
        <div className="data-card-header">
          <span className="data-card-title"><Bell size={14}/> Notification Log</span>
          <button className="btn btn-outline btn-sm" onClick={loadData}><RefreshCw size={12}/></button>
        </div>
        {loading ? (
          <div style={{ padding:32, textAlign:"center", color:"var(--text3)" }}>Loading…</div>
        ) : logs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🔔</div>
            <div className="empty-title">No notifications yet</div>
          </div>
        ) : (
          <table className="glass-table">
            <thead><tr>
              <th>Type</th><th>Channel</th><th>Recipient</th>
              <th>Session</th><th>Status</th><th>Time</th>
            </tr></thead>
            <tbody>
              {logs.map((l,i) => (
                <tr key={i}>
                  <td style={{ fontSize:11 }}>{l.notification_type||l.type}</td>
                  <td><span className="badge badge-blue">{l.channel}</span></td>
                  <td style={{ fontSize:11 }}>{l.recipient}</td>
                  <td className="font-mono" style={{ fontSize:10, color:"var(--text3)" }}>{l.session_id?.slice(0,16)}</td>
                  <td><span className={`badge ${l.status==="SENT"?"badge-green":l.status==="DEV_LOGGED"?"badge-yellow":"badge-red"}`}>{l.status}</span></td>
                  <td style={{ fontSize:11, color:"var(--text3)" }}>{l.timestamp ? new Date(l.timestamp).toLocaleTimeString("en-BD") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
