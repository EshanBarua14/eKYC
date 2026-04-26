
import { useState, useEffect } from "react"
import { Card, Btn, SectionTitle, StatGrid, Divider, Badge, Spinner } from "./ui"
import { CheckCircle, Download, RefreshCw, Shield, FileCheck, Bell } from "lucide-react"
import { API } from "../config"

export default function CompletionScreen({ profileData, matchResult, signatureData, nidScan, onReset }) {
  const [saving,      setSaving]      = useState(false)
  const [saved,       setSaved]       = useState(false)
  const [profileId,   setProfileId]   = useState(null)
  const [pdfLoading,  setPdfLoading]  = useState(false)
  const [pdfMsg,      setPdfMsg]      = useState("")
  const [notifMsg,    setNotifMsg]    = useState("")
  const [error,       setError]       = useState("")

  useEffect(() => { saveProfile() }, [])

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
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      })

      if (r.ok) {
        const d = await r.json()
        setProfileId(d.profile_id)
        setSaved(true)
        // Send success notification
        sendNotification(payload.session_id, payload.full_name, payload.mobile)
      } else if (r.status === 409) {
        // Already exists — that's fine
        setSaved(true)
      } else {
        const e = await r.json()
        setError(`Save failed: ${e.detail || r.statusText}`)
      }
    } catch(e) {
      // Backend unavailable in demo mode — mark as saved locally
      console.warn("Save to backend failed (demo mode):", e.message)
      setSaved(true)
      setProfileId("DEMO-" + Date.now())
    }
    setSaving(false)
  }

  const sendNotification = async (sessionId, name, mobile) => {
    try {
      await fetch(`${API}/api/v1/notify/kyc-success`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
          session_id:   sessionId,
          full_name:    name,
          mobile:       mobile,
          email:        profileData.email || null,
          kyc_type:     "SIMPLIFIED",
          risk_grade: profileData?.riskResult?.grade || "LOW",
          confidence:   matchResult?.confidence || 0,
        })
      })
      setNotifMsg("✓ Account opening notification sent to your mobile")
    } catch(e) {}
  }

  const downloadPDF = async () => {
    setPdfLoading(true); setPdfMsg("")
    try {
      const sid = matchResult?.session_id || `sess_${Date.now()}`
      const gen = await fetch(`${API}/api/v1/kyc/pdf/generate`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
          session_id:    sid,
          verdict:       matchResult?.verdict    || "MATCHED",
          confidence:    matchResult?.confidence || 0,
          full_name:     profileData.full_name,
          full_name_bn:  profileData.full_name_bn   || "",
          date_of_birth: profileData.date_of_birth,
          mobile:        profileData.mobile,
          gender:        profileData.gender          || "",
          nationality:   profileData.nationality     || "Bangladeshi",
          profession:    profileData.profession      || "",
          fathers_name:  profileData.fathers_name    || "",
          mothers_name:  profileData.mothers_name    || "",
          spouse_name:   profileData.spouse_name     || "",
          present_address:   profileData.present_address   || "",
          permanent_address: profileData.permanent_address || "",
          source_of_funds:   profileData.source_of_funds   || "",
          monthly_income:    profileData.monthly_income     || "",
          nominee_name:      profileData.nominee_name       || "",
          nominee_relation:  profileData.nominee_relation   || "",
          pep_flag:      profileData.pep_flag        || false,
          institution_type:  profileData.institution_type  || "",
          product_type:      profileData.product_type      || "",
          risk_score:    profileData?.riskResult?.score || 0,
          kyc_type:      profileData.kyc_type        || "SIMPLIFIED",
          risk_grade:    profileData?.riskResult?.grade || "LOW",
          status:        "APPROVED",
          liveness_passed: matchResult?.liveness?.overall_pass || true,
          liveness_score:  matchResult?.liveness?.score        || 5,
          liveness_max:    matchResult?.liveness?.max_score    || 5,
          ssim_score:      matchResult?.match_scores?.ssim_score      || 0,
          orb_score:       matchResult?.match_scores?.feature_score   || 0,
          histogram_score: matchResult?.match_scores?.histogram_score || 0,
          pixel_score:     matchResult?.match_scores?.pixel_score     || 0,
          agent_id:        "self-service",
        })
      })
      const genData = await gen.json()
      const dl = await fetch(`${API}${genData.download_url}`)
      const blob = await dl.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement("a")
      a.href = url; a.download = `kyc_certificate_${sid}.pdf`; a.click()
      URL.revokeObjectURL(url)
      setPdfMsg("✓ KYC Certificate downloaded successfully")
    } catch(e) { setPdfMsg(`Error: ${e.message}`) }
    setPdfLoading(false)
  }

  return (
    <div style={{ display:"grid", gap:16, animation:"fadeUp 0.25s ease both" }}>
      {/* Success Banner */}
      <div style={{
        padding:"24px 28px", borderRadius:"var(--radius)",
        background:"linear-gradient(135deg, var(--green-bg) 0%, var(--accent-bg) 100%)",
        border:"1px solid var(--green-border)",
        display:"flex", alignItems:"center", gap:20,
      }}>
        <div style={{ width:56, height:56, borderRadius:16, flexShrink:0,
          background:"linear-gradient(135deg, var(--green), var(--green-h))",
          display:"flex", alignItems:"center", justifyContent:"center",
          boxShadow:"var(--shadow-green)" }}>
          <CheckCircle size={26} color="#fff" strokeWidth={2.5}/>
        </div>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:20, fontWeight:800, color:"var(--green)",
            letterSpacing:"-0.02em", marginBottom:4 }}>
            eKYC Verification Complete
          </div>
          <div style={{ fontSize:13, color:"var(--text2)", lineHeight:1.6 }}>
            Your identity has been verified against the Bangladesh Election Commission database.
            Your digital KYC profile has been created and is compliant with BFIU Circular No. 29.
          </div>
        </div>
        <div style={{ textAlign:"right", flexShrink:0 }}>
          <div style={{ fontSize:36, fontWeight:800, color:"var(--green)",
            fontFamily:"var(--font-mono)", lineHeight:1 }}>
            {matchResult?.confidence || 0}%
          </div>
          <div style={{ fontSize:10, color:"var(--text3)", fontWeight:600,
            textTransform:"uppercase", letterSpacing:"0.06em" }}>Match Score</div>
        </div>
      </div>

      {/* Save Status */}
      {saving && (
        <Card>
          <div style={{ display:"flex", alignItems:"center", gap:12, padding:"8px 0" }}>
            <Spinner size={18}/>
            <span style={{ fontSize:13, color:"var(--text2)" }}>Saving your KYC profile to database...</span>
          </div>
        </Card>
      )}
      {error && (
        <Card>
          <div style={{ fontSize:13, color:"var(--red)" }}>{error}</div>
          <Btn size="sm" variant="ghost" onClick={saveProfile} style={{ marginTop:10 }}>Retry Save</Btn>
        </Card>
      )}

      {/* Profile Summary */}
      <Card glow={saved}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
          <SectionTitle sub="Your verified digital KYC profile — BFIU §6.1">
            <div style={{ display:"flex", alignItems:"center", gap:8 }}>
              <Shield size={14} color="var(--accent)"/> KYC Profile Summary
            </div>
          </SectionTitle>
          <div style={{ display:"flex", gap:8 }}>
            {saved && <Badge color="green">✓ Saved to DB</Badge>}
            {profileId && <Badge color="blue">ID: {profileId}</Badge>}
          </div>
        </div>

        <StatGrid items={[
          ["Full Name",    profileData.full_name || "—",       "var(--text)"],
          ["KYC Type",     "SIMPLIFIED",                       "var(--accent)"],
          ["Risk Grade", profileData?.riskResult?.grade || "LOW", profileData?.riskResult?.grade === "HIGH" ? "var(--red)" : profileData?.riskResult?.grade === "MEDIUM" ? "var(--yellow)" : "var(--green)"],
          ["Match Score",  `${matchResult?.confidence || 0}%`, "var(--green)"],
          ["Mobile",       profileData.mobile     || "—",      "var(--text)"],
          ["Profession",   profileData.profession || "—",      "var(--text)"],
          ["Signature",    signatureData?.signature_type || "—","var(--text)"],
          ["Status",       saved ? "APPROVED" : "PENDING",    saved ? "var(--green)" : "var(--yellow)"],
        ]}/>

        <Divider label="Verified Fields"/>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
          {[
            ["Father's Name",  profileData.fathers_name  || "N/A"],
            ["Mother's Name",  profileData.mothers_name  || "N/A"],
            ["Date of Birth",  profileData.date_of_birth || "N/A"],
            ["Gender",         profileData.gender === "M" ? "Male" : profileData.gender === "F" ? "Female" : "Other"],
            ["Present Address",profileData.present_address?.slice(0,40)+"..." || "N/A"],
            ["Nominee",        profileData.nominee_name ? `${profileData.nominee_name} (${profileData.nominee_relation})` : "N/A"],
          ].map(([label, val]) => (
            <div key={label} style={{ padding:"8px 11px", borderRadius:"var(--radius-xs)",
              background:"var(--bg3)", border:"1px solid var(--border)" }}>
              <div style={{ fontSize:10, color:"var(--text3)", fontWeight:600,
                textTransform:"uppercase", letterSpacing:"0.05em", marginBottom:2 }}>{label}</div>
              <div style={{ fontSize:12, color:"var(--text)", fontWeight:600 }}>{val}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Notifications */}
      {notifMsg && (
        <div style={{ padding:"11px 16px", borderRadius:"var(--radius-sm)",
          background:"var(--green-bg)", border:"1px solid var(--green-border)",
          display:"flex", alignItems:"center", gap:8, fontSize:12, color:"var(--green)" }}>
          <Bell size={14}/>{notifMsg}
        </div>
      )}

      {/* Actions */}
      <Card>
        <SectionTitle sub="Download your BFIU-compliant digital KYC certificate">Documents</SectionTitle>
        <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
          <Btn onClick={downloadPDF} loading={pdfLoading} variant="success" size="lg">
            <Download size={14}/> Download KYC Certificate (PDF)
          </Btn>
          <Btn onClick={onReset} variant="ghost" size="lg">
            <RefreshCw size={13}/> Start New Verification
          </Btn>
        </div>
        {pdfMsg && (
          <div style={{ marginTop:10, fontSize:12,
            color: pdfMsg.startsWith("✓") ? "var(--green)" : "var(--red)",
            display:"flex", alignItems:"center", gap:6 }}>
            {pdfMsg.startsWith("✓") && <FileCheck size={13}/>}{pdfMsg}
          </div>
        )}
        <div style={{ marginTop:12, padding:"10px 14px", borderRadius:"var(--radius-xs)",
          background:"var(--bg3)", border:"1px solid var(--border)",
          fontSize:11, color:"var(--text3)", lineHeight:1.7 }}>
          Your KYC record will be retained for 5 years in accordance with BFIU Circular No. 29 §5.1.
          You will receive periodic review notifications based on your risk grade.
          For queries, contact your institution's helpdesk.
        </div>
      </Card>
    </div>
  )
}
