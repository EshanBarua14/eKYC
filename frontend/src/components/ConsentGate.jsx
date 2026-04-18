
import { useState } from "react"
import { Shield, CheckCircle, XCircle, AlertTriangle, FileText } from "lucide-react"
import { Card, Btn, Badge, Divider } from "./ui"
import { API } from "../config"

const CONSENT_TEXT = `I hereby provide my explicit consent for this institution to verify my identity against the Bangladesh Election Commission (EC) NID database in accordance with BFIU Circular No. 29. I confirm that the information provided is accurate and authorise the retrieval of my demographic profile, including my name, address, and biometric photograph, for the sole purpose of completing this eKYC verification.`

export default function ConsentGate({ sessionId, nidHash, onConsented, onDeclined }) {
  const [checked,  setChecked]  = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [err,      setErr]      = useState("")

  const submit = async () => {
    if (!checked) { setErr("Please read and accept the consent statement to continue."); return }
    setLoading(true); setErr("")
    try {
      const r = await fetch(`${API}/api/v1/consent/record`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id:     sessionId,
          nid_hash:       nidHash || "N/A",
          institution_id: "N/A",
          agent_id:       "self-service",
          channel:        "SELF_SERVICE",
          otp_verified:   false,
        }),
      })
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
      const d = await r.json()
      onConsented(d.consent)
    } catch(e) {
      setErr(`Failed to record consent: ${e.message}`)
    }
    setLoading(false)
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 999,
      background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "24px", animation: "fadeUp 0.2s ease both",
    }}>
      <div style={{
        width: "100%", maxWidth: 520,
        background: "var(--bg2)", borderRadius: "var(--radius)",
        border: "1px solid var(--border)", boxShadow: "var(--shadow)",
        overflow: "hidden",
      }}>
        {/* Header */}
        <div style={{
          background: "linear-gradient(135deg, var(--accent), var(--accent2))",
          padding: "20px 24px", display: "flex", alignItems: "center", gap: 12,
        }}>
          <div style={{ width:40, height:40, borderRadius:12, background:"rgba(255,255,255,0.2)",
            display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
            <Shield size={20} color="#fff" strokeWidth={2.5}/>
          </div>
          <div>
            <div style={{ fontSize:15, fontWeight:800, color:"#fff", lineHeight:1.2 }}>Digital Consent Required</div>
            <div style={{ fontSize:11, color:"rgba(255,255,255,0.8)", marginTop:2 }}>BFIU Circular No. 29 — Section 3.2</div>
          </div>
          <Badge color="green" style={{ marginLeft:"auto" }}>Mandatory</Badge>
        </div>

        <div style={{ padding: "20px 24px" }}>
          {/* What we will access */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize:11, fontWeight:700, color:"var(--text2)", textTransform:"uppercase",
              letterSpacing:"0.06em", marginBottom:8 }}>What this institution will access:</div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
              {[
                ["Full Name",        "From EC database"],
                ["Date of Birth",    "Verified against NID"],
                ["Address",         "Present & permanent"],
                ["NID Photo",       "For face matching"],
                ["Parent Names",    "Father & mother"],
                ["Spouse Name",     "If applicable"],
              ].map(([label, desc]) => (
                <div key={label} style={{ display:"flex", alignItems:"flex-start", gap:7,
                  padding:"7px 10px", background:"var(--bg3)", borderRadius:"var(--radius-xs)",
                  border:"1px solid var(--border)" }}>
                  <CheckCircle size={11} color="var(--green)" strokeWidth={2.5} style={{ flexShrink:0, marginTop:1 }}/>
                  <div>
                    <div style={{ fontSize:11, fontWeight:700, color:"var(--text)" }}>{label}</div>
                    <div style={{ fontSize:10, color:"var(--text3)" }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Divider/>

          {/* Consent text */}
          <div style={{ marginBottom:14 }}>
            <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:8 }}>
              <FileText size={12} color="var(--text3)" strokeWidth={2}/>
              <span style={{ fontSize:11, fontWeight:700, color:"var(--text2)", textTransform:"uppercase", letterSpacing:"0.05em" }}>
                Consent Statement
              </span>
            </div>
            <div style={{
              padding:"12px 14px", background:"var(--bg3)", borderRadius:"var(--radius-sm)",
              border:"1px solid var(--border)", fontSize:12, color:"var(--text2)",
              lineHeight:1.7, maxHeight:100, overflowY:"auto",
            }}>
              {CONSENT_TEXT}
            </div>
          </div>

          {/* Checkbox */}
          <label style={{ display:"flex", alignItems:"flex-start", gap:10, cursor:"pointer", marginBottom:16,
            padding:"12px 14px", borderRadius:"var(--radius-sm)",
            background: checked ? "var(--green-bg)" : "var(--bg3)",
            border:`1px solid ${checked ? "var(--green-border)" : "var(--border)"}`,
            transition:"all 0.2s" }}>
            <div onClick={() => setChecked(c => !c)} style={{
              width:18, height:18, borderRadius:5, flexShrink:0, marginTop:1,
              border:`2px solid ${checked ? "var(--green)" : "var(--border-h)"}`,
              background: checked ? "var(--green)" : "transparent",
              display:"flex", alignItems:"center", justifyContent:"center",
              transition:"all 0.15s", cursor:"pointer",
            }}>
              {checked && <span style={{ color:"#fff", fontSize:11, fontWeight:800, lineHeight:1 }}>✓</span>}
            </div>
            <span style={{ fontSize:12, color:"var(--text)", lineHeight:1.6, fontWeight:checked ? 600 : 400 }}>
              I have read and understood the consent statement above. I voluntarily agree to allow this institution to access my EC NID data for the purpose of eKYC verification.
            </span>
          </label>

          {/* Warning */}
          <div style={{ display:"flex", gap:8, padding:"9px 12px", background:"var(--yellow-bg)",
            border:"1px solid var(--yellow-border)", borderRadius:"var(--radius-xs)", marginBottom:14 }}>
            <AlertTriangle size={13} color="var(--yellow)" strokeWidth={2.5} style={{ flexShrink:0, marginTop:1 }}/>
            <span style={{ fontSize:11, color:"var(--yellow)", lineHeight:1.5 }}>
              Your consent is recorded with timestamp and IP address as required by BFIU Circular No. 29. This record is retained for 5 years.
            </span>
          </div>

          {err && <div style={{ fontSize:12, color:"var(--red)", marginBottom:10 }}>{err}</div>}

          {/* Buttons */}
          <div style={{ display:"flex", gap:10 }}>
            <Btn onClick={submit} loading={loading} disabled={!checked} style={{ flex:1, justifyContent:"center" }}>
              <CheckCircle size={13}/>
              I Consent — Proceed to Verification
            </Btn>
            <Btn variant="ghost" onClick={onDeclined} style={{ padding:"10px 16px" }}>
              <XCircle size={13}/> Decline
            </Btn>
          </div>
        </div>
      </div>
    </div>
  )
}
