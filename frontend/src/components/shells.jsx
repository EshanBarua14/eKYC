/**
 * Shell wrappers — connect GlassShell to existing role components
 * Each shell manages activeTab state and passes it to the underlying component
 */
import { useState } from "react"
import { Toaster } from "react-hot-toast"
import GlassShell from "./GlassShell"
import AdminConsole from "./AdminConsole"
import AgentDashboard from "./AgentDashboard"
import AdminDashboard from "../pages/dashboards/AdminDashboard"
import CheckerDashboard from "../pages/dashboards/CheckerDashboard"
import AuditorDashboard from "../pages/dashboards/AuditorDashboard"
import AgentDashboardPage from "../pages/dashboards/AgentDashboard"
import ComplianceDashboard from "../pages/dashboards/ComplianceDashboard"

// ── Admin Shell ──────────────────────────────────────────────────────────────
export function AdminShell({ theme, toggleTheme, onExit }) {
  const [activeTab, setActiveTab] = useState("dashboard")
  // Map GlassShell tabs to AdminConsole tabs
  const tabMap = {
    dashboard:    "dashboard",
    health:       "health",
    institutions: "institutions",
    users:        "users",
    thresholds:   "thresholds",
    webhooks:     "webhooks",
    pep:          "pep",
    auditlogs:    "auditlogs",
    settings:     "settings",
  }
  // Tabs handled by AdminConsole internally
  const ADMIN_CONSOLE_TABS = ["health","institutions","users","thresholds","webhooks","auditlogs","settings","pep"]

  const renderAdminContent = () => {
    if (activeTab === "dashboard")        return <AdminDashboard/>
    if (activeTab === "lifecycle")        return <LifecycleManager/>
    if (activeTab === "screening_manual") return <ScreeningPanel/>
    if (activeTab === "notifications")    return <NotificationCenter/>
    if (activeTab === "pep")              return <PEPManagementPage/>
    // Pass key to force remount when tab changes so useState init picks up new externalTab
    const mappedTab = tabMap[activeTab] || activeTab
    return (
      <AdminConsole
        key={mappedTab}
        onExit={onExit} theme={theme} toggleTheme={toggleTheme}
        externalTab={mappedTab}
        onTabChange={setActiveTab}
      />
    )
  }
  return (
    <GlassShell role="ADMIN" theme={theme} toggleTheme={toggleTheme}
      onExit={onExit} activeTab={activeTab} setActiveTab={setActiveTab}>
      <Toaster position="top-right"/>
      {renderAdminContent()}
    </GlassShell>
  )
}

// ── Agent Shell ──────────────────────────────────────────────────────────────
export function AgentShell({ theme, toggleTheme, onExit }) {
  const [activeTab, setActiveTab] = useState("dashboard")
  const tabMap = {
    dashboard:"dashboard", new:"new", sessions:"sessions",
    search:"search", reports:"reports", profile:"profile",
  }
  const renderAgentContent = () => {
    if (activeTab === "dashboard")                                     return <AgentDashboardPage/>
    if (activeTab === "screening" || activeTab === "screening_manual") return <ScreeningPanel/>
    if (activeTab === "fallback")  return <FallbackKYC/>
    if (activeTab === "risk")      return <RiskEngine/>
    if (activeTab === "search" || activeTab === "reports" || activeTab === "profile" || activeTab === "sessions" || activeTab === "new") {
      const mappedAgentTab = tabMap[activeTab] || activeTab
      return (
        <AgentDashboard
          key={mappedAgentTab}
          onExit={onExit} theme={theme} toggleTheme={toggleTheme}
          externalTab={mappedAgentTab}
          onTabChange={setActiveTab}
        />
      )
    }
    return <AgentDashboardPage/>
  }
  return (
    <GlassShell role="AGENT" theme={theme} toggleTheme={toggleTheme}
      onExit={onExit} activeTab={activeTab} setActiveTab={setActiveTab}>
      <Toaster position="top-right"/>
      {renderAgentContent()}
    </GlassShell>
  )
}

// ── Compliance Shell (CHECKER / AUDITOR / COMPLIANCE_OFFICER) ────────────────
export function ComplianceShell({ role, theme, toggleTheme, onExit }) {
  const [activeTab, setActiveTab] = useState("posture")
  const tabMap = {
    posture:"posture", queues:"queues", edd:"edd",
    screening:"screening", failed:"failed", export:"export",
  }
  const renderCompContent = () => {
    if (activeTab === "screening_manual") return <ScreeningPanel/>
    if (activeTab === "beneficial_owner") return <BeneficialOwner/>
    if (activeTab === "lifecycle")        return <LifecycleManager/>
    if (activeTab === "notifications")    return <NotificationCenter/>
    // Role-specific dashboards for posture/home tab
    if (activeTab === "posture" || activeTab === "dashboard") {
      if (role === "CHECKER")            return <CheckerDashboard/>
      if (role === "AUDITOR")            return <AuditorDashboard/>
      return <ComplianceDashboard role={role} externalTab="posture"/>
    }
    const mappedCompTab = tabMap[activeTab] || activeTab
    return (
      <ComplianceDashboard
        key={mappedCompTab}
        onExit={onExit} theme={theme} toggleTheme={toggleTheme}
        externalTab={mappedCompTab}
        onTabChange={setActiveTab}
        role={role}
      />
    )
  }
  return (
    <GlassShell role={role} theme={theme} toggleTheme={toggleTheme}
      onExit={onExit} activeTab={activeTab} setActiveTab={setActiveTab}>
      <Toaster position="top-right"/>
      {renderCompContent()}
    </GlassShell>
  )
}

// ── Maker Shell ──────────────────────────────────────────────────────────────
export function MakerShell({ theme, toggleTheme, onExit }) {
  const [activeTab, setActiveTab] = useState("dashboard")
  return (
    <GlassShell role="MAKER" theme={theme} toggleTheme={toggleTheme}
      onExit={onExit} activeTab={activeTab} setActiveTab={setActiveTab}>
      <Toaster position="top-right"/>
      <MakerContent activeTab={activeTab} onExit={onExit}/>
    </GlassShell>
  )
}

// ── Maker Content (inline since MakerDashboard is in App.jsx) ────────────────
import { useState as useS, useEffect } from "react"
import { toast } from "react-hot-toast"
import FallbackKYC from "../pages/staff/FallbackKYC"
import BeneficialOwner from "../pages/staff/BeneficialOwner"
import LifecycleManager from "../pages/staff/LifecycleManager"
import ScreeningPanel from "../pages/staff/ScreeningPanel"
import NotificationCenter from "../pages/staff/NotificationCenter"
import RiskEngine from "../pages/staff/RiskEngine"
import { API, getToken, authHeaders, ensureAdminToken } from "../config"
import PEPManagementPage from "../pages/staff/PEPPage"

function MakerContent({ activeTab, onExit }) {
  const [submissions, setSubmissions] = useState([])
  const token = getToken() || localStorage.getItem("ekyc_admin_token") || ""

  useEffect(() => {
    fetch(`${API}/api/v1/kyc/profiles?limit=50`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.profiles) setSubmissions(d.profiles) })
      .catch(() => {})
  }, [activeTab])

  if (activeTab === "submit" || activeTab === "new" || activeTab === "dashboard") {
    return <MakerSubmitView token={token} onSuccess={() => toast.success("Submitted for Checker review ✓")}/>
  }
  const filtered = submissions.filter(s =>
    activeTab === "queue"    ? ["PENDING","EDD_REQUIRED","REVIEW"].includes(s.status) :
    activeTab === "approved" ? s.status === "APPROVED" :
    activeTab === "rejected" ? s.status === "REJECTED" :
    true
  )
  return <SubmissionListView submissions={filtered} title={activeTab}/>
}

function MakerSubmitView({ token, onSuccess }) {
  const [form, setForm] = useState({
    full_name:"", date_of_birth:"", mobile:"", email:"",
    nid_number:"", nationality:"Bangladeshi", profession:"",
    source_of_funds:"", present_address:"", permanent_address:"",
    nominee_name:"", nominee_relation:"", kyc_type:"SIMPLIFIED",
    institution_type:"INSURANCE_LIFE", product_amount:"",
  })
  const [loading, setLoading] = useState(false)
  const f = k => e => setForm(p => ({...p, [k]: e.target.value}))

  const submit = async () => {
    if (!form.full_name || !form.mobile || !form.nid_number) {
      toast.error("Name, mobile and NID are required"); return
    }
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/v1/kyc/profile`, {
        method:"POST",
        headers:{ "Content-Type":"application/json", ...(token ? {Authorization:`Bearer ${token}`} : {}) },
        body: JSON.stringify({
          session_id: `maker-${Date.now()}`,
          verdict: "REVIEW", confidence: 0.5,
          ...form,
          product_amount: parseFloat(form.product_amount)||null,
        })
      })
      if (!res.ok && res.status !== 409) throw new Error(await res.text())
      toast.success("✓ KYC profile submitted for Checker review (BFIU §4.x Maker-Checker)")
      onSuccess()
      setForm(p => ({ ...p, full_name:"", mobile:"", nid_number:"", email:"" }))
    } catch(e) {
      toast.error(e.message?.slice(0,80) || "Submission failed")
    } finally { setLoading(false) }
  }

  const fields = [
    ["Full Name *","full_name","text"], ["NID Number *","nid_number","text"],
    ["Date of Birth *","date_of_birth","date"], ["Mobile *","mobile","text"],
    ["Email","email","email"], ["Nationality","nationality","text"],
    ["Profession","profession","text"], ["Source of Funds","source_of_funds","text"],
  ]

  return (
    <div style={{ maxWidth:700 }}>
      <div className="page-header">
        <div className="page-title">New KYC Submission</div>
        <div className="page-subtitle">BFIU §4.x Maker-Checker workflow — submit for Checker approval</div>
      </div>
      <div className="alert alert-info" style={{ marginBottom:16 }}>
        <span>📋</span>
        <span>As Maker, submit KYC profiles for Checker review. All fields per BFIU §6.1 (Simplified) or §6.2 (Regular).</span>
      </div>
      <div className="data-card">
        <div className="data-card-header">
          <span className="data-card-title">Customer Information</span>
          <span className="badge badge-blue">BFIU §6.1/§6.2</span>
        </div>
        <div className="data-card-body">
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            {fields.map(([label,key,type]) => (
              <div key={key}>
                <label className="input-label">{label}</label>
                <input type={type} value={form[key]} onChange={f(key)}
                  className="glass-input" placeholder={label.replace(" *","")}/>
              </div>
            ))}
            <div style={{ gridColumn:"1/-1" }}>
              <label className="input-label">Present Address</label>
              <input value={form.present_address} onChange={f("present_address")} className="glass-input" placeholder="Present address"/>
            </div>
            <div style={{ gridColumn:"1/-1" }}>
              <label className="input-label">Permanent Address</label>
              <input value={form.permanent_address} onChange={f("permanent_address")} className="glass-input" placeholder="Permanent address"/>
            </div>
            <div>
              <label className="input-label">Nominee Name</label>
              <input value={form.nominee_name} onChange={f("nominee_name")} className="glass-input" placeholder="Nominee full name"/>
            </div>
            <div>
              <label className="input-label">Nominee Relation</label>
              <input value={form.nominee_relation} onChange={f("nominee_relation")} className="glass-input" placeholder="e.g. Spouse, Parent"/>
            </div>
            <div>
              <label className="input-label">KYC Type</label>
              <select value={form.kyc_type} onChange={f("kyc_type")} className="glass-input">
                <option value="SIMPLIFIED">Simplified (§6.1)</option>
                <option value="REGULAR">Regular (§6.2)</option>
              </select>
            </div>
            <div>
              <label className="input-label">Institution Type</label>
              <select value={form.institution_type} onChange={f("institution_type")} className="glass-input">
                {["INSURANCE_LIFE","INSURANCE_NON_LIFE","CMI","BANK","MFI","NBFI"].map(t =>
                  <option key={t} value={t}>{t.replace(/_/g," ")}</option>
                )}
              </select>
            </div>
          </div>
          <div style={{ marginTop:18 }}>
            <button onClick={submit} disabled={loading}
              className={`btn btn-primary btn-lg`} style={{ width:"100%" }}>
              {loading ? "⏳ Submitting…" : "→ Submit for Checker Review"}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function SubmissionListView({ submissions, title }) {
  const statusBadge = (s) => {
    const map = { APPROVED:"badge-green", REJECTED:"badge-red", PENDING:"badge-yellow",
                  EDD_REQUIRED:"badge-red", REVIEW:"badge-yellow" }
    return <span className={`badge ${map[s]||"badge-gray"}`}>{s||"PENDING"}</span>
  }
  return (
    <div>
      <div className="page-header">
        <div className="page-title">{title.charAt(0).toUpperCase()+title.slice(1)} Submissions</div>
        <div className="page-subtitle">{submissions.length} records</div>
      </div>
      <div className="data-card" style={{ padding:0, overflow:"hidden" }}>
        {submissions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <div className="empty-title">No submissions</div>
            <div className="empty-desc">No records found for this filter</div>
          </div>
        ) : (
          <table className="glass-table">
            <thead>
              <tr>
                <th>Name</th><th>KYC Type</th><th>Risk Grade</th>
                <th>Status</th><th>Institution</th><th>Created</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((s,i) => (
                <tr key={i}>
                  <td style={{ fontWeight:600, color:"var(--text)" }}>{s.full_name||"—"}</td>
                  <td><span className="badge badge-blue">{s.kyc_type||"—"}</span></td>
                  <td><span className={`badge ${s.risk_grade==="HIGH"?"badge-red":s.risk_grade==="MEDIUM"?"badge-yellow":"badge-green"}`}>{s.risk_grade||"—"}</span></td>
                  <td>{statusBadge(s.status)}</td>
                  <td style={{ color:"var(--text3)", fontSize:11 }}>{s.institution_type||"—"}</td>
                  <td style={{ color:"var(--text3)", fontSize:11 }}>{s.created_at ? new Date(s.created_at).toLocaleDateString("en-BD") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
