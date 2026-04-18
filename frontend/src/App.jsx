import { useState, useEffect } from "react"
import { Shield, Sun, Moon, Fingerprint, ChevronRight } from "lucide-react"
import NIDScanner      from "./components/NIDScanner"
import LivenessCapture from "./components/LivenessCapture"
import MatchReport     from "./components/MatchReport"
import { Badge }       from "./components/ui"
import AgentDashboard  from "./components/AgentDashboard"
import "./App.css"

const STEPS = { NID:1, LIVENESS:2, REPORT:3 }
const PORTALS = { CUSTOMER:"customer", AGENT:"agent" }

const STEP_META = [
  { n:1, label:"Scan NID",  desc:"Upload or photograph your NID card" },
  { n:2, label:"Liveness",  desc:"Complete the AI face challenge" },
  { n:3, label:"Report",    desc:"View your verification result" },
]

function StepBar({ current }) {
  return (
    <div style={{ display:"flex", alignItems:"flex-start", gap:0, margin:"32px 0 40px" }}>
      {STEP_META.map((s, i) => {
        const done    = current > s.n
        const active  = current === s.n
        const pending = current < s.n
        return (
          <div key={s.n} style={{ display:"flex", alignItems:"flex-start", flex: i < STEP_META.length-1 ? 1 : "none" }}>
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:8 }}>
              <div style={{
                width:36, height:36, borderRadius:"50%", flexShrink:0,
                display:"flex", alignItems:"center", justifyContent:"center",
                fontSize:12, fontWeight:700, transition:"all 0.3s",
                background: done ? "var(--green)" : active ? "var(--accent)" : "var(--bg4)",
                color: done || active ? "#fff" : "var(--text3)",
                boxShadow: active ? "0 0 0 4px var(--accent-bg), var(--shadow-accent)" : done ? "0 0 0 4px var(--green-bg)" : "none",
                animation: active ? "glow 2s ease infinite" : "none",
              }}>
                {done ? "✓" : s.n}
              </div>
              <div style={{ textAlign:"center" }}>
                <div style={{ fontSize:12, fontWeight:700, color: pending ? "var(--text3)" : "var(--text)", whiteSpace:"nowrap" }}>{s.label}</div>
                <div style={{ fontSize:10, color:"var(--text3)", marginTop:1, whiteSpace:"nowrap", maxWidth:90 }}>{s.desc}</div>
              </div>
            </div>
            {i < STEP_META.length-1 && (
              <div style={{ flex:1, display:"flex", alignItems:"center", paddingTop:17, margin:"0 8px" }}>
                <div style={{ flex:1, height:2, borderRadius:99, background: done ? "var(--green)" : active ? "linear-gradient(90deg,var(--green),var(--accent))" : "var(--bg4)", transition:"all 0.4s" }} />
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
  const [theme,    setTheme]    = useState("light")
  const [step,     setStep]     = useState(STEPS.NID)
  const [nidB64,   setNidB64]   = useState(null)
  const [nidScan,  setNidScan]  = useState(null)
  const [liveB64,  setLiveB64]  = useState(null)
  const [liveness, setLiveness] = useState(null)

  useEffect(() => { document.documentElement.setAttribute("data-theme", theme) }, [theme])

  const onNIDCaptured = (b64, scan) => { setNidB64(b64); setNidScan(scan); setStep(STEPS.LIVENESS) }
  const onLiveness    = (b64, res)  => { setLiveB64(b64); setLiveness(res); setStep(STEPS.REPORT) }
  const reset         = () => { setStep(STEPS.NID); setNidB64(null); setNidScan(null); setLiveB64(null); setLiveness(null) }

  if (portal === PORTALS.AGENT) {
    return (
      <div data-theme={theme} style={{ fontFamily:'var(--font)' }}>
        <AgentDashboard onExit={() => setPortal('customer')} theme={theme} toggleTheme={() => setTheme(t => t==="light"?"dark":"light")} />
      </div>
    )
  }

  return (
    <div style={{ minHeight:"100vh", background:"var(--bg)", paddingBottom:80 }}>

      {/* Header */}
      <header style={{
        background: "var(--bg2)",
        borderBottom: "1px solid var(--border)",
        position: "sticky", top: 0, zIndex: 100,
        boxShadow: "var(--shadow-sm)",
      }}>
        <div style={{ maxWidth:980, margin:"0 auto", padding:"0 24px", height:60, display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <div style={{
              width:36, height:36, borderRadius:10,
              background:"linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%)",
              display:"flex", alignItems:"center", justifyContent:"center",
              boxShadow:"var(--shadow-accent)",
            }}>
              <Shield size={17} color="#fff" strokeWidth={2.5} />
            </div>
            <div>
              <div style={{ fontSize:14, fontWeight:800, color:"var(--text)", lineHeight:1.1, letterSpacing:"-0.02em" }}>Xpert eKYC</div>
              <div style={{ fontSize:9, color:"var(--text3)", fontWeight:600, letterSpacing:"0.1em", textTransform:"uppercase" }}>BFIU Circular No. 29</div>
            </div>
          </div>

          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <div style={{ display:"flex", alignItems:"center", gap:5, padding:"5px 10px", borderRadius:"var(--radius-xs)", background:"var(--green-bg)", border:"1px solid var(--green-border)" }}>
              <div style={{ width:6, height:6, borderRadius:"50%", background:"var(--green)", animation:"pulse 2s ease infinite" }} />
              <span style={{ fontSize:11, fontWeight:700, color:"var(--green)" }}>API Live</span>
            </div>

            <button onClick={() => setPortal(PORTALS.AGENT)} style={{
              display:'flex', alignItems:'center', gap:6,
              padding:'7px 14px', borderRadius:'var(--radius-sm)',
              background:'var(--accent-bg)', color:'var(--accent)',
              border:'1px solid rgba(99,88,255,0.2)',
              fontFamily:'var(--font)', fontSize:12, fontWeight:700,
              cursor:'pointer', marginRight:6,
            }}>
              Agent Portal
            </button>
            <button onClick={() => setTheme(t => t==="light"?"dark":"light")} style={{
              display:"flex", alignItems:"center", gap:6,
              padding:"7px 12px", borderRadius:"var(--radius-xs)",
              background:"var(--bg3)", border:"1px solid var(--border)",
              cursor:"pointer", fontSize:12, fontWeight:600,
              color:"var(--text2)", fontFamily:"var(--font)",
              transition:"all 0.15s",
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = "var(--border-h)"}
            onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
            >
              {theme==="light"
                ? <><Moon size={13} strokeWidth={2}/> Dark</>
                : <><Sun  size={13} strokeWidth={2}/> Light</>}
            </button>
          </div>
        </div>
      </header>

      <main style={{ maxWidth:980, margin:"0 auto", padding:"40px 24px 0" }}>

        {/* Hero */}
        <div style={{ marginBottom:0, animation:"fadeUp 0.3s ease both" }}>
          <div style={{ display:"flex", alignItems:"center", gap:7, marginBottom:12 }}>
            <div style={{ width:20, height:20, borderRadius:6, background:"var(--accent-bg)", display:"flex", alignItems:"center", justifyContent:"center" }}>
              <Fingerprint size={11} color="var(--accent)" strokeWidth={2.5} />
            </div>
            <span style={{ fontSize:11, color:"var(--accent)", fontWeight:700, letterSpacing:"0.08em", textTransform:"uppercase" }}>
              Face Matching · Section 3.3 · Liveness · Annexure-2
            </span>
          </div>
          <h1 style={{ fontSize:36, fontWeight:800, color:"var(--text)", lineHeight:1.1, marginBottom:10, letterSpacing:"-0.03em" }}>
            NID Face{" "}
            <span style={{ background:"linear-gradient(135deg, var(--accent), var(--accent2))", WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>
              Verification
            </span>
          </h1>
          <p style={{ fontSize:14, color:"var(--text2)", maxWidth:500, lineHeight:1.7 }}>
            Upload your Bangladesh NID card, complete the AI liveness challenge, and receive a full biometric match report compliant with BFIU Circular No.&nbsp;29.
          </p>
        </div>

        <StepBar current={step} />

        {step === STEPS.NID      && <NIDScanner      onNIDCaptured={onNIDCaptured} />}
        {step === STEPS.LIVENESS && <LivenessCapture onLivenessPassed={onLiveness} />}
        {step === STEPS.REPORT   && <MatchReport     nidB64={nidB64} liveB64={liveB64} livenessResults={liveness} onReset={reset} />}

      </main>
    </div>
  )
}
