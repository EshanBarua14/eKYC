/**
 * Screening Panel — BFIU §3.2.2/§4.2
 * UNSCR + PEP + Adverse Media + Exit List
 * Endpoints: /api/v1/screening/*, /api/v1/pep/*
 */
import { useState } from "react"
import { toast } from "react-hot-toast"
import { API, getToken } from "../../config"
import { Search, Shield, AlertTriangle, CheckCircle, XCircle } from "lucide-react"

const token = () => getToken() || localStorage.getItem("ekyc_admin_token") || ""
const apiFetch = (path, opts={}) => fetch(`${API}${path}`, {
  ...opts,
  headers: { "Content-Type":"application/json", Authorization:`Bearer ${token()}`, ...(opts.headers||{}) }
}).then(r => r.json())

export default function ScreeningPanel() {
  const [name, setName]       = useState("")
  const [nid, setNid]         = useState("")
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [unscr, setUnscr]     = useState(null)

  const runScreening = async () => {
    if (!name && !nid) { toast.error("Enter name or NID"); return }
    setLoading(true)
    try {
      const d = await apiFetch("/api/v1/screening/check", {
        method:"POST",
        body: JSON.stringify({ name, nid_number: nid, institution_id:"inst-demo-001" })
      })
      setResult(d)
      if (d.overall_verdict === "BLOCKED") toast.error("⚠️ SCREENING HIT — EDD Required")
      else if (d.overall_verdict === "REVIEW") toast.warning("Screening: Manual review recommended")
      else toast.success("Screening: CLEAR ✓")
    } catch(e) { toast.error("Screening failed") }
    finally { setLoading(false) }
  }

  const checkUnscr = async () => {
    try {
      const d = await apiFetch("/api/v1/screening/unscr/status")
      setUnscr(d)
    } catch { toast.error("UNSCR status check failed") }
  }

  const addExitList = async () => {
    if (!nid) { toast.error("NID required for exit list"); return }
    try {
      await apiFetch("/api/v1/exit-list/add", {
        method:"POST",
        body: JSON.stringify({ nid_number: nid, reason:"COMPLIANCE_BLOCK", added_by:"compliance_officer" })
      })
      toast.success("Added to exit list ✓ (BFIU §5.1)")
    } catch { toast.error("Exit list add failed") }
  }

  const verdictColor = { CLEAR:"badge-green", REVIEW:"badge-yellow", BLOCKED:"badge-red" }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Screening Panel</div>
        <div className="page-subtitle">UNSCR · PEP · Adverse Media · Exit List — BFIU §3.2.2/§4.2</div>
      </div>

      {/* UNSCR Status */}
      <div style={{ display:"flex", gap:10, marginBottom:16 }}>
        <button className="btn btn-outline btn-sm" onClick={checkUnscr}>
          <Shield size={12}/> Check UNSCR Feed Status
        </button>
        {unscr && (
          <span className={`badge ${unscr.is_fresh?"badge-green":"badge-red"}`}>
            UNSCR: {unscr.is_fresh?"FRESH":"STALE"} · {unscr.total_entries||0} entries · Last: {unscr.last_updated||"unknown"}
          </span>
        )}
      </div>

      {/* Search form */}
      <div className="data-card" style={{ marginBottom:16 }}>
        <div className="data-card-header">
          <span className="data-card-title"><Search size={14}/> Run Screening Check</span>
          <span className="badge badge-accent">BFIU §3.2.2</span>
        </div>
        <div className="data-card-body">
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:14 }}>
            <div>
              <label className="input-label">Full Name</label>
              <input className="glass-input" value={name} onChange={e=>setName(e.target.value)}
                placeholder="Customer full name"/>
            </div>
            <div>
              <label className="input-label">NID Number</label>
              <input className="glass-input" value={nid} onChange={e=>setNid(e.target.value)}
                placeholder="NID number"/>
            </div>
          </div>
          <div style={{ display:"flex", gap:10 }}>
            <button className="btn btn-primary btn-md" onClick={runScreening} disabled={loading}>
              <Search size={13}/> {loading ? "Screening…" : "Run Full Screening"}
            </button>
            <button className="btn btn-danger btn-sm" onClick={addExitList}>
              Add to Exit List
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="data-card">
          <div className="data-card-header">
            <span className="data-card-title">Screening Results</span>
            <span className={`badge ${verdictColor[result.overall_verdict]||"badge-gray"}`}>
              {result.overall_verdict || "UNKNOWN"}
            </span>
          </div>
          <div className="data-card-body">
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12 }}>
              {[
                { label:"UNSCR",        key:"unscr_result",   bfiu:"§3.2.2" },
                { label:"PEP/IP",       key:"pep_result",     bfiu:"§4.2"   },
                { label:"Adverse Media",key:"adverse_result",  bfiu:"§5.3"  },
                { label:"Exit List",    key:"exit_list_result",bfiu:"§5.1"  },
              ].map(item => {
                const r = result[item.key] || {}
                const hit = r.hit || r.found || r.blocked
                return (
                  <div key={item.key} style={{ padding:"12px 14px", background:"var(--bg3)", borderRadius:10, border:`1px solid ${hit?"var(--red-border)":"var(--border)"}` }}>
                    <div style={{ fontSize:11, fontWeight:700, color:"var(--text3)", marginBottom:4 }}>{item.label} <span style={{ color:"var(--text4)", fontWeight:400 }}>{item.bfiu}</span></div>
                    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                      {hit
                        ? <><XCircle size={14} color="var(--red)"/><span style={{ color:"var(--red)", fontSize:12, fontWeight:700 }}>HIT</span></>
                        : <><CheckCircle size={14} color="var(--green)"/><span style={{ color:"var(--green)", fontSize:12, fontWeight:700 }}>CLEAR</span></>
                      }
                    </div>
                    {r.match_score && <div style={{ fontSize:10, color:"var(--text3)", marginTop:4 }}>Score: {r.match_score}%</div>}
                  </div>
                )
              })}
            </div>
            {result.edd_required && (
              <div className="alert alert-danger" style={{ marginTop:14 }}>
                <AlertTriangle size={14} style={{ flexShrink:0 }}/>
                <span><strong>EDD Required</strong> — Screening hit detected. Enhanced Due Diligence mandatory per BFIU §4.3.</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
