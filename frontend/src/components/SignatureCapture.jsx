
import { useState, useRef, useEffect } from "react"
import { Card, Btn, SectionTitle, Badge, Divider } from "./ui"
import { PenLine, Hash, Smartphone, CheckCircle, RotateCcw } from "lucide-react"

const SIG_TYPES = [
  { id:"PIN",        label:"PIN Code",           icon:Hash,       desc:"4-digit PIN — low risk accounts only",     lowRiskOnly:true  },
  { id:"ELECTRONIC", label:"Draw Signature",      icon:PenLine,    desc:"Draw your signature using mouse or touch", lowRiskOnly:false },
  { id:"DIGITAL",    label:"Digital Signature",   icon:Smartphone, desc:"One-Time PIN sent to your mobile",         lowRiskOnly:false },
]

function DrawPad({ onSigned }) {
  const canvasRef = useRef(null)
  const [drawing, setDrawing] = useState(false)
  const [hasMark, setHasMark] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    ctx.fillStyle = "transparent"
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.strokeStyle = "var(--accent)"
    ctx.lineWidth = 2.5
    ctx.lineCap = "round"
    ctx.lineJoin = "round"
  }, [])

  const getPos = (e, canvas) => {
    const rect = canvas.getBoundingClientRect()
    const src = e.touches ? e.touches[0] : e
    return { x: src.clientX - rect.left, y: src.clientY - rect.top }
  }

  const start = (e) => {
    e.preventDefault()
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    const pos = getPos(e, canvas)
    ctx.beginPath()
    ctx.moveTo(pos.x, pos.y)
    setDrawing(true)
    setHasMark(true)
  }

  const draw = (e) => {
    e.preventDefault()
    if (!drawing) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    const pos = getPos(e, canvas)
    ctx.lineTo(pos.x, pos.y)
    ctx.stroke()
  }

  const stop = () => {
    setDrawing(false)
    if (hasMark) {
      const dataUrl = canvasRef.current.toDataURL("image/png")
      onSigned(dataUrl)
    }
  }

  const clear = () => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    setHasMark(false)
    onSigned(null)
  }

  return (
    <div>
      <div style={{ position:"relative", borderRadius:"var(--radius-sm)",
        border:"2px dashed var(--accent)", overflow:"hidden",
        background:"var(--bg3)", cursor:"crosshair" }}>
        <canvas
          ref={canvasRef}
          width={560} height={160}
          style={{ display:"block", width:"100%", height:160, touchAction:"none" }}
          onMouseDown={start} onMouseMove={draw} onMouseUp={stop} onMouseLeave={stop}
          onTouchStart={start} onTouchMove={draw} onTouchEnd={stop}
        />
        {!hasMark && (
          <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center",
            justifyContent:"center", pointerEvents:"none" }}>
            <span style={{ fontSize:13, color:"var(--text4)", fontStyle:"italic" }}>
              Draw your signature here...
            </span>
          </div>
        )}
      </div>
      <div style={{ display:"flex", justifyContent:"flex-end", marginTop:8 }}>
        <Btn size="sm" variant="ghost" onClick={clear}>
          <RotateCcw size={11}/> Clear
        </Btn>
      </div>
    </div>
  )
}

export default function SignatureCapture({ riskGrade = "LOW", onSubmit, onBack }) {
  const [sigType, setSigType]   = useState("PIN")
  const [pin,     setPin]       = useState("")
  const [pin2,    setPin2]      = useState("")
  const [sigData, setSigData]   = useState(null)
  const [otpSent, setOtpSent]   = useState(false)
  const [otp,     setOtp]       = useState("")
  const [err,     setErr]       = useState("")

  const isHighRisk = riskGrade === "HIGH" || riskGrade === "MEDIUM"

  const availableTypes = SIG_TYPES.filter(t =>
    !t.lowRiskOnly || !isHighRisk
  )

  // Force non-PIN for high risk
  useEffect(() => {
    if (isHighRisk && sigType === "PIN") setSigType("ELECTRONIC")
  }, [isHighRisk])

  const validate = () => {
    setErr("")
    if (sigType === "PIN") {
      if (!/^\d{4}$/.test(pin))     { setErr("PIN must be exactly 4 digits"); return false }
      if (pin !== pin2)              { setErr("PINs do not match"); return false }
    }
    if (sigType === "ELECTRONIC" && !sigData) {
      setErr("Please draw your signature above"); return false
    }
    if (sigType === "DIGITAL" && otp.length < 4) {
      setErr("Please enter the OTP sent to your mobile"); return false
    }
    return true
  }

  const handleSubmit = () => {
    if (!validate()) return
    onSubmit({
      signature_type: sigType,
      signature_data: sigType === "PIN" ? pin : sigType === "ELECTRONIC" ? sigData : `OTP:${otp}`,
      risk_grade:     riskGrade,
    })
  }

  return (
    <div style={{ display:"grid", gap:16, animation:"fadeUp 0.25s ease both" }}>
      <Card>
        <SectionTitle sub="BFIU §3.3 Step 4 — Required for all accounts">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <PenLine size={14} color="var(--accent)"/> Signature Capture
          </div>
        </SectionTitle>

        {isHighRisk && (
          <div style={{ padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:14,
            background:"var(--red-bg)", border:"1px solid var(--red-border)",
            fontSize:12, color:"var(--red)", display:"flex", gap:8, alignItems:"center" }}>
            <span style={{ fontSize:14 }}>⚠</span>
            <div>
              <strong>High/Medium Risk Account:</strong> PIN is not permitted.
              Wet or electronic signature is mandatory per BFIU guidelines.
            </div>
          </div>
        )}

        {/* Signature type selector */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10, marginBottom:20 }}>
          {availableTypes.map(t => {
            const Icon = t.icon
            const active = sigType === t.id
            return (
              <button key={t.id} onClick={() => { setSigType(t.id); setErr("") }} style={{
                padding:"12px 10px", borderRadius:"var(--radius-sm)", cursor:"pointer",
                background: active ? "var(--accent-bg2)" : "var(--bg3)",
                border:`2px solid ${active ? "var(--accent)" : "var(--border)"}`,
                display:"flex", flexDirection:"column", alignItems:"center", gap:8,
                transition:"all 0.15s ease", fontFamily:"var(--font)",
              }}>
                <Icon size={20} color={active ? "var(--accent)" : "var(--text3)"} strokeWidth={active ? 2.5 : 1.5}/>
                <div style={{ fontSize:12, fontWeight:700, color: active ? "var(--accent)" : "var(--text)" }}>{t.label}</div>
                <div style={{ fontSize:10, color:"var(--text3)", textAlign:"center", lineHeight:1.4 }}>{t.desc}</div>
              </button>
            )
          })}
        </div>

        <Divider/>

        {/* PIN */}
        {sigType === "PIN" && (
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
            <div>
              <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:4 }}>
                4-Digit PIN
              </label>
              <input type="password" maxLength={4} value={pin} onChange={e=>setPin(e.target.value.replace(/\D/g,""))}
                placeholder="••••"
                style={{ width:"100%", padding:"12px 16px", borderRadius:"var(--radius-sm)",
                  fontSize:24, letterSpacing:"0.5em", textAlign:"center",
                  background:"var(--bg2)", border:"1px solid var(--border)",
                  color:"var(--text)", fontFamily:"var(--font-mono)", outline:"none" }}/>
            </div>
            <div>
              <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:4 }}>
                Confirm PIN
              </label>
              <input type="password" maxLength={4} value={pin2} onChange={e=>setPin2(e.target.value.replace(/\D/g,""))}
                placeholder="••••"
                style={{ width:"100%", padding:"12px 16px", borderRadius:"var(--radius-sm)",
                  fontSize:24, letterSpacing:"0.5em", textAlign:"center",
                  background:"var(--bg2)", border:"1px solid var(--border)",
                  color:"var(--text)", fontFamily:"var(--font-mono)", outline:"none" }}/>
            </div>
            <div style={{ gridColumn:"1/-1", fontSize:11, color:"var(--text3)", padding:"8px 12px",
              background:"var(--bg3)", borderRadius:"var(--radius-xs)", border:"1px solid var(--border)" }}>
              PIN is only permitted for low-risk Simplified eKYC accounts. Choose a PIN you can remember — it will be used for future transaction authentication.
            </div>
          </div>
        )}

        {/* Draw */}
        {sigType === "ELECTRONIC" && (
          <DrawPad onSigned={setSigData}/>
        )}

        {/* OTP Digital */}
        {sigType === "DIGITAL" && (
          <div style={{ display:"grid", gap:12 }}>
            {!otpSent ? (
              <div style={{ textAlign:"center", padding:"20px" }}>
                <div style={{ fontSize:13, color:"var(--text2)", marginBottom:16 }}>
                  A One-Time PIN will be sent to your registered mobile number
                </div>
                <Btn onClick={() => setOtpSent(true)} size="lg">
                  <Smartphone size={14}/> Send OTP to Mobile
                </Btn>
              </div>
            ) : (
              <div>
                <div style={{ padding:"10px 14px", background:"var(--green-bg)",
                  border:"1px solid var(--green-border)", borderRadius:"var(--radius-sm)",
                  fontSize:12, color:"var(--green)", marginBottom:12 }}>
                  ✓ OTP sent to your registered mobile number
                </div>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                  textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:4 }}>
                  Enter OTP
                </label>
                <input value={otp} onChange={e=>setOtp(e.target.value.replace(/\D/g,"").slice(0,6))}
                  placeholder="6-digit OTP"
                  style={{ width:"100%", padding:"12px 16px", borderRadius:"var(--radius-sm)",
                    fontSize:22, letterSpacing:"0.4em", textAlign:"center",
                    background:"var(--bg2)", border:"1px solid var(--border)",
                    color:"var(--text)", fontFamily:"var(--font-mono)", outline:"none" }}/>
                <button onClick={() => setOtpSent(false)}
                  style={{ marginTop:8, fontSize:11, color:"var(--accent)", background:"none",
                    border:"none", cursor:"pointer", fontFamily:"var(--font)" }}>
                  Resend OTP
                </button>
              </div>
            )}
          </div>
        )}

        {err && (
          <div style={{ marginTop:12, padding:"9px 12px", borderRadius:"var(--radius-xs)",
            background:"var(--red-bg)", border:"1px solid var(--red-border)",
            fontSize:12, color:"var(--red)" }}>{err}</div>
        )}
      </Card>

      <div style={{ display:"flex", gap:10 }}>
        <Btn variant="ghost" onClick={onBack} size="lg" style={{ padding:"13px 24px" }}>← Back</Btn>
        <Btn onClick={handleSubmit} size="lg" style={{ flex:1, justifyContent:"center" }}>
          <CheckCircle size={14}/> Confirm Signature & Complete eKYC
        </Btn>
      </div>
    </div>
  )
}
