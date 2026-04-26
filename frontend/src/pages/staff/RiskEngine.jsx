/**
 * Risk Engine — BFIU Annexure-1
 * Manual risk grading + rescore
 * Endpoints: /api/v1/risk/*
 */
import { useState } from "react"
import { toast } from "react-hot-toast"
import { API, getToken } from "../../config"
import { BarChart3, RefreshCw, AlertTriangle } from "lucide-react"

const token = () => getToken() || localStorage.getItem("ekyc_admin_token") || ""
const apiFetch = (path, opts={}) => fetch(`${API}${path}`, {
  ...opts,
  headers: { "Content-Type":"application/json", Authorization:`Bearer ${token()}`, ...(opts.headers||{}) }
}).then(r => r.json())

export default function RiskEngine() {
  const [form, setForm]     = useState({
    nationality:"BD", profession:"", monthly_income:"",
    source_of_funds:"", pep_flag: false, unscr_checked: false,
    product_amount:"", institution_type:"INSURANCE_LIFE"
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [factors, setFactors] = useState(null)
  const [thresholds, setThresholds] = useState(null)

  const grade = async () => {
    setLoading(true)
    try {
      const d = await apiFetch("/api/v1/risk/grade", {
        method:"POST",
        body: JSON.stringify({
          ...form,
          monthly_income: parseFloat(form.monthly_income)||0,
          product_amount: parseFloat(form.product_amount)||0,
          pep_flag: form.pep_flag === "true" || form.pep_flag === true,
        })
      })
      setResult(d)
      const grade = d.grade || d.risk_grade
      if (grade === "HIGH") toast.error("HIGH RISK — EDD required (BFIU §4.3)")
      else if (grade === "MEDIUM") toast.warning("MEDIUM RISK — Enhanced monitoring")
      else toast.success("LOW RISK ✓")
    } catch { toast.error("Risk grading failed") }
    finally { setLoading(false) }
  }

  const loadFactors = async () => {
    const d = await apiFetch("/api/v1/risk/factors")
    setFactors(d.factors || d)
    toast.success("Risk factors loaded")
  }

  const loadThresholds = async () => {
    const d = await apiFetch("/api/v1/risk/thresholds")
    setThresholds(d.thresholds || d)
  }

  const f = k => e => setForm(p => ({...p, [k]: e.target.value}))

  const gradeColor = { HIGH:"var(--red)", MEDIUM:"var(--yellow)", LOW:"var(--green)" }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Risk Engine</div>
        <div className="page-subtitle">7-dimension risk grading · BFIU Annexure-1</div>
      </div>

      <div style={{ display:"flex", gap:10, marginBottom:16 }}>
        <button className="btn btn-outline btn-sm" onClick={loadFactors}><BarChart3 size={12}/> View Factors</button>
        <button className="btn btn-outline btn-sm" onClick={loadThresholds}><RefreshCw size={12}/> Thresholds</button>
      </div>

      {thresholds && (
        <div className="data-card" style={{ marginBottom:16 }}>
          <div className="data-card-header"><span className="data-card-title">Risk Thresholds</span></div>
          <div className="data-card-body">
            <div style={{ display:"flex", gap:12 }}>
              {Object.entries(thresholds).map(([k,v]) => (
                <div key={k} style={{ padding:"8px 14px", background:"var(--bg3)", borderRadius:8, border:"1px solid var(--border)" }}>
                  <div style={{ fontSize:10, color:"var(--text3)", textTransform:"uppercase" }}>{k.replace(/_/g," ")}</div>
                  <div style={{ fontSize:16, fontWeight:800, color:"var(--text)" }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        {/* Input */}
        <div className="data-card">
          <div className="data-card-header"><span className="data-card-title">Customer Risk Profile</span></div>
          <div className="data-card-body" style={{ display:"grid", gap:12 }}>
            {[["Nationality (ISO)","nationality"],["Profession","profession"],
              ["Monthly Income (BDT)","monthly_income"],["Source of Funds","source_of_funds"],
              ["Product Amount","product_amount"]].map(([l,k]) => (
              <div key={k}>
                <label className="input-label">{l}</label>
                <input className="glass-input" value={form[k]} onChange={f(k)}
                  type={k.includes("income")||k.includes("amount")?"number":"text"} placeholder={l}/>
              </div>
            ))}
            <div>
              <label className="input-label">Institution Type</label>
              <select className="glass-input" value={form.institution_type} onChange={f("institution_type")}>
                {["INSURANCE_LIFE","INSURANCE_NON_LIFE","CMI","BANK","MFI"].map(t=>
                  <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
              </select>
            </div>
            <div style={{ display:"flex", gap:16 }}>
              {[["pep_flag","PEP/IP Flag"],["unscr_checked","UNSCR Checked"]].map(([k,l]) => (
                <label key={k} style={{ display:"flex", alignItems:"center", gap:6, fontSize:12, fontWeight:600, color:"var(--text2)", cursor:"pointer" }}>
                  <input type="checkbox" checked={!!form[k]}
                    onChange={e=>setForm(p=>({...p,[k]:e.target.checked}))}/>
                  {l}
                </label>
              ))}
            </div>
            <button className="btn btn-primary btn-md" onClick={grade} disabled={loading}>
              {loading ? "Grading…" : "Calculate Risk Grade"}
            </button>
          </div>
        </div>

        {/* Result */}
        <div className="data-card">
          <div className="data-card-header"><span className="data-card-title">Risk Assessment Result</span></div>
          <div className="data-card-body">
            {!result ? (
              <div className="empty-state" style={{ padding:"40px 20px" }}>
                <div className="empty-icon">📊</div>
                <div className="empty-title">No result yet</div>
                <div className="empty-desc">Fill the form and calculate</div>
              </div>
            ) : (
              <div style={{ textAlign:"center" }}>
                <div style={{ fontSize:64, fontWeight:900, color: gradeColor[result.grade||result.risk_grade], lineHeight:1 }}>
                  {result.grade || result.risk_grade}
                </div>
                <div style={{ fontSize:13, color:"var(--text3)", marginTop:8 }}>Risk Grade · Score: {result.total_score ?? result.score ?? "—"}</div>
                {result.edd_required && (
                  <div className="alert alert-danger" style={{ marginTop:16, textAlign:"left" }}>
                    <AlertTriangle size={14}/> <span>EDD Required — BFIU §4.3</span>
                  </div>
                )}
                {result.dimensions && (
                  <div style={{ marginTop:16, textAlign:"left" }}>
                    <div style={{ fontSize:11, fontWeight:700, color:"var(--text3)", marginBottom:8 }}>DIMENSIONS</div>
                    {Object.entries(result.dimensions).map(([k,v]) => (
                      <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"4px 0", borderBottom:"1px solid var(--border)", fontSize:12 }}>
                        <span style={{ color:"var(--text2)" }}>{k.replace(/_/g," ")}</span>
                        <span style={{ fontWeight:700, color:"var(--text)" }}>{v}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
