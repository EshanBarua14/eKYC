
import { useState } from "react"
import { Card, Btn, SectionTitle, Divider, Badge } from "./ui"
import { User, Phone, MapPin, Users, Briefcase, CheckCircle, AlertCircle } from "lucide-react"

const PROFESSIONS = [
  "Business","Service","Agriculture","Doctor","Engineer","Teacher",
  "Lawyer","Banker","Government Officer","Retired","Student","Housewife",
  "Driver","Laborer","Trader","Other"
]

export default function ProfileForm({ nidScan, matchResult, onSubmit, onBack }) {
  const ec = matchResult?.ec_data || {}
  const ocr = nidScan?.fields || {}

  const [form, setForm] = useState({
    full_name:         ec.full_name_en  || ocr.name_en  || "",
    full_name_bn:      ec.full_name_bn  || ocr.name_bn  || "",
    fathers_name:      ec.fathers_name  || ocr.fathers_name || "",
    mothers_name:      ec.mothers_name  || ocr.mothers_name || "",
    spouse_name:       ec.spouse_name   || "",
    date_of_birth:     ec.date_of_birth || ocr.dob      || "",
    gender:            ec.gender        || "M",
    profession:        "",
    mobile:            "",
    email:             "",
    present_address:   ec.present_address  || ocr.address || "",
    permanent_address: ec.present_address  || ocr.address || "",
    nationality:       "Bangladeshi",
    monthly_income:    "",
    source_of_funds:   "",
    nominee_name:      "",
    nominee_relation:  "",
    nominee_dob:       "",
  })
  const [errors, setErrors] = useState({})

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.full_name.trim())      e.full_name = "Required"
    if (!form.mobile.trim())         e.mobile    = "Required — needed for account notification"
    if (!form.present_address.trim())e.present_address = "Required"
    if (!form.profession)            e.profession = "Required"
    if (form.mobile && !/^01[3-9]\d{8}$/.test(form.mobile))
      e.mobile = "Enter valid Bangladesh mobile number (01XXXXXXXXX)"
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = () => {
    if (validate()) onSubmit(form)
  }

  const Field = ({ label, k, type="text", required, placeholder, readOnly, hint }) => (
    <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
      <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
        textTransform:"uppercase", letterSpacing:"0.05em", display:"flex", alignItems:"center", gap:4 }}>
        {label}
        {required && <span style={{ color:"var(--red)", fontSize:10 }}>*</span>}
        {readOnly && <Badge color="blue" style={{ fontSize:9, padding:"1px 6px" }}>EC Verified</Badge>}
      </label>
      <input
        type={type}
        value={form[k]}
        onChange={e => set(k, e.target.value)}
        readOnly={readOnly}
        placeholder={placeholder || label}
        style={{
          padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13,
          background: readOnly ? "var(--bg3)" : "var(--bg2)",
          border:`1px solid ${errors[k] ? "var(--red)" : "var(--border)"}`,
          color: readOnly ? "var(--text2)" : "var(--text)",
          fontFamily:"var(--font)", outline:"none",
          cursor: readOnly ? "not-allowed" : "text",
        }}
      />
      {errors[k] && <span style={{ fontSize:11, color:"var(--red)" }}>{errors[k]}</span>}
      {hint && !errors[k] && <span style={{ fontSize:10, color:"var(--text3)" }}>{hint}</span>}
    </div>
  )

  return (
    <div style={{ display:"grid", gap:16, animation:"fadeUp 0.25s ease both" }}>
      {/* EC Data Banner */}
      {matchResult && (
        <div style={{ padding:"12px 16px", borderRadius:"var(--radius-sm)",
          background:"var(--green-bg)", border:"1px solid var(--green-border)",
          display:"flex", alignItems:"center", gap:10 }}>
          <CheckCircle size={16} color="var(--green)" strokeWidth={2}/>
          <div>
            <div style={{ fontSize:13, fontWeight:700, color:"var(--green)" }}>
              EC Database Verified — {matchResult.confidence}% match
            </div>
            <div style={{ fontSize:11, color:"var(--text2)", marginTop:1 }}>
              Fields marked EC Verified are pulled from the Election Commission database and cannot be edited.
              Please complete the remaining fields.
            </div>
          </div>
        </div>
      )}

      {/* Personal Info */}
      <Card>
        <SectionTitle sub="BFIU §3.3 Step 3 — OCR-populated, editable">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <User size={14} color="var(--accent)"/> Personal Information
          </div>
        </SectionTitle>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <div style={{ gridColumn:"1/-1" }}>
            <Field label="Full Name (English)" k="full_name" required readOnly={!!ec.full_name_en}/>
          </div>
          <div style={{ gridColumn:"1/-1" }}>
            <Field label="Full Name (Bangla)" k="full_name_bn" placeholder="পূর্ণ নাম" readOnly={!!ec.full_name_bn}/>
          </div>
          <Field label="Father's Name"  k="fathers_name" readOnly={!!ec.fathers_name}/>
          <Field label="Mother's Name"  k="mothers_name" readOnly={!!ec.mothers_name}/>
          <Field label="Spouse Name (if applicable)" k="spouse_name" placeholder="N/A if unmarried"/>
          <Field label="Date of Birth"  k="date_of_birth" type="date" readOnly={!!ec.date_of_birth}/>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
              textTransform:"uppercase", letterSpacing:"0.05em" }}>
              Gender (M/F/T) <span style={{ color:"var(--red)" }}>*</span>
            </label>
            <select value={form.gender} onChange={e=>set("gender",e.target.value)}
              disabled={!!ec.gender}
              style={{ width:"100%", marginTop:4, padding:"9px 12px", borderRadius:"var(--radius-sm)",
                fontSize:13, background:"var(--bg2)", border:"1px solid var(--border)",
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="T">Third Gender</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
              textTransform:"uppercase", letterSpacing:"0.05em" }}>
              Profession <span style={{ color:"var(--red)" }}>*</span>
            </label>
            <select value={form.profession} onChange={e=>set("profession",e.target.value)}
              style={{ width:"100%", marginTop:4, padding:"9px 12px", borderRadius:"var(--radius-sm)",
                fontSize:13, background:"var(--bg2)", border:`1px solid ${errors.profession?"var(--red)":"var(--border)"}`,
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
              <option value="">Select profession...</option>
              {PROFESSIONS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            {errors.profession && <span style={{ fontSize:11, color:"var(--red)" }}>{errors.profession}</span>}
          </div>
        </div>
      </Card>

      {/* Contact */}
      <Card>
        <SectionTitle sub="Required for account opening notification (BFIU mandate)">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <Phone size={14} color="var(--accent)"/> Contact Details
          </div>
        </SectionTitle>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <Field label="Mobile Number" k="mobile" required placeholder="01XXXXXXXXX"
            hint="Must be registered SIM — used for account notification"/>
          <Field label="Email Address" k="email" type="email" placeholder="optional@email.com"
            hint="Optional — used for secondary notification"/>
        </div>
      </Card>

      {/* Address */}
      <Card>
        <SectionTitle sub="OCR-populated from NID — verify and correct if needed">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <MapPin size={14} color="var(--accent)"/> Address
          </div>
        </SectionTitle>
        <div style={{ display:"grid", gap:12 }}>
          <Field label="Present Address" k="present_address" required/>
          <Field label="Permanent Address" k="permanent_address" required
            hint="Must match NID permanent address"/>
          <Field label="Nationality" k="nationality" readOnly/>
        </div>
      </Card>

      {/* Nominee */}
      <Card>
        <SectionTitle sub="Required for insurance products">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <Users size={14} color="var(--accent)"/> Nominee Information
          </div>
        </SectionTitle>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12 }}>
          <Field label="Nominee Name"     k="nominee_name"     placeholder="Full name"/>
          <Field label="Nominee Relation" k="nominee_relation" placeholder="e.g. Wife, Son"/>
          <Field label="Nominee DOB"      k="nominee_dob"      type="date"/>
        </div>
        <div style={{ marginTop:10, padding:"9px 12px", borderRadius:"var(--radius-xs)",
          background:"var(--yellow-bg)", border:"1px solid var(--yellow-border)", fontSize:11, color:"var(--yellow)" }}>
          If nominee is a minor — guardian name, NID, address and relation are required. Agent will complete these fields.
        </div>
      </Card>

      {/* Financial (Regular eKYC) */}
      <Card>
        <SectionTitle sub="Required for Regular eKYC (above BDT thresholds)">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <Briefcase size={14} color="var(--accent)"/> Financial Information
          </div>
        </SectionTitle>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <Field label="Monthly Income (BDT)" k="monthly_income" type="number"
            placeholder="0" hint="Used for risk grading (Annexure-1)"/>
          <Field label="Source of Funds" k="source_of_funds"
            placeholder="e.g. Salary, Business, Remittance"/>
        </div>
      </Card>

      <div style={{ display:"flex", gap:10 }}>
        <Btn variant="ghost" onClick={onBack} size="lg" style={{ padding:"13px 24px" }}>
          ← Back
        </Btn>
        <Btn onClick={handleSubmit} size="lg" style={{ flex:1, justifyContent:"center" }}>
          <CheckCircle size={14}/> Confirm & Continue to Signature
        </Btn>
      </div>
    </div>
  )
}
