import { useState } from "react"
import { Card, Btn, SectionTitle, Badge } from "./ui"
import { User, Phone, MapPin, Users, Briefcase, CheckCircle, AlertCircle, ShieldAlert } from "lucide-react"

const API = import.meta.env.VITE_API_URL || ""

const PROFESSIONS = [
  "Business","Service","Agriculture","Doctor","Engineer","Teacher",
  "Lawyer","Banker","Government Officer","Retired","Student","Housewife",
  "Driver","Laborer","Trader","Other"
]

// Maps ProfileForm profession strings → risk engine keys
const PROFESSION_MAP = {
  "Business":           "BUSINESS_OWNER",
  "Service":            "OTHER",
  "Agriculture":        "OTHER",
  "Doctor":             "DOCTOR",
  "Engineer":           "ENGINEER",
  "Teacher":            "TEACHER",
  "Lawyer":             "LAWYER",
  "Banker":             "BANKER",
  "Government Officer": "GOVERNMENT_EMPLOYEE",
  "Retired":            "RETIRED",
  "Student":            "STUDENT",
  "Housewife":          "HOUSEWIFE",
  "Driver":             "OTHER",
  "Laborer":            "OTHER",
  "Trader":             "WHOLESALE",
  "Other":              "OTHER",
}

// Standalone Field — defined OUTSIDE ProfileForm to avoid remount on every keystroke
function Field({ label, k, type="text", required, placeholder, readOnly, hint, form, errors, onChange }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
      <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
        textTransform:"uppercase", letterSpacing:"0.05em", display:"flex", alignItems:"center", gap:4 }}>
        {label}
        {required && <span style={{ color:"var(--red)", fontSize:10 }}>*</span>}
        {readOnly && <Badge color="blue" style={{ fontSize:9, padding:"1px 6px" }}>EC Verified</Badge>}
      </label>
      <input
        type={type}
        value={form[k] ?? ""}
        onChange={e => onChange(k, e.target.value)}
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
}

const GRADE_COLOR = { HIGH:"var(--red)", MEDIUM:"var(--yellow)", LOW:"var(--green)" }
const GRADE_BG    = { HIGH:"#fef2f2",    MEDIUM:"#fffbeb",       LOW:"#f0fdf4"      }
const GRADE_BORDER= { HIGH:"#fecaca",    MEDIUM:"#fde68a",       LOW:"#bbf7d0"      }

export default function ProfileForm({ nidScan, matchResult, nidEntry, onSubmit, onBack }) {
  const ec = matchResult?.ec_data || matchResult?.ec_result?.ec_data || nidEntry?.ecResult?.ec_data || {}
  const f0 = nidScan?.fields || {}

  const [form, setForm] = useState(() => ({
    full_name:         ec.full_name_en      || f0.full_name_en    || f0.name_en  || f0.name  || "",
    full_name_bn:      ec.full_name_bn      || f0.full_name_bn    || f0.name_bn  || "",
    fathers_name:      ec.fathers_name      || f0.fathers_name_en || f0.father_name || f0.fathers_name || "",
    mothers_name:      ec.mothers_name      || f0.mothers_name_en || f0.mother_name || f0.mothers_name || "",
    spouse_name:       ec.spouse_name       || f0.spouse_name     || "",
    date_of_birth:     ec.date_of_birth     || f0.date_of_birth   || f0.dob      || "",
    gender:            ec.gender            || f0.gender          || "M",
    profession:        "",
    mobile:            f0.mobile            || "",
    email:             f0.email             || "",
    present_address:   ec.present_address   || f0.present_address || f0.address  || "",
    permanent_address: ec.permanent_address || f0.permanent_address || f0.address || "",
    nationality:       ec.nationality       || f0.nationality     || "Bangladeshi",
    monthly_income:    "",
    source_of_funds:   "",
    nominee_name:      "",
    nominee_relation:  "",
    nominee_dob:       "",
    // Risk grading fields
    institution_type:   "CMI",
    onboarding_channel: "AGENCY",
    residency:          "RESIDENT",
    pep_flag:           false,
    adverse_media:      false,
    product_type:       "BO_ACCOUNT",
    deposit_amount:     "",
  }))

  const [errors,     setErrors]     = useState({})
  const [grading,    setGrading]    = useState(false)
  const [riskResult, setRiskResult] = useState(null)
  const [riskError,  setRiskError]  = useState("")

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.full_name.trim())       e.full_name       = "Required"
    if (!form.mobile.trim())          e.mobile          = "Required"
    if (!form.present_address.trim()) e.present_address = "Required"
    if (!form.profession)             e.profession      = "Required"
    if (!form.source_of_funds.trim()) e.source_of_funds = "Required for BFIU AML compliance"
    if (form.mobile && !/^01[3-9]\d{8}$/.test(form.mobile))
      e.mobile = "Enter valid Bangladesh mobile number (01XXXXXXXXX)"
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const callRiskAPI = async () => {
    const token = localStorage.getItem("ekyc_token") || localStorage.getItem("ekyc_admin_token")
    if (!token) return null

    const annual = parseFloat(form.monthly_income || 0) * 12
    const payload = {
      kyc_profile_id:     `sess-${Date.now()}`,
      institution_type:   form.institution_type,
      onboarding_channel: form.onboarding_channel,
      residency:          form.residency,
      pep_ip_status:      form.pep_flag ? "PEP" : "NONE",
      product_type:       form.product_type,
      business_type:      "OTHER",
      profession:         PROFESSION_MAP[form.profession] || "OTHER",
      annual_income_bdt:  annual,
      source_of_funds:    form.source_of_funds || null,
      pep_flag:           form.pep_flag,
      adverse_media:      form.adverse_media,
    }

    const r = await fetch(`${API}/api/v1/risk/grade`, {
      method: "POST",
      headers: { "Content-Type":"application/json", "Authorization":`Bearer ${token}` },
      body: JSON.stringify(payload),
    })
    if (!r.ok) return null
    return await r.json()
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setGrading(true); setRiskError("")
    try {
      const result = await callRiskAPI()
      if (result) {
        setRiskResult(result)
        onSubmit({ ...form, riskResult: result })
      } else {
        // Fallback: compute locally if API unavailable
        const fallback = { grade:"LOW", total_score:0, edd_required:false, review_years:5 }
        setRiskResult(fallback)
        onSubmit({ ...form, riskResult: fallback })
      }
    } catch {
      setRiskError("Risk grading failed — using fallback LOW grade")
      onSubmit({ ...form, riskResult:{ grade:"LOW", total_score:0, edd_required:false, review_years:5 } })
    }
    setGrading(false)
  }

  const grade = riskResult?.grade

  return (
    <div style={{ display:"grid", gap:16, animation:"fadeUp 0.25s ease both" }}>

      {/* EC Banner */}
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
              EC Verified fields are locked. Complete remaining fields to calculate BFIU risk grade.
            </div>
          </div>
        </div>
      )}

      {/* Live risk result banner */}
      {riskResult && (
        <div style={{ padding:"14px 16px", borderRadius:"var(--radius-sm)",
          background: GRADE_BG[grade], border:`1px solid ${GRADE_BORDER[grade]}`,
          display:"flex", alignItems:"center", gap:12 }}>
          <ShieldAlert size={20} color={GRADE_COLOR[grade]}/>
          <div style={{ flex:1 }}>
            <div style={{ fontSize:14, fontWeight:800, color:GRADE_COLOR[grade] }}>
              Risk Grade: {grade} — Score {riskResult.total_score} / {riskResult.thresholds?.high || 15}
            </div>
            <div style={{ fontSize:11, color:"var(--text2)", marginTop:2 }}>
              KYC Type: {grade === "LOW" ? "Simplified eKYC" : "Regular eKYC (detailed review required)"}
              {" · "}Periodic review every {riskResult.review_years} year{riskResult.review_years > 1 ? "s" : ""}
              {riskResult.edd_required && " · ⚠️ EDD mandatory — Chief AML Officer notified"}
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
            <Field label="Full Name (English)" k="full_name" required readOnly={!!ec.full_name_en}
              form={form} errors={errors} onChange={set}/>
          </div>
          <div style={{ gridColumn:"1/-1" }}>
            <Field label="Full Name (Bangla)" k="full_name_bn" placeholder="পূর্ণ নাম" readOnly={!!ec.full_name_bn}
              form={form} errors={errors} onChange={set}/>
          </div>
          <Field label="Father's Name"  k="fathers_name" readOnly={!!ec.fathers_name}
            form={form} errors={errors} onChange={set}/>
          <Field label="Mother's Name"  k="mothers_name" readOnly={!!ec.mothers_name}
            form={form} errors={errors} onChange={set}/>
          <Field label="Spouse Name (if applicable)" k="spouse_name" placeholder="N/A if unmarried"
            form={form} errors={errors} onChange={set}/>
          <Field label="Date of Birth" k="date_of_birth" type="date" readOnly={!!ec.date_of_birth}
            form={form} errors={errors} onChange={set}/>
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
              textTransform:"uppercase", letterSpacing:"0.05em" }}>Gender *</label>
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
            hint="Must be registered SIM" form={form} errors={errors} onChange={set}/>
          <Field label="Email Address" k="email" type="email" placeholder="optional@email.com"
            form={form} errors={errors} onChange={set}/>
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
          <Field label="Present Address"   k="present_address"   required form={form} errors={errors} onChange={set}/>
          <Field label="Permanent Address" k="permanent_address" required
            hint="Must match NID permanent address" form={form} errors={errors} onChange={set}/>
          <Field label="Nationality" k="nationality" readOnly form={form} errors={errors} onChange={set}/>
        </div>
      </Card>

      {/* Nominee */}
      <Card>
        <SectionTitle sub="Required for insurance and investment products">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <Users size={14} color="var(--accent)"/> Nominee Information
          </div>
        </SectionTitle>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12 }}>
          <Field label="Nominee Name"     k="nominee_name"     placeholder="Full name"
            form={form} errors={errors} onChange={set}/>
          <Field label="Nominee Relation" k="nominee_relation" placeholder="e.g. Wife, Son"
            form={form} errors={errors} onChange={set}/>
          <Field label="Nominee DOB"      k="nominee_dob"      type="date"
            form={form} errors={errors} onChange={set}/>
        </div>
        <div style={{ marginTop:10, padding:"9px 12px", borderRadius:"var(--radius-sm)",
          background:"var(--yellow-bg)", border:"1px solid var(--yellow-border)", fontSize:11, color:"var(--yellow)" }}>
          If nominee is a minor — guardian name, NID, address and relation are required. Agent will complete these fields.
        </div>
      </Card>

      {/* Financial + Risk Grading */}
      <Card>
        <SectionTitle sub="BFIU Annexure-1 — Required for risk grade calculation">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <Briefcase size={14} color="var(--accent)"/> Financial & Risk Information
          </div>
        </SectionTitle>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <Field label="Monthly Income (BDT)" k="monthly_income" type="number"
            placeholder="0" hint="Annual = monthly × 12, used for risk scoring"
            form={form} errors={errors} onChange={set}/>
          <Field label="Source of Funds" k="source_of_funds" required
            placeholder="e.g. Salary, Business, Remittance"
            hint="Required — BFIU AML compliance" form={form} errors={errors} onChange={set}/>
          <Field label="Initial Deposit / Investment Amount (BDT)" k="deposit_amount" type="number"
            placeholder="0" hint="≤15 lakh = Simplified eKYC, above = Regular eKYC"
            form={form} errors={errors} onChange={set}/>

          {/* Institution type */}
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
              textTransform:"uppercase", letterSpacing:"0.05em" }}>Institution Type *</label>
            <select value={form.institution_type} onChange={e=>set("institution_type",e.target.value)}
              style={{ width:"100%", marginTop:4, padding:"9px 12px", borderRadius:"var(--radius-sm)",
                fontSize:13, background:"var(--bg2)", border:"1px solid var(--border)",
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
              <option value="CMI">Capital Market (Stock Broker / DP)</option>
              <option value="BANK">Bank / NBFI</option>
              <option value="INSURANCE">Insurance Company</option>
              <option value="MFS">Mobile Financial Services</option>
            </select>
          </div>

          {/* Product type */}
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
              textTransform:"uppercase", letterSpacing:"0.05em" }}>Product Type *</label>
            <select value={form.product_type} onChange={e=>set("product_type",e.target.value)}
              style={{ width:"100%", marginTop:4, padding:"9px 12px", borderRadius:"var(--radius-sm)",
                fontSize:13, background:"var(--bg2)", border:"1px solid var(--border)",
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
              <optgroup label="Capital Market">
                <option value="BO_ACCOUNT">BO Account (Individual)</option>
                <option value="MARGIN_ACCOUNT">Margin Account</option>
                <option value="DISCRETIONARY">Discretionary Portfolio</option>
                <option value="TRADING">Trading Account</option>
              </optgroup>
              <optgroup label="Bank">
                <option value="SAVINGS">Savings Account</option>
                <option value="CURRENT">Current Account</option>
                <option value="FDR">Fixed Deposit (FDR)</option>
              </optgroup>
              <optgroup label="Insurance">
                <option value="ORDINARY_LIFE">Ordinary Life</option>
                <option value="TERM">Term Insurance</option>
                <option value="HEALTH">Health Insurance</option>
                <option value="GROUP">Group Insurance</option>
              </optgroup>
            </select>
          </div>

          {/* Onboarding channel */}
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
              textTransform:"uppercase", letterSpacing:"0.05em" }}>Onboarding Channel *</label>
            <select value={form.onboarding_channel} onChange={e=>set("onboarding_channel",e.target.value)}
              style={{ width:"100%", marginTop:4, padding:"9px 12px", borderRadius:"var(--radius-sm)",
                fontSize:13, background:"var(--bg2)", border:"1px solid var(--border)",
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
              <option value="AGENCY">Agency / Field Agent</option>
              <option value="WALK_IN">Walk-in Branch</option>
              <option value="DIGITAL_DIRECT">Digital / Self-Service</option>
              <option value="BANK">Bank Channel</option>
              <option value="DSA">Direct Sales Agent (DSA)</option>
              <option value="BRANCH_RM">Branch RM</option>
            </select>
          </div>

          {/* Residency */}
          <div>
            <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
              textTransform:"uppercase", letterSpacing:"0.05em" }}>Residency Status *</label>
            <select value={form.residency} onChange={e=>set("residency",e.target.value)}
              style={{ width:"100%", marginTop:4, padding:"9px 12px", borderRadius:"var(--radius-sm)",
                fontSize:13, background:"var(--bg2)", border:"1px solid var(--border)",
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
              <option value="RESIDENT">Resident Bangladeshi</option>
              <option value="NRB">Non-Resident Bangladeshi (NRB)</option>
              <option value="FOREIGN">Foreign National</option>
            </select>
          </div>
        </div>

        {/* PEP / Adverse Media flags */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginTop:14,
          padding:"12px", borderRadius:"var(--radius-sm)",
          background:"var(--bg3)", border:"1px solid var(--border)" }}>
          <label style={{ display:"flex", alignItems:"center", gap:10, cursor:"pointer", fontSize:13 }}>
            <input type="checkbox" checked={form.pep_flag}
              onChange={e=>set("pep_flag",e.target.checked)}
              style={{ width:16, height:16, accentColor:"var(--red)" }}/>
            <div>
              <div style={{ fontWeight:700, color:"var(--text)" }}>PEP / IP Flag</div>
              <div style={{ fontSize:10, color:"var(--text3)" }}>Politically Exposed Person or Influential Person — forces HIGH risk + EDD</div>
            </div>
          </label>
          <label style={{ display:"flex", alignItems:"center", gap:10, cursor:"pointer", fontSize:13 }}>
            <input type="checkbox" checked={form.adverse_media}
              onChange={e=>set("adverse_media",e.target.checked)}
              style={{ width:16, height:16, accentColor:"var(--red)" }}/>
            <div>
              <div style={{ fontWeight:700, color:"var(--text)" }}>Adverse Media</div>
              <div style={{ fontSize:10, color:"var(--text3)" }}>Negative news / sanction list hit — forces HIGH risk + EDD</div>
            </div>
          </label>
        </div>

        {riskError && (
          <div style={{ display:"flex", gap:8, alignItems:"center", marginTop:10,
            padding:"9px 12px", borderRadius:"var(--radius-sm)",
            background:"#fef2f2", border:"1px solid #fecaca", fontSize:12, color:"#dc2626" }}>
            <AlertCircle size={13}/>{riskError}
          </div>
        )}
      </Card>

      <div style={{ display:"flex", gap:10 }}>
        <Btn variant="ghost" onClick={onBack} size="lg" style={{ padding:"13px 24px" }}>
          ← Back
        </Btn>
        <Btn onClick={handleSubmit} size="lg" disabled={grading}
          style={{ flex:1, justifyContent:"center", opacity: grading ? 0.7 : 1 }}>
          {grading
            ? <><span style={{ marginRight:6 }}>⏳</span>Calculating Risk Grade…</>
            : <><CheckCircle size={14}/> Calculate Risk Grade & Continue</>}
        </Btn>
      </div>
    </div>
  )
}
