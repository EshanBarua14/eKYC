import { useState, useEffect } from "react"
import { Shield, Sun, Moon, Fingerprint, ChevronRight } from "lucide-react"
import NIDScanner      from "./components/NIDScanner"
import LivenessCapture from "./components/LivenessCapture"
import MatchReport     from "./components/MatchReport"
import { Badge }       from "./components/ui"
import AgentDashboard  from "./components/AgentDashboard"
import AdminConsole         from "./components/AdminConsole"
import ComplianceDashboard  from "./components/ComplianceDashboard"
import "./App.css"

const STEPS = { NID:1, LIVENESS:2, REPORT:3 }
const PORTALS = { CUSTOMER:"customer", AGENT:"agent", ADMIN:"admin", COMPLIANCE:"compliance" }

const STEP_META = [
  { n:1, label:"Scan NID",  desc:"Upload or photograph your NID card" },
  { n:2, label:"Liveness",  desc:"Complete the AI face challenge" },
  { n:3, label:"Report",    desc:"View your verification result" },
]

function StepBar({ current }) {
  return (
    <div className="step-bar">
      {STEP_META.map((s, i) => {
        const done   = current > s.n
        const active = current === s.n
        const pending= current < s.n
        return (
          <div key={s.n} style={{ display:"flex", alignItems:"flex-start", flex: i < STEP_META.length-1 ? 1 : "none" }}>
            <div className="step-node">
              <div className={`step-circle ${done?"step-circle-done":active?"step-circle-active":"step-circle-pending"}`}>
                {done ? "✓" : s.n}
              </div>
              <div>
                <div className="step-label" style={{ color: pending ? "var(--text3)" : "var(--text)" }}>{s.label}</div>
                <div className="step-desc">{s.desc}</div>
              </div>
            </div>
            {i < STEP_META.length-1 && (
              <div className="step-connector">
                <div className={`step-line ${done?"step-line-done":active?"step-line-active":"step-line-pending"}`}/>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function App() {
  const [portal, setPortal] = useState("customer")
  const [theme, setTheme] = useState(() => localStorage.getItem("ekyc-theme") || "light")
  const [step,     setStep]     = useState(STEPS.NID)
  const [nidB64,   setNidB64]   = useState(null)
  const [nidScan,  setNidScan]  = useState(null)
  const [liveB64,  setLiveB64]  = useState(null)
  const [liveness, setLiveness] = useState(null)

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("ekyc-theme", theme)
  }, [theme])

  const onNIDCaptured = (b64, scan) => { setNidB64(b64); setNidScan(scan); setStep(STEPS.LIVENESS) }
  const onLiveness    = (b64, res)  => { setLiveB64(b64); setLiveness(res); setStep(STEPS.REPORT) }
  const reset         = () => { setStep(STEPS.NID); setNidB64(null); setNidScan(null); setLiveB64(null); setLiveness(null) }

  if (portal === PORTALS.COMPLIANCE) {
    return (
      <div data-theme={theme} style={{ fontFamily:'var(--font)' }}>
        <ComplianceDashboard onExit={() => setPortal('customer')} theme={theme} toggleTheme={() => setTheme(t => t==="light"?"dark":"light")} />
      </div>
    )
  }

  if (portal === PORTALS.ADMIN) {
    return (
      <div data-theme={theme} style={{ fontFamily:'var(--font)' }}>
        <AdminConsole onExit={() => setPortal('customer')} theme={theme} toggleTheme={() => setTheme(t => t==="light"?"dark":"light")} />
      </div>
    )
  }

  if (portal === PORTALS.AGENT) {
    return (
      <div data-theme={theme} style={{ fontFamily:'var(--font)' }}>
        <AgentDashboard onExit={() => setPortal('customer')} theme={theme} toggleTheme={() => setTheme(t => t==="light"?"dark":"light")} />
      </div>
    )
  }

  return (
    <div style={{ minHeight:"100vh" }}>

      {/* Header */}
      <header className="app-header">
        <div className="header-inner">
          <div style={{ display:"flex", alignItems:"center", gap:11 }}>
            <div className="logo-mark">
              <Shield size={17} color="#fff" strokeWidth={2.5} style={{ position:"relative", zIndex:1 }}/>
            </div>
            <div>
              <div className="logo-text-primary">Xpert eKYC</div>
              <div className="logo-text-sub">BFIU Circular No. 29</div>
            </div>
          </div>

          <div style={{ display:"flex", alignItems:"center", gap:6, flexWrap:"wrap" }}>
            <div className="api-live">
              <div className="api-live-dot"/>
              <span className="api-live-text">API Live</span>
            </div>

            <button className="portal-btn portal-btn-agent" onClick={() => setPortal(PORTALS.AGENT)}>
              <Fingerprint size={12} strokeWidth={2.5}/> Agent
            </button>
            <button className="portal-btn portal-btn-admin" onClick={() => setPortal(PORTALS.ADMIN)}>
              <Shield size={12} strokeWidth={2.5}/> Admin
            </button>
            <button className="portal-btn portal-btn-compliance" onClick={() => setPortal(PORTALS.COMPLIANCE)}>
              <ChevronRight size={12} strokeWidth={2.5}/> Compliance
            </button>

            <button className="theme-toggle" onClick={() => setTheme(t => t==="light"?"dark":"light")}>
              {theme==="light"
                ? <><Moon size={13} strokeWidth={2}/> Dark</>
                : <><Sun  size={13} strokeWidth={2}/> Light</>}
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">

        {/* Hero */}
        <div style={{ marginBottom:0, animation:"fadeUp 0.25s cubic-bezier(0.34,1.56,0.64,1) both" }}>
          <div className="hero-tag">
            <div className="hero-tag-icon">
              <Fingerprint size={11} color="var(--accent)" strokeWidth={2.5}/>
            </div>
            <span className="hero-tag-text">Face Matching · §3.3 · Liveness · Annexure-2</span>
          </div>
          <h1 className="hero-title">
            NID Face{" "}
            <span className="gradient-text">Verification</span>
          </h1>
          <p className="hero-sub">
            Upload your Bangladesh NID card, complete the AI liveness challenge,
            and receive a full biometric match report compliant with BFIU Circular No.&nbsp;29.
          </p>
        </div>

        <StepBar current={step}/>

        {step === STEPS.NID      && <NIDScanner      onNIDCaptured={onNIDCaptured} />}
        {step === STEPS.LIVENESS && <LivenessCapture onLivenessPassed={onLiveness} />}
        {step === STEPS.REPORT   && <MatchReport     nidB64={nidB64} liveB64={liveB64} livenessResults={liveness} onReset={reset} />}

      </main>
    </div>
  )
}
