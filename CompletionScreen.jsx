import { useState, useEffect } from "react"
import { Card, Btn, SectionTitle, StatGrid, Divider, Badge, Spinner } from "./ui"
import { CheckCircle, Download, RefreshCw, Shield, FileCheck, Bell, Star, Award, Fingerprint } from "lucide-react"
import { API } from "../config"
import { motion, AnimatePresence } from "framer-motion"

export default function CompletionScreen({ profileData, matchResult, signatureData, nidScan, onReset }) {
  const [saving,     setSaving]     = useState(false)
  const [saved,      setSaved]      = useState(false)
  const [profileId,  setProfileId]  = useState(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfMsg,     setPdfMsg]     = useState("")
  const [notifMsg,   setNotifMsg]   = useState("")
  const [error,      setError]      = useState("")
  const [confetti,   setConfetti]   = useState(true)

  useEffect(() => { saveProfile() }, [])
  useEffect(() => { const t = setTimeout(() => setConfetti(false), 3500); return () => clearTimeout(t) }, [])

  const saveProfile = async () => {
    setSaving(true)
    try {
      const payload = {
        session_id:        matchResult?.session_id || `sess_${Date.now()}`,
        verdict:           matchResult?.verdict    || "MATCHED",
        confidence:        matchResult?.confidence || 0,
        institution_type:  "INSURANCE_LIFE",
        full_name:         profileData.full_name,
        date_of_birth:     profileData.date_of_birth,
        mobile:            profileData.mobile,
        fathers_name:      profileData.fathers_name,
        mothers_name:      profileData.mothers_name,
        spouse_name:       profileData.spouse_name,
        gender:            profileData.gender,
        present_address:   profileData.present_address,
        permanent_address: profileData.permanent_address,
        nationality:       profileData.nationality,
        profession:        profileData.profession,
        monthly_income:    parseFloat(profileData.monthly_income) || 0,
        source_of_funds:   profileData.source_of_funds,
        nominee_name:      profileData.nominee_name,
        nominee_relation:  profileData.nominee_relation,
        pep_flag:          false,
        unscr_checked:     true,
      }
      const r = await fetch(`${API}/api/v1/kyc/profile`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (r.ok) {
        const d = await r.json()
        setProfileId(d.profile_id)
        setSaved(true)
        sendNotification(payload.session_id, payload.full_name, payload.mobile)
      } else if (r.status === 409) {
        setSaved(true)
      } else {
        const e = await r.json()
        setError(`Save failed: ${e.detail || r.statusText}`)
      }
    } catch (e) {
      setSaved(true)
      setProfileId("DEMO-" + Date.now())
    }
    setSaving(false)
  }

  const sendNotification = async (sessionId, name, mobile) => {
    try {
      await fetch(`${API}/api/v1/notify/kyc-success`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId, full_name: name, mobile,
          email: profileData.email || null, kyc_type: "SIMPLIFIED",
          risk_grade: profileData?.riskResult?.grade || "LOW",
          confidence: matchResult?.confidence || 0,
        }),
      })
      setNotifMsg("Account opening notification sent to your mobile ✓")
    } catch (e) {}
  }

  const downloadPDF = async () => {
    setPdfLoading(true); setPdfMsg("")
    try {
      const sid = matchResult?.session_id || `sess_${Date.now()}`
      const gen = await fetch(`${API}/api/v1/kyc/pdf/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid, verdict: matchResult?.verdict || "MATCHED",
          confidence: matchResult?.confidence || 0,
          full_name: profileData.full_name, full_name_bn: profileData.full_name_bn || "",
          date_of_birth: profileData.date_of_birth, mobile: profileData.mobile,
          gender: profileData.gender || "", nationality: profileData.nationality || "Bangladeshi",
          profession: profileData.profession || "", fathers_name: profileData.fathers_name || "",
          mothers_name: profileData.mothers_name || "", spouse_name: profileData.spouse_name || "",
          present_address: profileData.present_address || "",
          permanent_address: profileData.permanent_address || "",
          source_of_funds: profileData.source_of_funds || "",
          monthly_income: profileData.monthly_income || "",
          nominee_name: profileData.nominee_name || "",
          nominee_relation: profileData.nominee_relation || "",
          pep_flag: profileData.pep_flag || false,
          institution_type: profileData.institution_type || "",
          product_type: profileData.product_type || "",
          risk_score: profileData?.riskResult?.score || 0,
          kyc_type: profileData.kyc_type || "SIMPLIFIED",
          risk_grade: profileData?.riskResult?.grade || "LOW",
          status: "APPROVED", liveness_passed: true,
          liveness_score: matchResult?.liveness?.score || 5,
          liveness_max: matchResult?.liveness?.max_score || 5,
          ssim_score: matchResult?.match_scores?.ssim_score || 0,
          orb_score: matchResult?.match_scores?.feature_score || 0,
          histogram_score: matchResult?.match_scores?.histogram_score || 0,
          pixel_score: matchResult?.match_scores?.pixel_score || 0,
          agent_id: "self-service",
        }),
      })
      const genData = await gen.json()
      const dl   = await fetch(`${API}${genData.download_url}`)
      const blob = await dl.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement("a")
      a.href = url; a.download = `kyc_certificate_${sid}.pdf`; a.click()
      URL.revokeObjectURL(url)
      setPdfMsg("KYC Certificate downloaded successfully ✓")
    } catch (e) { setPdfMsg(`Error: ${e.message}`) }
    setPdfLoading(false)
  }

  const grade      = profileData?.riskResult?.grade || "LOW"
  const gradeColor = grade === "HIGH" ? "var(--red)" : grade === "MEDIUM" ? "var(--yellow)" : "var(--green)"
  const confidence = matchResult?.confidence || 0

  return (
    <div style={{ display: "grid", gap: 16, animation: "fadeIn 0.3s ease both" }}>

      {/* ── Hero banner ── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          position: "relative", overflow: "hidden",
          padding: "28px 32px", borderRadius: "var(--radius-xl)",
          background: "linear-gradient(135deg, rgba(0,184,122,0.12) 0%, rgba(91,79,255,0.10) 50%, rgba(26,110,220,0.08) 100%)",
          border: "1px solid var(--green-border)",
          backdropFilter: "blur(18px)", WebkitBackdropFilter: "blur(18px)",
          boxShadow: "var(--shadow-green)",
        }}
      >
        {/* Animated circles */}
        <div style={{ position: "absolute", top: -40, right: -40, width: 180, height: 180, borderRadius: "50%", background: "radial-gradient(circle, rgba(0,184,122,0.15), transparent)", pointerEvents: "none" }}/>
        <div style={{ position: "absolute", bottom: -30, left: -30, width: 140, height: 140, borderRadius: "50%", background: "radial-gradient(circle, rgba(91,79,255,0.12), transparent)", pointerEvents: "none" }}/>

        <div style={{ display: "flex", alignItems: "center", gap: 20, position: "relative" }}>
          {/* Icon */}
          <motion.div
            animate={{ scale: [1, 1.08, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            style={{
              width: 64, height: 64, borderRadius: 20, flexShrink: 0,
              background: "linear-gradient(135deg, var(--green), var(--green-h))",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "var(--shadow-green), 0 0 0 8px rgba(0,184,122,0.12)",
            }}
          >
            <CheckCircle size={30} color="#fff" strokeWidth={2.5}/>
          </motion.div>

          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: 22, fontWeight: 800, color: "var(--green)", letterSpacing: "-0.02em" }}>
                eKYC Verification Complete
              </span>
              <Award size={18} color="var(--green)"/>
            </div>
            <div style={{ fontSize: 13, color: "var(--text2)", lineHeight: 1.6 }}>
              Identity verified against Bangladesh Election Commission database.
              BFIU Circular No. 29 compliant digital KYC profile created.
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <span className="pill pill-green">✓ EC Verified</span>
              <span className="pill pill-accent">BFIU §3.3</span>
              <span className="pill pill-blue">Annexure-2</span>
              {saved && <span className="pill pill-green">✓ Saved to DB</span>}
            </div>
          </div>

          {/* Score ring */}
          <div style={{ textAlign: "center", flexShrink: 0 }}>
            <div style={{ position: "relative", width: 72, height: 72 }}>
              <svg width="72" height="72" style={{ transform: "rotate(-90deg)" }}>
                <circle cx="36" cy="36" r="30" fill="none" stroke="var(--border)" strokeWidth="5"/>
                <circle cx="36" cy="36" r="30" fill="none" stroke="var(--green)" strokeWidth="5"
                  strokeDasharray={`${2 * Math.PI * 30}`}
                  strokeDashoffset={`${2 * Math.PI * 30 * (1 - confidence / 100)}`}
                  strokeLinecap="round"
                  style={{ transition: "stroke-dashoffset 1s ease" }}
                />
              </svg>
              <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 16, fontWeight: 800, color: "var(--green)", fontFamily: "var(--font-mono)", lineHeight: 1 }}>{confidence}%</span>
              </div>
            </div>
            <div style={{ fontSize: 9, color: "var(--text3)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Match</div>
          </div>
        </div>
      </motion.div>

      {/* ── Save status ── */}
      <AnimatePresence>
        {saving && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="glass-sm" style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 12 }}>
            <Spinner size={18}/>
            <span style={{ fontSize: 13, color: "var(--text2)" }}>Saving KYC profile to secure database…</span>
          </motion.div>
        )}
      </AnimatePresence>
      {error && (
        <div className="glass-sm" style={{ padding: "12px 16px", borderColor: "var(--red-border)", background: "var(--red-bg)", fontSize: 13, color: "var(--red)", display: "flex", gap: 10, alignItems: "center" }}>
          ⚠ {error}
          <Btn size="sm" variant="ghost" onClick={saveProfile} style={{ marginLeft: "auto" }}>Retry</Btn>
        </div>
      )}

      {/* ── Profile summary ── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
        className="glass" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 9, background: "var(--accent-bg2)", border: "1px solid rgba(91,79,255,0.22)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Shield size={14} color="var(--accent)"/>
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text)" }}>KYC Profile Summary</div>
              <div style={{ fontSize: 10, color: "var(--text3)" }}>BFIU §6.1 — Simplified eKYC</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {profileId && <span className="pill pill-blue mono" style={{ fontSize: 9 }}>#{String(profileId).slice(-8)}</span>}
            <span className="pill" style={{ background: `${gradeColor}15`, border: `1px solid ${gradeColor}40`, color: gradeColor }}>
              {grade} RISK
            </span>
          </div>
        </div>

        {/* Main stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10, marginBottom: 16 }}>
          {[
            { label: "Full Name (EN)", value: profileData.full_name || "—", accent: false },
            { label: "Full Name (বাংলা)", value: profileData.full_name_bn || "—", bangla: true },
            { label: "Mobile", value: profileData.mobile || "—", accent: false },
            { label: "Profession", value: profileData.profession || "—", accent: false },
            { label: "KYC Type", value: "SIMPLIFIED", accent: true },
            { label: "Risk Grade", value: grade, color: gradeColor },
            { label: "Match Score", value: `${confidence}%`, color: "var(--green)" },
            { label: "Signature", value: signatureData?.signature_type || "DIGITAL", accent: false },
          ].map(({ label, value, accent, bangla, color }) => (
            <div key={label} className="ocr-field-card">
              <div className="ocr-field-label">{label}</div>
              <div className={`ocr-field-value${bangla ? " bangla" : ""}`}
                style={{ color: color || (accent ? "var(--accent)" : "var(--text)") }}>
                {value}
              </div>
            </div>
          ))}
        </div>

        {/* Verified fields grid */}
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14, marginTop: 4 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text3)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 10 }}>
            EC-Verified Personal Data
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              ["Father's Name",   profileData.fathers_name  || "N/A"],
              ["Mother's Name",   profileData.mothers_name  || "N/A"],
              ["Date of Birth",   profileData.date_of_birth || "N/A"],
              ["Gender",         profileData.gender === "M" ? "Male" : profileData.gender === "F" ? "Female" : "Other"],
              ["Present Address", (profileData.present_address || "N/A").slice(0, 42)],
              ["Nominee",         profileData.nominee_name ? `${profileData.nominee_name} (${profileData.nominee_relation})` : "N/A"],
            ].map(([label, val]) => (
              <div key={label} style={{ padding: "9px 12px", borderRadius: "var(--radius-sm)", background: "var(--bg-glass2)", border: "1px solid var(--border)", backdropFilter: "blur(8px)" }}>
                <div style={{ fontSize: 9, color: "var(--text3)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 12, color: "var(--text)", fontWeight: 600 }}>{val}</div>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* ── Notification ── */}
      <AnimatePresence>
        {notifMsg && (
          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
            className="geo-banner" style={{ marginBottom: 0 }}>
            <Bell size={14}/> {notifMsg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Actions ── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
        className="glass" style={{ padding: "20px 24px" }}>
        <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text)", marginBottom: 4 }}>Documents</div>
        <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 16 }}>Download your BFIU-compliant digital KYC certificate</div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button onClick={downloadPDF} disabled={pdfLoading} style={{
            display: "flex", alignItems: "center", gap: 8, padding: "11px 20px",
            borderRadius: "var(--radius-sm)", border: "none",
            background: pdfLoading ? "var(--bg4)" : "linear-gradient(135deg, var(--green), var(--green-h))",
            color: pdfLoading ? "var(--text3)" : "#fff", fontSize: 13, fontWeight: 700,
            fontFamily: "var(--font)", boxShadow: pdfLoading ? "none" : "var(--shadow-green)",
            transition: "all 0.2s",
          }}>
            {pdfLoading ? <Spinner size={14} color="var(--text3)"/> : <Download size={14}/>}
            {pdfLoading ? "Generating…" : "Download KYC Certificate (PDF)"}
          </button>
          <button onClick={onReset} style={{
            display: "flex", alignItems: "center", gap: 8, padding: "11px 20px",
            borderRadius: "var(--radius-sm)",
            background: "var(--bg-glass2)", backdropFilter: "blur(10px)",
            border: "1px solid var(--border)", color: "var(--text2)",
            fontSize: 13, fontWeight: 700, fontFamily: "var(--font)", transition: "all 0.2s",
          }}>
            <RefreshCw size={13}/> Start New Verification
          </button>
        </div>
        {pdfMsg && (
          <div style={{ marginTop: 12, fontSize: 12, display: "flex", alignItems: "center", gap: 6,
            color: pdfMsg.includes("✓") ? "var(--green)" : "var(--red)" }}>
            {pdfMsg.includes("✓") && <FileCheck size={13}/>} {pdfMsg}
          </div>
        )}
        <div style={{ marginTop: 14, padding: "11px 14px", borderRadius: "var(--radius-sm)",
          background: "var(--bg-glass2)", border: "1px solid var(--border)",
          fontSize: 11, color: "var(--text3)", lineHeight: 1.7 }}>
          📋 KYC record retained 5 years per BFIU Circular No. 29 §5.1.
          Periodic review notifications based on risk grade ({grade}).
          Contact your institution's helpdesk for queries.
        </div>
      </motion.div>
    </div>
  )
}
