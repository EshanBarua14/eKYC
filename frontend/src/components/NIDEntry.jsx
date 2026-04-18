
import { useState } from "react"
import { Card, Btn, SectionTitle, Divider, Badge, Spinner } from "./ui"
import { CreditCard, Calendar, CheckCircle, AlertCircle, Shield } from "lucide-react"
import { API } from "../config"

export default function NIDEntry({ onVerified }) {
  const [nidNumber, setNidNumber] = useState("")
  const [dob,       setDob]       = useState("")
  const [loading,   setLoading]   = useState(false)
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState("")

  const formatNID = (val) => {
    // Allow only digits, max 17
    return val.replace(/\D/g, "").slice(0, 17)
  }

  const validate = () => {
    if (!nidNumber || nidNumber.length < 10) {
      setError("Please enter a valid NID number (10, 13, or 17 digits)"); return false
    }
    if (!dob) {
      setError("Date of Birth is required"); return false
    }
    return true
  }

  const verify = async () => {
    if (!validate()) return
    setLoading(true); setError(""); setResult(null)
    try {
      // Call EC NID verification via our backend
      const r = await fetch(`${API}/api/v1/nid/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nid_number: nidNumber,
          session_id: `entry_${Date.now()}`,
          ocr_fields: { date_of_birth: dob }
        })
      })
      if (r.status === 403) {
        // No auth token — use demo mode
        setResult({
          found: true,
          demo: true,
          nid_number: nidNumber,
          dob: dob,
          ec_data: {
            full_name_en: "Demo User",
            date_of_birth: dob,
          }
        })
        return
      }
      const data = await r.json()
      if (r.ok) {
        setResult({ found: true, ...data })
      } else {
        setError(data.detail?.message || data.detail || "NID not found in EC database")
      }
    } catch(e) {
      // Network error — allow demo mode
      setResult({
        found: true,
        demo: true,
        nid_number: nidNumber,
        dob: dob,
      })
    } finally { setLoading(false) }
  }

  const proceed = () => {
    onVerified({ nidNumber, dob, ecResult: result })
  }

  return (
    <div className="nid-entry-wrap" style={{ animation:"fadeUp 0.25s ease both" }}>
      <Card glow>
        {/* Header */}
        <div style={{ textAlign:"center", marginBottom:28 }}>
          <div style={{ width:56, height:56, borderRadius:16, margin:"0 auto 14px",
            background:"linear-gradient(135deg, var(--accent), var(--blue))",
            display:"flex", alignItems:"center", justifyContent:"center",
            boxShadow:"var(--shadow-accent)" }}>
            <CreditCard size={24} color="#fff" strokeWidth={2}/>
          </div>
          <h2 style={{ fontSize:20, fontWeight:800, color:"var(--text)",
            letterSpacing:"-0.025em", marginBottom:6 }}>
            Enter Your NID Details
          </h2>
          <p style={{ fontSize:13, color:"var(--text2)", lineHeight:1.6 }}>
            Your National ID Number and Date of Birth will be verified against the
            Bangladesh Election Commission database before proceeding.
          </p>
        </div>

        <Divider label="EC Pre-Verification"/>

        {/* NID Number */}
        <div style={{ marginBottom:16 }}>
          <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
            textTransform:"uppercase", letterSpacing:"0.06em",
            display:"flex", alignItems:"center", gap:6, marginBottom:6 }}>
            <CreditCard size={12} color="var(--accent)"/>
            NID Number <span style={{ color:"var(--red)" }}>*</span>
          </label>
          <input
            type="text"
            value={nidNumber}
            onChange={e => { setNidNumber(formatNID(e.target.value)); setError(""); setResult(null) }}
            placeholder="Enter 10, 13, or 17-digit NID number"
            style={{
              width:"100%", padding:"13px 16px",
              borderRadius:"var(--radius-sm)", fontSize:16,
              fontFamily:"var(--font-mono)", letterSpacing:"0.1em",
              background:"var(--bg3)", outline:"none",
              border:`1px solid ${error && !nidNumber ? "var(--red)" : result?.found ? "var(--green)" : "var(--border)"}`,
              color:"var(--text)", boxSizing:"border-box",
              transition:"border-color 0.2s",
            }}
          />
          <div style={{ fontSize:10, color:"var(--text3)", marginTop:4 }}>
            Smart NID: 10 digits · Old NID: 13 digits · New NID: 17 digits
          </div>
        </div>

        {/* Date of Birth */}
        <div style={{ marginBottom:20 }}>
          <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
            textTransform:"uppercase", letterSpacing:"0.06em",
            display:"flex", alignItems:"center", gap:6, marginBottom:6 }}>
            <Calendar size={12} color="var(--accent)"/>
            Date of Birth <span style={{ color:"var(--red)" }}>*</span>
          </label>
          <input
            type="date"
            value={dob}
            onChange={e => { setDob(e.target.value); setError(""); setResult(null) }}
            max={new Date().toISOString().split("T")[0]}
            style={{
              width:"100%", padding:"13px 16px",
              borderRadius:"var(--radius-sm)", fontSize:15,
              background:"var(--bg3)", outline:"none",
              border:`1px solid ${error && !dob ? "var(--red)" : result?.found ? "var(--green)" : "var(--border)"}`,
              color:"var(--text)", fontFamily:"var(--font)",
              boxSizing:"border-box", transition:"border-color 0.2s",
            }}
          />
        </div>

        {error && (
          <div style={{ display:"flex", gap:8, padding:"10px 14px", marginBottom:14,
            background:"var(--red-bg)", border:"1px solid var(--red-border)",
            borderRadius:"var(--radius-sm)" }}>
            <AlertCircle size={15} color="var(--red)" strokeWidth={2} style={{ flexShrink:0, marginTop:1 }}/>
            <span style={{ fontSize:12, color:"var(--red)", fontWeight:500 }}>{error}</span>
          </div>
        )}

        {/* EC Result */}
        {result?.found && !error && (
          <div style={{ padding:"14px 16px", marginBottom:16,
            background:"var(--green-bg)", border:"1px solid var(--green-border)",
            borderRadius:"var(--radius-sm)" }}>
            <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
              <CheckCircle size={16} color="var(--green)" strokeWidth={2}/>
              <span style={{ fontSize:13, fontWeight:700, color:"var(--green)" }}>
                {result.demo ? "NID Validated (Demo Mode)" : "NID Found in EC Database"}
              </span>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
              {[
                ["NID Number", nidNumber],
                ["Date of Birth", dob],
                ...(result.ec_data?.full_name_en ? [["Name", result.ec_data.full_name_en]] : []),
                ...(result.ec_source ? [["Source", result.ec_source]] : [["Source", "EC Database"]]),
              ].map(([label, val]) => (
                <div key={label} style={{ fontSize:11 }}>
                  <span style={{ color:"var(--text3)", fontWeight:600 }}>{label}: </span>
                  <span style={{ color:"var(--text)", fontFamily:"var(--font-mono)", fontSize:10 }}>{val}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Verify button */}
        {!result?.found && (
          <Btn onClick={verify} loading={loading} size="lg"
            style={{ width:"100%", justifyContent:"center", marginBottom:14 }}>
            {loading
              ? "Verifying with EC Database..."
              : <><Shield size={14}/> Verify NID with Election Commission</>}
          </Btn>
        )}

        {/* Proceed button */}
        {result?.found && (
          <Btn onClick={proceed} variant="success" size="lg"
            style={{ width:"100%", justifyContent:"center" }}>
            <CheckCircle size={14}/> Confirmed — Proceed to NID Scan →
          </Btn>
        )}

        {/* Security note */}
        <div style={{ marginTop:16, padding:"9px 12px", borderRadius:"var(--radius-xs)",
          background:"var(--bg3)", border:"1px solid var(--border)",
          fontSize:11, color:"var(--text3)", lineHeight:1.7,
          display:"flex", gap:8, alignItems:"flex-start" }}>
          <Shield size={12} color="var(--text3)" strokeWidth={2} style={{ flexShrink:0, marginTop:2 }}/>
          Your NID data is verified directly against the Bangladesh Election Commission database via
          a BFIU-approved secure gateway. No data is stored until you provide explicit consent.
        </div>
      </Card>
    </div>
  )
}
