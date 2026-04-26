import { useState, useEffect } from "react"
import { Shield, Sun, Moon, Fingerprint, LogOut, Menu, X, Bell, ChevronRight } from "lucide-react"
import { Toaster, toast } from "react-hot-toast"
import { motion, AnimatePresence } from "framer-motion"

// ── Existing working components (preserved exactly) ──────────────────────────
import RBACLogin           from "./components/RBACLogin"
import NIDEntry            from "./components/NIDEntry"
import NIDScanner          from "./components/NIDScanner"
import LivenessCapture     from "./components/LivenessCapture"
import MatchReport         from "./components/MatchReport"
import ProfileForm         from "./components/ProfileForm"
import SignatureCapture    from "./components/SignatureCapture"
import CompletionScreen    from "./components/CompletionScreen"
import AgentDashboard      from "./components/AgentDashboard"
import AdminConsole        from "./components/AdminConsole"
import ComplianceDashboard from "./components/ComplianceDashboard"
import SettingsPanel       from "./components/SettingsPanel"
import GlassShell from "./components/GlassShell"
import { AdminShell, AgentShell, ComplianceShell, MakerShell } from "./components/shells"
import "./App.css"

const STEPS = { ENTRY:1, NID:2, LIVENESS:3, REPORT:4, PROFILE:5, SIGNATURE:6, COMPLETE:7 }
const STEP_META = [
  { n:1, label:"NID Entry",  desc:"Enter NID & DOB"           },
  { n:2, label:"Scan NID",   desc:"Upload NID card"            },
  { n:3, label:"Liveness",   desc:"AI face challenge"          },
  { n:4, label:"Verify",     desc:"EC biometric match"         },
  { n:5, label:"Profile",    desc:"Confirm personal info"      },
  { n:6, label:"Signature",  desc:"Sign KYC form"              },
  { n:7, label:"Complete",   desc:"Certificate ready"          },
]

// ── Token decoder ────────────────────────────────────────────────────────────
function decodeRole(token) {
  try {
    if (!token) return null
    const p = JSON.parse(atob(token.split(".")[1]))
    if (p.exp < Math.floor(Date.now() / 1000)) return null
    return (p.role || "").toUpperCase() || null
  } catch { return null }
}

// ── Demo JWT generator (works without backend) ───────────────────────────────
function makeDemoToken(role) {
  const b64 = obj => btoa(JSON.stringify(obj)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=/g,"")
  const now  = Math.floor(Date.now() / 1000)
  const payload = {
    sub: "inst-demo-001", user_id: `demo-${role.toLowerCase()}`,
    role: role.toLowerCase(), tenant_schema: "public",
    exp: now + 86400, iat: now, jti: `demo-${Date.now()}`, type: "access",
  }
  return `${b64({alg:"RS256",typ:"JWT"})}.${b64(payload)}.demo_sig`
}

// ── Enhanced Step Bar ────────────────────────────────────────────────────────
function StepBar({ current }) {
  return (
    <div style={{ display:"flex", alignItems:"flex-start", padding:"0 0 4px", overflowX:"auto", gap:0 }}>
      {STEP_META.map((s, i) => {
        const done   = current > s.n
        const active = current === s.n
        return (
          <div key={s.n} style={{ display:"flex", alignItems:"flex-start", flex: i < STEP_META.length-1 ? 1 : "none", minWidth:0 }}>
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:6, minWidth:56 }}>
              <motion.div
                animate={{ scale: active ? 1.1 : 1 }}
                style={{
                  width:28, height:28, borderRadius:"50%", display:"flex",
                  alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700,
                  background: done ? "var(--green)" : active ? "var(--accent)" : "var(--bg3)",
                  color: done||active ? "#fff" : "var(--text3)",
                  border: `2px solid ${done?"var(--green)":active?"var(--accent)":"var(--border)"}`,
                  boxShadow: active ? "0 0 0 4px rgba(99,88,255,0.15)" : "none",
                  transition: "all 0.3s",
                }}
              >
                {done ? "✓" : s.n}
              </motion.div>
              <div style={{ textAlign:"center" }}>
                <div style={{ fontSize:10, fontWeight:600, color: active?"var(--accent)":done?"var(--green)":"var(--text3)", lineHeight:1.2 }}>{s.label}</div>
              </div>
            </div>
            {i < STEP_META.length-1 && (
              <div style={{ flex:1, marginTop:14, marginLeft:2, marginRight:2 }}>
                <div style={{ height:2, background: done?"var(--green)":active?"rgba(99,88,255,0.4)":"var(--border)", borderRadius:2, transition:"background 0.4s" }}/>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Enhanced Header ──────────────────────────────────────────────────────────
function AppHeader({ theme, toggleTheme, onStaffLogin, userRole, onLogout, userName }) {
  const [notifOpen, setNotifOpen] = useState(false)

  return (
    <header className="app-header" style={{ position:"sticky", top:0, zIndex:100, backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)" }}>
      <div className="header-inner" style={{ maxWidth:1400 }}>
        {/* Logo */}
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:34, height:34, borderRadius:10, background:"linear-gradient(135deg,var(--accent),var(--blue))", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
            <Fingerprint size={16} color="#fff" strokeWidth={2.5}/>
          </div>
          <div>
            <div style={{ fontSize:13, fontWeight:800, color:"var(--text)", lineHeight:1.1 }}>Xpert eKYC</div>
            <div style={{ fontSize:9, color:"var(--text3)", fontWeight:600, letterSpacing:"0.04em" }}>BFIU CIRCULAR NO. 29</div>
          </div>
        </div>

        {/* Right controls */}
        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
          {/* Live indicator */}
          <div style={{ display:"flex", alignItems:"center", gap:5, padding:"4px 10px", borderRadius:20, background:"rgba(16,185,129,0.08)", border:"1px solid rgba(16,185,129,0.2)" }}>
            <span style={{ width:6, height:6, borderRadius:"50%", background:"var(--green)", display:"block", animation:"pulse 2s infinite" }}/>
            <span style={{ fontSize:10, fontWeight:700, color:"var(--green)" }}>API Live</span>
          </div>

          {/* Notifications (logged in only) */}
          {userRole && (
            <div style={{ position:"relative" }}>
              <button onClick={() => setNotifOpen(!notifOpen)} style={{ width:32, height:32, borderRadius:8, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", position:"relative" }}>
                <Bell size={14} color="var(--text2)"/>
                <span style={{ position:"absolute", top:6, right:6, width:6, height:6, borderRadius:"50%", background:"var(--red)", border:"1.5px solid var(--bg)" }}/>
              </button>
              <AnimatePresence>
                {notifOpen && (
                  <motion.div
                    initial={{ opacity:0, y:-8, scale:0.95 }}
                    animate={{ opacity:1, y:0, scale:1 }}
                    exit={{ opacity:0, y:-8, scale:0.95 }}
                    style={{ position:"absolute", right:0, top:40, width:280, background:"var(--bg2)", border:"1px solid var(--border)", borderRadius:12, boxShadow:"var(--shadow)", zIndex:200, overflow:"hidden" }}
                  >
                    <div style={{ padding:"12px 14px", borderBottom:"1px solid var(--border)", fontSize:12, fontWeight:700, color:"var(--text)" }}>Notifications</div>
                    {[
                      { msg:"UNSCR feed updated — 0 new hits", time:"2 min ago", type:"green" },
                      { msg:"EDD case #EDD-001 awaiting review", time:"15 min ago", type:"yellow" },
                      { msg:"Monthly BFIU report generated", time:"1 hour ago", type:"blue" },
                    ].map((n,i) => (
                      <div key={i} style={{ padding:"10px 14px", borderBottom:"1px solid var(--border)", display:"flex", gap:10, alignItems:"flex-start" }}>
                        <span style={{ width:6, height:6, borderRadius:"50%", background:`var(--${n.type})`, marginTop:5, flexShrink:0 }}/>
                        <div>
                          <div style={{ fontSize:11, color:"var(--text)", fontWeight:500 }}>{n.msg}</div>
                          <div style={{ fontSize:10, color:"var(--text3)", marginTop:2 }}>{n.time}</div>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Theme toggle */}
          <button onClick={toggleTheme} style={{ width:32, height:32, borderRadius:8, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer" }}>
            {theme==="light" ? <Moon size={14} color="var(--text2)"/> : <Sun size={14} color="#f59e0b"/>}
          </button>

          {/* Auth button */}
          {userRole ? (
            <div style={{ display:"flex", alignItems:"center", gap:6 }}>
              <div style={{ padding:"5px 10px", borderRadius:8, background:"var(--accent-bg)", border:"1px solid rgba(99,88,255,0.2)", fontSize:11, fontWeight:700, color:"var(--accent)" }}>
                {userRole}
              </div>
              <button onClick={onLogout} style={{ display:"flex", alignItems:"center", gap:5, padding:"5px 10px", borderRadius:8, background:"rgba(239,68,68,0.08)", border:"1px solid rgba(239,68,68,0.2)", color:"var(--red)", fontSize:11, fontWeight:700, cursor:"pointer" }}>
                <LogOut size={11}/> Exit
              </button>
            </div>
          ) : (
            <button onClick={onStaffLogin} className="portal-btn portal-btn-agent" style={{ display:"flex", alignItems:"center", gap:5 }}>
              <Fingerprint size={12} strokeWidth={2.5}/> Staff Login
            </button>
          )}
        </div>
      </div>
    </header>
  )
}

// ── Enhanced Footer ──────────────────────────────────────────────────────────
function AppFooter() {
  return (
    <footer style={{ borderTop:"1px solid var(--border)", padding:"16px 24px", marginTop:40 }}>
      <div style={{ maxWidth:1400, margin:"0 auto", display:"flex", flexWrap:"wrap", alignItems:"center", justifyContent:"space-between", gap:8 }}>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{ width:20, height:20, borderRadius:6, background:"linear-gradient(135deg,var(--accent),var(--blue))", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <Fingerprint size={11} color="#fff" strokeWidth={2.5}/>
          </div>
          <span style={{ fontSize:11, color:"var(--text3)" }}>
            Design &amp; Developed by <strong style={{ color:"var(--accent)" }}>Xpert Fintech Ltd.</strong>
          </span>
        </div>
        <span style={{ fontSize:10, color:"var(--text3)" }}>BFIU Circular No. 29 Compliant · Bangladesh Financial Intelligence Unit</span>
        <span style={{ fontSize:10, color:"var(--text3)" }}>© {new Date().getFullYear()} All rights reserved</span>
      </div>
    </footer>
  )
}

// ── MAKER Dashboard (new) ─────────────────────────────────────────────────────
function MakerDashboard({ onExit, theme, toggleTheme }) {
  const [active, setActive] = useState("submit")
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(false)
  const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"
  const token = localStorage.getItem("ekyc_admin_token") || localStorage.getItem("ekyc_token") || ""

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/maker-checker/pending`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.ok ? r.json() : null).then(d => {
      if (d?.applications) setSubmissions(d.applications)
    }).catch(() => {})
  }, [])

  const nav = [
    { id:"submit",      label:"New Submission", icon:"📝" },
    { id:"queue",       label:"My Queue",        icon:"📋" },
    { id:"approved",    label:"Approved",        icon:"✅" },
    { id:"rejected",    label:"Rejected",        icon:"❌" },
  ]

  return (
    <div style={{ display:"flex", minHeight:"100vh", background:"var(--bg)" }}>
      {/* Sidebar */}
      <div style={{ width:200, background:"var(--bg2)", borderRight:"1px solid var(--border)", display:"flex", flexDirection:"column", height:"100vh", position:"sticky", top:0 }}>
        <div style={{ padding:"18px 16px 14px", borderBottom:"1px solid var(--border)" }}>
          <div style={{ fontSize:13, fontWeight:800, color:"var(--text)" }}>Maker Portal</div>
          <div style={{ fontSize:10, color:"var(--text3)", marginTop:2 }}>Submit KYC for review</div>
        </div>
        <nav style={{ flex:1, padding:"10px 8px" }}>
          {nav.map(n => (
            <button key={n.id} onClick={() => setActive(n.id)} style={{
              width:"100%", display:"flex", alignItems:"center", gap:8, padding:"8px 10px",
              borderRadius:8, marginBottom:2, fontSize:12, fontWeight:active===n.id?700:500,
              background: active===n.id?"var(--accent-bg)":"transparent",
              color: active===n.id?"var(--accent)":"var(--text2)",
              border: active===n.id?"1px solid rgba(99,88,255,0.2)":"1px solid transparent",
              cursor:"pointer", fontFamily:"var(--font)", textAlign:"left",
            }}>
              <span>{n.icon}</span>{n.label}
            </button>
          ))}
        </nav>
        <div style={{ padding:12, borderTop:"1px solid var(--border)" }}>
          <button onClick={onExit} style={{ width:"100%", padding:"7px", borderRadius:8, background:"rgba(239,68,68,0.08)", border:"1px solid rgba(239,68,68,0.2)", color:"var(--red)", fontSize:11, fontWeight:700, cursor:"pointer", fontFamily:"var(--font)", display:"flex", alignItems:"center", justifyContent:"center", gap:5 }}>
            <LogOut size={11}/> Sign Out
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex:1, padding:24, overflowY:"auto" }}>
        <div style={{ marginBottom:20 }}>
          <div style={{ fontSize:20, fontWeight:800, color:"var(--text)" }}>
            {active === "submit" ? "New KYC Submission" : active === "queue" ? "My Submissions" : active === "approved" ? "Approved" : "Rejected"}
          </div>
          <div style={{ fontSize:12, color:"var(--text3)", marginTop:4 }}>BFIU Circular No. 29 — Maker-Checker Workflow</div>
        </div>

        {active === "submit" && (
          <div style={{ maxWidth:600 }}>
            <div style={{ padding:16, background:"var(--blue-bg, rgba(59,130,246,0.08))", borderRadius:12, border:"1px solid rgba(59,130,246,0.2)", marginBottom:20, fontSize:12, color:"var(--text2)" }}>
              📋 As a Maker, submit a KYC profile for Checker review. Fill all required fields per BFIU §6.1/§6.2.
            </div>
            <MakerSubmitForm token={token} apiBase={API_BASE} onSuccess={() => { toast.success("Submission sent for Checker review ✓"); setActive("queue") }}/>
          </div>
        )}

        {active !== "submit" && (
          <SubmissionList
            submissions={submissions.filter(s =>
              active === "queue"    ? ["PENDING","UNDER_REVIEW"].includes(s.status) :
              active === "approved" ? s.status === "APPROVED" :
              s.status === "REJECTED"
            )}
            loading={loading}
          />
        )}
      </div>
    </div>
  )
}

function MakerSubmitForm({ token, apiBase, onSuccess }) {
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
      toast.error("Name, mobile and NID required")
      return
    }
    setLoading(true)
    try {
      const sessionId = `maker-${Date.now()}`
      const res = await fetch(`${apiBase}/api/v1/kyc/profile`, {
        method:"POST",
        headers:{ "Content-Type":"application/json", Authorization:`Bearer ${token}` },
        body: JSON.stringify({
          session_id: sessionId,
          verdict: "REVIEW",
          confidence: 0.5,
          ...form,
          product_amount: parseFloat(form.product_amount) || null,
        })
      })
      if (!res.ok) throw new Error(await res.text())
      onSuccess()
    } catch(e) {
      toast.error(e.message?.slice(0,80) || "Submission failed")
    } finally { setLoading(false) }
  }

  const Field = ({ label, k, type="text", options }) => (
    <div>
      <label style={{ fontSize:11, fontWeight:600, color:"var(--text3)", display:"block", marginBottom:4, textTransform:"uppercase", letterSpacing:"0.05em" }}>{label}</label>
      {type === "select"
        ? <select value={form[k]} onChange={f(k)} style={{ width:"100%", padding:"9px 12px", borderRadius:8, background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontSize:13, outline:"none" }}>
            {options.map(o => <option key={o.v||o} value={o.v||o}>{o.l||o}</option>)}
          </select>
        : <input type={type} value={form[k]} onChange={f(k)} style={{ width:"100%", padding:"9px 12px", borderRadius:8, background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontSize:13, outline:"none", fontFamily:"var(--font)" }}/>
      }
    </div>
  )

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
      <Field label="Full Name *" k="full_name"/>
      <Field label="NID Number *" k="nid_number"/>
      <Field label="Date of Birth *" k="date_of_birth" type="date"/>
      <Field label="Mobile *" k="mobile"/>
      <Field label="Email" k="email" type="email"/>
      <Field label="Nationality" k="nationality"/>
      <Field label="Profession" k="profession"/>
      <Field label="Source of Funds" k="source_of_funds"/>
      <Field label="KYC Type" k="kyc_type" type="select" options={[{v:"SIMPLIFIED",l:"Simplified (§6.1)"},{v:"REGULAR",l:"Regular (§6.2)"}]}/>
      <Field label="Institution Type" k="institution_type" type="select" options={["INSURANCE_LIFE","INSURANCE_NON_LIFE","CMI","BANK","MFI","NBFI"]}/>
      <div style={{ gridColumn:"1/-1" }}>
        <Field label="Present Address" k="present_address"/>
      </div>
      <div style={{ gridColumn:"1/-1" }}>
        <Field label="Permanent Address" k="permanent_address"/>
      </div>
      <Field label="Nominee Name" k="nominee_name"/>
      <Field label="Nominee Relation" k="nominee_relation"/>
      <div style={{ gridColumn:"1/-1", marginTop:8 }}>
        <button onClick={submit} disabled={loading} style={{
          width:"100%", padding:"12px", borderRadius:10,
          background: loading ? "var(--bg3)" : "var(--accent)",
          color: loading ? "var(--text3)" : "#fff",
          border:"none", fontSize:13, fontWeight:700, cursor: loading?"not-allowed":"pointer",
          fontFamily:"var(--font)", display:"flex", alignItems:"center", justifyContent:"center", gap:8,
        }}>
          {loading ? "Submitting…" : <><ChevronRight size={14}/> Submit for Checker Review</>}
        </button>
      </div>
    </div>
  )
}

function SubmissionList({ submissions, loading }) {
  if (loading) return <div style={{ textAlign:"center", padding:40, color:"var(--text3)" }}>Loading…</div>
  if (submissions.length === 0) return (
    <div style={{ textAlign:"center", padding:60, color:"var(--text3)" }}>
      <div style={{ fontSize:32, marginBottom:12 }}>📭</div>
      <div style={{ fontSize:14, fontWeight:600 }}>No submissions found</div>
    </div>
  )
  return (
    <div style={{ display:"grid", gap:10 }}>
      {submissions.map((s,i) => (
        <div key={i} style={{ padding:"14px 18px", background:"var(--bg2)", borderRadius:12, border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div>
            <div style={{ fontSize:13, fontWeight:700, color:"var(--text)" }}>{s.full_name || s.session_id}</div>
            <div style={{ fontSize:11, color:"var(--text3)", marginTop:2 }}>{s.kyc_type} · {s.institution_type} · {s.created_at ? new Date(s.created_at).toLocaleString("en-BD") : "—"}</div>
          </div>
          <span style={{ padding:"4px 10px", borderRadius:20, fontSize:11, fontWeight:700, background: s.status==="APPROVED"?"var(--green-bg,rgba(16,185,129,0.1))":s.status==="REJECTED"?"rgba(239,68,68,0.1)":"var(--accent-bg)", color: s.status==="APPROVED"?"var(--green)":s.status==="REJECTED"?"var(--red)":"var(--accent)" }}>
            {s.status || "PENDING"}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [authToken, setAuthToken] = useState(() =>
    localStorage.getItem("ekyc_admin_token") || localStorage.getItem("ekyc_token") || ""
  )
  const [userRole, setUserRole] = useState(() =>
    decodeRole(localStorage.getItem("ekyc_admin_token") || localStorage.getItem("ekyc_token"))
  )
  const [showLogin,      setShowLogin]      = useState(false)
  const [theme,          setTheme]          = useState(() => localStorage.getItem("ekyc-theme") || "light")
  const [step,           setStep]           = useState(STEPS.ENTRY)
  const [nidEntry,       setNidEntry]       = useState(null)
  const [nidB64,         setNidB64]         = useState(null)
  const [nidScan,        setNidScan]        = useState(null)
  const [liveB64,        setLiveB64]        = useState(null)
  const [liveness,       setLiveness]       = useState(null)
  const [matchResult,    setMatchResult]    = useState(null)
  const [profileData,    setProfileData]    = useState(null)
  const [signatureData,  setSignatureData]  = useState(null)

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("ekyc-theme", theme)
  }, [theme])

  const handleLogin = (token, role) => {
    // If token looks like real JWT try to decode role from it
    let resolvedRole = (role || "").toUpperCase()
    const decoded = decodeRole(token)
    if (decoded) resolvedRole = decoded

    // If backend returned no token (demo mode) generate one
    if (!token || token === "") {
      token = makeDemoToken(resolvedRole)
    }

    localStorage.setItem("ekyc_token", token)
    localStorage.setItem("ekyc_admin_token", token)
    setAuthToken(token)
    setUserRole(resolvedRole)
    setShowLogin(false)
    toast.success(`Welcome — ${resolvedRole} (${token.endsWith("demo_sig") ? "Demo Mode" : "Live"})`)
  }

  const handleLogout = () => {
    localStorage.removeItem("ekyc_admin_token")
    localStorage.removeItem("ekyc_token")
    setAuthToken("")
    setUserRole(null)
    setShowLogin(false)
    toast.success("Signed out successfully")
  }

  const reset = () => {
    setStep(STEPS.ENTRY)
    setNidEntry(null); setNidB64(null); setNidScan(null)
    setLiveB64(null);  setLiveness(null)
    setMatchResult(null); setProfileData(null); setSignatureData(null)
  }

  const toggleTheme = () => setTheme(t => t === "light" ? "dark" : "light")

  const sharedProps = { onExit: handleLogout, theme, toggleTheme }

  // ── Role routing ────────────────────────────────────────────────────────
  if (userRole === "ADMIN") {
    return <AdminShell theme={theme} toggleTheme={toggleTheme} onExit={handleLogout}/>
  }

  if (userRole === "CHECKER" || userRole === "AUDITOR" || userRole === "COMPLIANCE_OFFICER") {
    return <ComplianceShell role={userRole} theme={theme} toggleTheme={toggleTheme} onExit={handleLogout}/>
  }

  if (userRole === "MAKER") {
    return <MakerShell theme={theme} toggleTheme={toggleTheme} onExit={handleLogout}/>
  }

  if (userRole === "AGENT") {
    return <AgentShell theme={theme} toggleTheme={toggleTheme} onExit={handleLogout}/>
  }

  // ── Staff login fullscreen ──────────────────────────────────────────────
  if (showLogin) {
    return (
      <div data-theme={theme}>
        <Toaster position="top-right"/>
        <RBACLogin
          onLogin={handleLogin}
          onCancel={() => setShowLogin(false)}
          makeDemoToken={makeDemoToken}
        />
      </div>
    )
  }

  // ── Public Customer Self-eKYC Portal ────────────────────────────────────
  return (
    <div style={{ minHeight:"100vh", display:"flex", flexDirection:"column" }}>
      <Toaster position="top-right"/>

      <AppHeader
        theme={theme}
        toggleTheme={toggleTheme}
        onStaffLogin={() => setShowLogin(true)}
        userRole={userRole}
        onLogout={handleLogout}
      />

      <main className="app-main" style={{ flex:1 }}>
        {/* Hero */}
        <motion.div
          initial={{ opacity:0, y:16 }}
          animate={{ opacity:1, y:0 }}
          style={{ marginBottom:8 }}
        >
          <div className="hero-tag">
            <div className="hero-tag-icon">
              <Fingerprint size={11} color="var(--accent)" strokeWidth={2.5}/>
            </div>
            <span className="hero-tag-text">BFIU §3.3 · Face Matching · 7-Step eKYC · Annexure-2</span>
          </div>
          <h1 className="hero-title">
            Digital eKYC{" "}
            <span className="gradient-text">Onboarding</span>
          </h1>
          <p className="hero-sub">
            Complete your Bangladesh eKYC in 7 steps — NID entry, card scan, liveness detection,
            EC face verification, personal profile, digital signature, and certificate.
            BFIU Circular No. 29 compliant.
          </p>
        </motion.div>

        <StepBar current={step}/>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity:0, x:12 }}
            animate={{ opacity:1, x:0 }}
            exit={{ opacity:0, x:-12 }}
            transition={{ duration:0.2 }}
          >
            {step === STEPS.ENTRY && (
              <NIDEntry onVerified={(data) => {
                setNidEntry(data)
                setStep(STEPS.NID)
                toast.success("NID verified ✓")
              }}/>
            )}
            {step === STEPS.NID && (
              <NIDScanner
                nidEntry={nidEntry}
                onNIDCaptured={(b64, scan) => {
                  setNidB64(b64); setNidScan(scan)
                  setStep(STEPS.LIVENESS)
                  toast.success("NID card scanned ✓")
                }}
                onBack={() => setStep(STEPS.ENTRY)}
              />
            )}
            {step === STEPS.LIVENESS && (
              <LivenessCapture onLivenessPassed={(b64, res) => {
                setLiveB64(b64); setLiveness(res)
                setStep(STEPS.REPORT)
                toast.success("Liveness check passed ✓")
              }}/>
            )}
            {step === STEPS.REPORT && (
              <MatchReport
                nidB64={nidB64} liveB64={liveB64} livenessResults={liveness}
                onReset={reset}
                onContinue={(result) => {
                  setMatchResult(result)
                  setStep(STEPS.PROFILE)
                  toast.success(`Face match: ${result?.verdict || "MATCHED"} ✓`)
                }}
              />
            )}
            {step === STEPS.PROFILE && (
              <ProfileForm
                nidScan={nidScan} matchResult={matchResult} nidEntry={nidEntry}
                onSubmit={(data) => {
                  setProfileData(data)
                  setStep(STEPS.SIGNATURE)
                  toast.success("Profile saved ✓")
                }}
                onBack={() => setStep(STEPS.REPORT)}
              />
            )}
            {step === STEPS.SIGNATURE && (
              <SignatureCapture
                riskGrade={profileData?.riskResult?.grade || "LOW"}
                onSubmit={(data) => {
                  setSignatureData(data)
                  setStep(STEPS.COMPLETE)
                  toast.success("eKYC complete — notifications dispatched ✓")
                }}
                onBack={() => setStep(STEPS.PROFILE)}
              />
            )}
            {step === STEPS.COMPLETE && (
              <CompletionScreen
                profileData={profileData} matchResult={matchResult}
                signatureData={signatureData} nidScan={nidScan}
                onReset={reset}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      <AppFooter/>
    </div>
  )
}
