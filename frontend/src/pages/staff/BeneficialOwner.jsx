/**
 * Beneficial Owner — BFIU §4.2
 * Endpoints: /api/v1/kyc/beneficial-owner/*
 */
import { useState, useEffect } from "react"
import { toast } from "react-hot-toast"
import { API, getToken } from "../../config"
import { Users, Plus, CheckCircle, AlertTriangle } from "lucide-react"

const token = () => getToken() || localStorage.getItem("ekyc_admin_token") || ""
const apiFetch = (path, opts={}) => fetch(`${API}${path}`, {
  ...opts,
  headers: { "Content-Type":"application/json", Authorization:`Bearer ${token()}`, ...(opts.headers||{}) }
}).then(r => r.json())

export default function BeneficialOwner() {
  const [sessionId, setSessionId] = useState("")
  const [boData, setBoData]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [addForm, setAddForm]     = useState({
    full_name:"", nid_number:"", date_of_birth:"",
    ownership_percentage:"", relationship:"", is_pep: false
  })

  const lookup = async () => {
    if (!sessionId) { toast.error("Enter session ID"); return }
    setLoading(true)
    try {
      const d = await apiFetch(`/api/v1/kyc/beneficial-owner/${sessionId}`)
      setBoData(d)
    } catch { toast.error("No BO record found for this session") }
    finally { setLoading(false) }
  }

  const addBO = async () => {
    if (!addForm.full_name || !sessionId) { toast.error("Name and session ID required"); return }
    try {
      await apiFetch("/api/v1/kyc/beneficial-owner", {
        method:"POST",
        body: JSON.stringify({ ...addForm, session_id: sessionId })
      })
      toast.success("Beneficial owner added ✓ (BFIU §4.2)")
      lookup()
    } catch(e) { toast.error("Failed to add BO") }
  }

  const complianceCheck = async () => {
    try {
      const d = await apiFetch(`/api/v1/kyc/beneficial-owner/compliance-status/${sessionId}`)
      toast.success(`BO Compliance: ${d.status || "CHECKED"}`)
    } catch { toast.error("Compliance check failed") }
  }

  const f = k => e => setAddForm(p => ({...p, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value}))

  return (
    <div>
      <div className="page-header">
        <div className="page-title">Beneficial Owner Management</div>
        <div className="page-subtitle">BFIU §4.2 — Identify & verify beneficial owners (≥25% ownership)</div>
      </div>

      <div className="alert alert-info" style={{ marginBottom:16 }}>
        <AlertTriangle size={14} style={{ flexShrink:0 }}/>
        <span>BFIU §4.2: Any person owning ≥25% of a legal entity must be identified and verified. If BO is PEP/IP, EDD is mandatory.</span>
      </div>

      {/* Session lookup */}
      <div className="data-card" style={{ marginBottom:16 }}>
        <div className="data-card-header">
          <span className="data-card-title"><Users size={14}/> Lookup by Session</span>
        </div>
        <div className="data-card-body">
          <div style={{ display:"flex", gap:10 }}>
            <input className="glass-input" value={sessionId}
              onChange={e=>setSessionId(e.target.value)}
              placeholder="Enter KYC session ID" style={{ flex:1 }}/>
            <button className="btn btn-primary btn-md" onClick={lookup} disabled={loading}>
              {loading ? "…" : "Lookup"}
            </button>
            <button className="btn btn-outline btn-md" onClick={complianceCheck}>
              Compliance Check
            </button>
          </div>
          {boData && (
            <div style={{ marginTop:16 }}>
              <div style={{ fontSize:12, fontWeight:700, color:"var(--text3)", marginBottom:8 }}>BENEFICIAL OWNERS</div>
              {(boData.beneficial_owners || boData.owners || [boData]).map((bo,i) => (
                <div key={i} style={{ padding:"12px 14px", background:"var(--bg3)", borderRadius:10, border:"1px solid var(--border)", marginBottom:8 }}>
                  <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                    <div style={{ fontWeight:700, color:"var(--text)" }}>{bo.full_name}</div>
                    <div style={{ display:"flex", gap:8 }}>
                      {bo.is_pep && <span className="badge badge-red">PEP</span>}
                      <span className="badge badge-blue">{bo.ownership_percentage}% ownership</span>
                    </div>
                  </div>
                  <div style={{ fontSize:11, color:"var(--text3)", marginTop:4 }}>
                    NID: {bo.nid_number} · DOB: {bo.date_of_birth} · Relation: {bo.relationship}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add BO */}
      <div className="data-card">
        <div className="data-card-header">
          <span className="data-card-title"><Plus size={14}/> Add Beneficial Owner</span>
          <span className="badge badge-accent">BFIU §4.2</span>
        </div>
        <div className="data-card-body">
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            {[["Full Name *","full_name"],["NID Number *","nid_number"],
              ["Date of Birth","date_of_birth"],["Ownership %","ownership_percentage"],
              ["Relationship","relationship"]].map(([label,key]) => (
              <div key={key}>
                <label className="input-label">{label}</label>
                <input className="glass-input" value={addForm[key]} onChange={f(key)}
                  type={key==="date_of_birth"?"date":key==="ownership_percentage"?"number":"text"}
                  placeholder={label.replace(" *","")}/>
              </div>
            ))}
            <div style={{ display:"flex", alignItems:"center", gap:10, paddingTop:20 }}>
              <input type="checkbox" id="is_pep" checked={addForm.is_pep} onChange={f("is_pep")}/>
              <label htmlFor="is_pep" style={{ fontSize:12, fontWeight:600, color:"var(--text2)" }}>
                Is PEP/IP — triggers EDD (BFIU §4.2)
              </label>
            </div>
          </div>
          <button className="btn btn-primary btn-md" style={{ marginTop:16, width:"100%" }} onClick={addBO}>
            <Plus size={13}/> Add Beneficial Owner
          </button>
        </div>
      </div>
    </div>
  )
}
