import { useState } from "react"
import { Shield, Eye, EyeOff, Lock, User, AlertCircle, CheckCircle } from "lucide-react"

const API = import.meta.env.VITE_API_URL || ""

const ROLE_CONFIG = {
  ADMIN:   { label:"Admin",       color:"#ef4444", bg:"#fef2f2", desc:"Full system access — institution management, RBAC, audit",  totp:true  },
  CHECKER: { label:"Checker",     color:"#f59e0b", bg:"#fffbeb", desc:"Review & approve KYC onboardings, view audit trail",        totp:true  },
  MAKER:   { label:"Maker",       color:"#3b82f6", bg:"#eff6ff", desc:"Create & submit KYC onboardings for checker review",        totp:false },
  AGENT:   { label:"Field Agent", color:"#10b981", bg:"#f0fdf4", desc:"Conduct face verification & liveness checks in the field",  totp:false },
  AUDITOR: { label:"Auditor",     color:"#8b5cf6", bg:"#f5f3ff", desc:"Read-only access to audit logs and compliance reports",     totp:false },
}

const DEMO_CREDS = {
  ADMIN:   { email:"admin-bypass@demo.ekyc",   password:"AdminDemo@2026",   totp_secret:"JBSWY3DPEHPK3PXP" },
  CHECKER: { email:"checker-bypass@demo.ekyc", password:"DemoChecker@2026", totp_secret:"JBSWY3DPEHPK3PXP" },
  MAKER:   { email:"maker-bypass@demo.ekyc",   password:"DemoMaker@2026"   },
  AGENT:   { email:"agent-bypass@demo.ekyc",   password:"DemoAgent@2026"   },
  AUDITOR: { email:"auditor-bypass@demo.ekyc", password:"DemoAudit@2026"   },
}

async function generateTOTP(secret) {
  const alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
  function base32ToBytes(b32) {
    let bits = 0, val = 0, out = []
    for (const c of b32.toUpperCase().replace(/=+$/, "")) {
      val = (val << 5) | alpha.indexOf(c); bits += 5
      if (bits >= 8) { out.push((val >>> (bits - 8)) & 255); bits -= 8 }
    }
    return new Uint8Array(out)
  }
  const counter = Math.floor(Date.now() / 1000 / 30)
  const buf = new ArrayBuffer(8)
  new DataView(buf).setUint32(4, counter)
  const key = await crypto.subtle.importKey("raw", base32ToBytes(secret),
    { name:"HMAC", hash:"SHA-1" }, false, ["sign"])
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, buf))
  const offset = sig[19] & 0xf
  const code = ((sig[offset] & 0x7f) << 24 | sig[offset+1] << 16 | sig[offset+2] << 8 | sig[offset+3]) % 1000000
  return String(code).padStart(6, "0")
}

export default function RBACLogin({ onLogin, onCancel }) {
  const [selectedRole, setSelectedRole] = useState(null)
  const [email,    setEmail]    = useState("")
  const [password, setPassword] = useState("")
  const [totp,     setTotp]     = useState("")
  const [showPass, setShowPass] = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState("")
  const [success,  setSuccess]  = useState("")

  const fillDemo = (role) => {
    const c = DEMO_CREDS[role]
    setEmail(c.email)
    setPassword(c.password)
    setTotp("")
    setError("")
  }

  const login = async () => {
    if (!email || !password) { setError("Email and password required"); return }
    setLoading(true); setError(""); setSuccess("")
    try {
      const payload = { email, password }
      const rc = ROLE_CONFIG[selectedRole]

      if (rc?.totp) {
        const creds = DEMO_CREDS[selectedRole]
        const code = totp || (creds?.totp_secret ? await generateTOTP(creds.totp_secret) : "")
        if (!code) { setError("TOTP code required for this role"); setLoading(false); return }
        payload.totp_code = code
      }

      const r = await fetch(`${API}/api/v1/auth/token`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      })
      const data = await r.json()

      if (!r.ok) {
        const msg = data?.error?.message || data?.detail?.message || data?.detail || "Login failed"
        setError(typeof msg === "string" ? msg : JSON.stringify(msg))
        setLoading(false); return
      }

      const token = data.access_token || data.token
      const role  = (data.role || "").toUpperCase()

      // Store token
      if (role === "ADMIN") {
        localStorage.setItem("ekyc_admin_token", token)
      } else {
        localStorage.setItem("ekyc_token", token)
      }

      setSuccess(`Logged in as ${role}`)
      setTimeout(() => onLogin(token, role, data), 500)
    } catch(e) {
      setError("Connection error: " + e.message)
    }
    setLoading(false)
  }

  const cfg = selectedRole ? ROLE_CONFIG[selectedRole] : null

  return (
    <div style={{ minHeight:"100vh", background:"var(--bg)", display:"flex", alignItems:"center",
      justifyContent:"center", padding:"24px", fontFamily:"var(--font)" }}>
      <div style={{ width:"100%", maxWidth:480 }}>

        {/* Back to customer portal */}
        {onCancel && (
          <div style={{ marginBottom:16 }}>
            <button onClick={onCancel}
              style={{ fontSize:12, color:"var(--text3)", background:"none", border:"none",
                cursor:"pointer", fontFamily:"var(--font)", padding:"4px 0" }}>
              ← Back to Customer Portal
            </button>
          </div>
        )}

        {/* Header */}
        <div style={{ textAlign:"center", marginBottom:32 }}>
          <div style={{ width:56, height:56, borderRadius:16,
            background:"linear-gradient(135deg,var(--accent),var(--accent2))",
            display:"flex", alignItems:"center", justifyContent:"center",
            margin:"0 auto 16px", boxShadow:"0 8px 24px rgba(99,102,241,0.3)" }}>
            <Shield size={24} color="#fff" strokeWidth={2.5}/>
          </div>
          <h1 style={{ fontSize:24, fontWeight:800, color:"var(--text)", margin:0 }}>Xpert eKYC</h1>
          <p style={{ fontSize:13, color:"var(--text3)", marginTop:4 }}>BFIU Circular No. 29 — Staff Portal</p>
        </div>

        {/* Step 1: Role selector */}
        {!selectedRole ? (
          <div>
            <p style={{ fontSize:12, fontWeight:700, color:"var(--text2)", textAlign:"center",
              textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:16 }}>
              Select your role to continue
            </p>
            <div style={{ display:"grid", gap:10 }}>
              {Object.entries(ROLE_CONFIG).map(([role, c]) => (
                <button key={role} onClick={() => { setSelectedRole(role); fillDemo(role) }}
                  style={{ padding:"14px 18px", borderRadius:12, border:`1.5px solid ${c.color}22`,
                    background:c.bg, cursor:"pointer", textAlign:"left",
                    display:"flex", alignItems:"center", gap:14, transition:"all 0.15s",
                    fontFamily:"var(--font)" }}>
                  <div style={{ width:40, height:40, borderRadius:10, background:c.color+"22",
                    display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
                    <Shield size={18} color={c.color} strokeWidth={2.2}/>
                  </div>
                  <div style={{ flex:1 }}>
                    <div style={{ fontSize:14, fontWeight:700, color:c.color }}>{c.label}</div>
                    <div style={{ fontSize:11, color:"var(--text3)", marginTop:2 }}>{c.desc}</div>
                  </div>
                  {c.totp && (
                    <div style={{ fontSize:9, fontWeight:700, padding:"2px 6px",
                      background:c.color+"22", color:c.color, borderRadius:4 }}>2FA</div>
                  )}
                </button>
              ))}
            </div>
          </div>

        ) : (
          /* Step 2: Credentials form */
          <div style={{ background:"var(--bg2)", borderRadius:16, border:"1px solid var(--border)", padding:24 }}>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20 }}>
              <button onClick={() => { setSelectedRole(null); setError("") }}
                style={{ fontSize:12, color:"var(--text3)", background:"none", border:"none",
                  cursor:"pointer", fontFamily:"var(--font)", padding:"4px 0" }}>
                ← Back
              </button>
              <div style={{ fontSize:12, fontWeight:700, padding:"4px 12px", borderRadius:99,
                background:cfg.color+"22", color:cfg.color }}>
                {cfg.label}
              </div>
            </div>

            {/* Email */}
            <div style={{ marginBottom:14 }}>
              <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>Email</label>
              <div style={{ position:"relative" }}>
                <User size={14} color="var(--text3)" style={{ position:"absolute", left:12, top:"50%", transform:"translateY(-50%)" }}/>
                <input value={email} onChange={e=>setEmail(e.target.value)}
                  placeholder="staff@institution.com"
                  style={{ width:"100%", padding:"10px 12px 10px 36px", borderRadius:8, boxSizing:"border-box",
                    background:"var(--bg3)", border:"1px solid var(--border)", fontSize:13,
                    color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}/>
              </div>
            </div>

            {/* Password */}
            <div style={{ marginBottom:14 }}>
              <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>Password</label>
              <div style={{ position:"relative" }}>
                <Lock size={14} color="var(--text3)" style={{ position:"absolute", left:12, top:"50%", transform:"translateY(-50%)" }}/>
                <input value={password} onChange={e=>setPassword(e.target.value)}
                  type={showPass ? "text" : "password"} placeholder="••••••••"
                  onKeyDown={e=>e.key==="Enter"&&login()}
                  style={{ width:"100%", padding:"10px 38px 10px 36px", borderRadius:8, boxSizing:"border-box",
                    background:"var(--bg3)", border:"1px solid var(--border)", fontSize:13,
                    color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}/>
                <button onClick={()=>setShowPass(s=>!s)}
                  style={{ position:"absolute", right:10, top:"50%", transform:"translateY(-50%)",
                    background:"none", border:"none", cursor:"pointer", color:"var(--text3)" }}>
                  {showPass ? <EyeOff size={14}/> : <Eye size={14}/>}
                </button>
              </div>
            </div>

            {/* TOTP (admin & checker only) */}
            {cfg.totp && (
              <div style={{ marginBottom:14 }}>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                  textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                  TOTP Code{" "}
                  <span style={{ fontSize:10, color:"var(--text3)", fontWeight:400 }}>(leave blank — auto-filled in demo)</span>
                </label>
                <input value={totp} onChange={e=>setTotp(e.target.value)}
                  placeholder="6-digit code" maxLength={6}
                  style={{ width:"100%", padding:"10px 12px", borderRadius:8, boxSizing:"border-box",
                    background:"var(--bg3)", border:"1px solid var(--border)", fontSize:13,
                    color:"var(--text)", fontFamily:"var(--font-mono,monospace)", outline:"none",
                    letterSpacing:"0.2em" }}/>
              </div>
            )}

            {error && (
              <div style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 12px",
                borderRadius:8, background:"#fef2f2", border:"1px solid #fecaca",
                marginBottom:14, fontSize:12, color:"#dc2626" }}>
                <AlertCircle size={14}/>{error}
              </div>
            )}
            {success && (
              <div style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 12px",
                borderRadius:8, background:"#f0fdf4", border:"1px solid #bbf7d0",
                marginBottom:14, fontSize:12, color:"#16a34a" }}>
                <CheckCircle size={14}/>{success}
              </div>
            )}

            <button onClick={login} disabled={loading}
              style={{ width:"100%", padding:"12px", borderRadius:8, border:"none",
                background: loading ? "var(--text3)" : cfg.color,
                color:"#fff", fontSize:14, fontWeight:700,
                cursor: loading ? "not-allowed" : "pointer",
                fontFamily:"var(--font)", transition:"all 0.15s" }}>
              {loading ? "Signing in…" : `Sign in as ${cfg.label}`}
            </button>

            <div style={{ marginTop:12, padding:"10px 12px", borderRadius:8,
              background:"var(--bg3)", border:"1px solid var(--border)", fontSize:11, color:"var(--text3)" }}>
              <strong style={{ color:"var(--text2)" }}>Demo credentials auto-filled.</strong>{" "}
              In production, use institution-issued credentials.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
