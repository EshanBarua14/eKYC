import { useState } from "react"
import { Card, Btn, SectionTitle, Badge, Spinner } from "./ui"
import { User, Phone, MapPin, Users, Briefcase, CheckCircle, AlertCircle, ShieldAlert, Fingerprint, Globe } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

const API = import.meta.env.VITE_API_URL || ""

const PROFESSIONS = [
  "Business","Service","Agriculture","Doctor","Engineer","Teacher",
  "Lawyer","Banker","Government Officer","Retired","Student","Housewife",
  "Driver","Laborer","Trader","Other"
]

const PROFESSION_MAP = {
  "Business":"BUSINESS_OWNER","Service":"OTHER","Agriculture":"OTHER",
  "Doctor":"DOCTOR","Engineer":"ENGINEER","Teacher":"TEACHER",
  "Lawyer":"LAWYER","Banker":"BANKER","Government Officer":"GOVERNMENT_EMPLOYEE",
  "Retired":"RETIRED","Student":"STUDENT","Housewife":"HOUSEWIFE",
  "Driver":"OTHER","Laborer":"OTHER","Trader":"WHOLESALE","Other":"OTHER",
}

const GRADE_COLOR  = { HIGH:"var(--red)",    MEDIUM:"var(--yellow)",  LOW:"var(--green)" }
const GRADE_BG     = { HIGH:"var(--red-bg)", MEDIUM:"var(--yellow-bg)",LOW:"var(--green-bg)" }
const GRADE_BORDER = { HIGH:"var(--red-border)",MEDIUM:"var(--yellow-border)",LOW:"var(--green-border)" }

// ── Glass Input Field ─────────────────────────────────────────────────────
function GlassField({ label, k, type="text", required, placeholder, readOnly, hint, form, errors, onChange, icon }) {
  const hasError = !!errors[k]
  const hasValue = !!(form[k] && String(form[k]).trim())
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
      <label style={{ fontSize:10, fontWeight:700, color:"var(--text3)", textTransform:"uppercase",
        letterSpacing:"0.06em", display:"flex", alignItems:"center", gap:5 }}>
        {icon && <span style={{ opacity:0.7 }}>{icon}</span>}
        {label}
        {required && <span style={{ color:"var(--red)" }}>*</span>}
        {readOnly && <span className="pill pill-blue" style={{ fontSize:8, padding:"1px 6px" }}>EC Verified</span>}
      </label>
      <input
        type={type}
        value={form[k] ?? ""}
        onChange={e => onChange(k, e.target.value)}
        readOnly={readOnly}
        placeholder={placeholder || label}
        className={`glass-input ${hasError ? "validation-err" : hasValue && !readOnly ? "validation-ok" : ""}`}
        style={{ cursor: readOnly ? "not-allowed" : "text",
          background: readOnly ? "var(--bg-glass3)" : undefined,
          color: readOnly ? "var(--text2)" : undefined }}
      />
      {hasError && (
        <span className="validation-msg validation-msg-err">
          <AlertCircle size={11}/> {errors[k]}
        </span>
      )}
      {hint && !hasError && (
        <span style={{ fontSize:10, color:"var(--text3)", paddingLeft:2 }}>{hint}</span>
      )}
    </div>
  )
}

// ── Glass Select Field ────────────────────────────────────────────────────
function GlassSelect({ label, k, required, options, form, errors, onChange, icon }) {
  const hasError = !!errors[k]
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
      <label style={{ fontSize:10, fontWeight:700, color:"var(--text3)", textTransform:"uppercase",
        letterSpacing:"0.06em", display:"flex", alignItems:"center", gap:5 }}>
        {icon && <span style={{ opacity:0.7 }}>{icon}</span>}
        {label}
        {required && <span style={{ color:"var(--red)" }}>*</span>}
      </label>
      <select
        value={form[k] ?? ""}
        onChange={e => onChange(k, e.target.value)}
        className={`glass-input ${hasError ? "validation-err" : ""}`}
        style={{ appearance:"none" }}
      >
        <option value="">Select {label}</option>
        {options.map(o => <option key={o.v||o} value={o.v||o}>{o.l||o}</option>)}
      </select>
      {hasError && <span className="validation-msg validation-msg-err"><AlertCircle size={11}/> {errors[k]}</span>}
    </div>
  )
}

// ── OCR Preview Card ──────────────────────────────────────────────────────
function OCRPreview({ nidScan }) {
  const f = nidScan?.fields || {}
  if (!f.full_name_en && !f.full_name_bn && !f.nid_number) return null
  return (
    <motion.div initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }}
      className="glass-sm" style={{ padding:"14px 16px", marginBottom:4,
        borderLeft:"3px solid var(--accent)", borderRadius:"var(--radius-sm)" }}>
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
        <Fingerprint size={13} color="var(--accent)"/>
        <span style={{ fontSize:11, fontWeight:800, color:"var(--accent)", textTransform:"uppercase", letterSpacing:"0.06em" }}>
          NID OCR — Auto-populated Fields
        </span>
        <span className="pill pill-green" style={{ marginLeft:"auto", fontSize:9 }}>
          {nidScan?.ocr_mode === "mock" ? "Demo" : "Live OCR"}
        </span>
      </div>
      <div className="ocr-field-grid" style={{ gridTemplateColumns:"repeat(auto-fill, minmax(160px,1fr))" }}>
        {f.full_name_en && (
          <div className="ocr-field-card">
            <div className="ocr-field-label">Name (English)</div>
            <div className="ocr-field-value">{f.full_name_en}</div>
          </div>
        )}
        {f.full_name_bn && (
          <div className="ocr-field-card">
            <div className="ocr-field-label">নাম (বাংলা)</div>
            <div className="ocr-field-value bangla">{f.full_name_bn}</div>
          </div>
        )}
        {f.nid_number && (
          <div className="ocr-field-card">
            <div className="ocr-field-label">NID Number</div>
            <div className="ocr-field-value mono">{f.nid_number}</div>
          </div>
        )}
        {f.date_of_birth && (
          <div className="ocr-field-card">
            <div className="ocr-field-label">Date of Birth</div>
            <div className="ocr-field-value">{f.date_of_birth}</div>
          </div>
        )}
        {f.fathers_name_en && (
          <div className="ocr-field-card">
            <div className="ocr-field-label">Father's Name</div>
            <div className="ocr-field-value">{f.fathers_name_en}</div>
          </div>
        )}
        {f.mothers_name_en && (
          <div className="ocr-field-card">
            <div className="ocr-field-label">Mother's Name</div>
            <div className="ocr-field-value">{f.mothers_name_en}</div>
          </div>
        )}
        {f.blood_group && (
          <div className="ocr-field-card">
            <div className="ocr-field-label">Blood Group</div>
            <div className="ocr-field-value" style={{ color:"var(--red)", fontWeight:800 }}>{f.blood_group}</div>
          </div>
        )}
        {f.address && (
          <div className="ocr-field-card" style={{ gridColumn:"span 2" }}>
            <div className="ocr-field-label">Address</div>
            <div className="ocr-field-value">{f.address}</div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ── Section Header ────────────────────────────────────────────────────────
function SectionHdr({ icon, title, subtitle }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:14, paddingBottom:10,
      borderBottom:"1px solid var(--border)" }}>
      <div style={{ width:34, height:34, borderRadius:10, background:"var(--accent-bg2)",
        border:"1px solid rgba(91,79,255,0.22)", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize:13, fontWeight:800, color:"var(--text)" }}>{title}</div>
        {subtitle && <div style={{ fontSize:10, color:"var(--text3)", marginTop:1 }}>{subtitle}</div>}
      </div>
    </div>
  )
}

// ── Risk Grade Badge ──────────────────────────────────────────────────────
function RiskBadge({ riskResult }) {
  if (!riskResult) return null
  const g = riskResult.grade || "LOW"
  return (
    <motion.div initial={{ opacity:0, scale:0.9 }} animate={{ opacity:1, scale:1 }}
      style={{ padding:"16px 20px", borderRadius:"var(--radius)", marginTop:4,
        background: GRADE_BG[g], border:`1px solid ${GRADE_BORDER[g]}`,
        backdropFilter:"blur(10px)" }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <ShieldAlert size={20} color={GRADE_COLOR[g]}/>
          <div>
            <div style={{ fontSize:14, fontWeight:800, color:GRADE_COLOR[g] }}>
              {g} RISK — Score {riskResult.score || 0}/100
            </div>
            <div style={{ fontSize:11, color:"var(--text3)", marginTop:2 }}>
              BFIU §6.3 — 7-dimension risk assessment complete
            </div>
          </div>
        </div>
        <span className="pill" style={{ background:`${GRADE_COLOR[g]}15`, border:`1px solid ${GRADE_COLOR[g]}40`,
          color:GRADE_COLOR[g], fontSize:11, fontWeight:800 }}>
          {g}
        </span>
      </div>
      {riskResult.factors && (
        <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginTop:10 }}>
          {Object.entries(riskResult.factors).map(([k,v]) => (
            <span key={k} style={{ fontSize:9, fontWeight:700, padding:"2px 8px", borderRadius:99,
              background:"var(--bg-glass2)", border:"1px solid var(--border)", color:"var(--text3)" }}>
              {k}: {v}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  )
}

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
      e.mobile = "Valid Bangladesh mobile required (01XXXXXXXXX)"
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const callRiskAPI = async () => {
    const token = localStorage.getItem("ekyc_token") || localStorage.getItem("ekyc_admin_token")
    if (!token) return null
    const annual = parseFloat(form.monthly_income || 0) * 12
    const r = await fetch(`${API}/api/v1/risk/grade`, {
      method:"POST",
      headers:{ "Content-Type":"application/json", "Authorization":`Bearer ${token}` },
      body: JSON.stringify({
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
      }),
    })
    if (!r.ok) return null
    return await r.json()
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setGrading(true); setRiskError("")
    let risk = null
    try { risk = await callRiskAPI() } catch(e) { setRiskError("Risk API unavailable — defaulting to LOW") }
    setRiskResult(risk)
    setGrading(false)
    onSubmit({ ...form, riskResult: risk })
  }

  return (
    <div style={{ display:"grid", gap:14 }}>

      {/* OCR auto-populated preview */}
      <OCRPreview nidScan={nidScan}/>

      {/* ── Personal Info ── */}
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.05 }}
        className="glass" style={{ padding:"20px 22px" }}>
        <SectionHdr
          icon={<User size={15} color="var(--accent)"/>}
          title="Personal Information"
          subtitle="BFIU §6.1 — Auto-populated from NID OCR · Edit to correct"
        />
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <GlassField label="Full Name (EN)" k="full_name" required
            readOnly={!!ec.full_name_en} form={form} errors={errors} onChange={set}
            icon={<User size={10}/>}/>
          <GlassField label="Full Name (বাংলা)" k="full_name_bn"
            form={form} errors={errors} onChange={set}
            hint="Bangla name from NID OCR"/>
          <GlassField label="Father's Name" k="fathers_name"
            readOnly={!!ec.fathers_name} form={form} errors={errors} onChange={set}/>
          <GlassField label="Mother's Name" k="mothers_name"
            readOnly={!!ec.mothers_name} form={form} errors={errors} onChange={set}/>
          <GlassField label="Spouse Name" k="spouse_name"
            form={form} errors={errors} onChange={set} placeholder="If applicable"/>
          <GlassField label="Date of Birth" k="date_of_birth" type="date"
            readOnly={!!ec.date_of_birth} form={form} errors={errors} onChange={set}/>
          <GlassSelect label="Gender" k="gender" required
            options={[{v:"M",l:"Male"},{v:"F",l:"Female"},{v:"T",l:"Third Gender"}]}
            form={form} errors={errors} onChange={set}/>
          <GlassField label="Nationality" k="nationality"
            readOnly form={form} errors={errors} onChange={set}/>
        </div>
      </motion.div>

      {/* ── Contact ── */}
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.10 }}
        className="glass" style={{ padding:"20px 22px" }}>
        <SectionHdr
          icon={<Phone size={15} color="var(--blue)"/>}
          title="Contact Information"
          subtitle="Bangladesh mobile number required for BFIU notification dispatch"
        />
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <GlassField label="Mobile Number" k="mobile" required type="tel"
            placeholder="01XXXXXXXXX" hint="Bangladesh number — 01X format"
            form={form} errors={errors} onChange={set} icon={<Phone size={10}/>}/>
          <GlassField label="Email Address" k="email" type="email"
            placeholder="optional" form={form} errors={errors} onChange={set}/>
        </div>
      </motion.div>

      {/* ── Address ── */}
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.15 }}
        className="glass" style={{ padding:"20px 22px" }}>
        <SectionHdr
          icon={<MapPin size={15} color="var(--green)"/>}
          title="Address"
          subtitle="Present and permanent address per BFIU §6.1"
        />
        <div style={{ display:"grid", gap:12 }}>
          <GlassField label="Present Address" k="present_address" required
            readOnly={!!ec.present_address} form={form} errors={errors} onChange={set}/>
          <GlassField label="Permanent Address" k="permanent_address"
            readOnly={!!ec.permanent_address} form={form} errors={errors} onChange={set}
            placeholder="Same as present if applicable"/>
        </div>
      </motion.div>

      {/* ── Financial ── */}
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.20 }}
        className="glass" style={{ padding:"20px 22px" }}>
        <SectionHdr
          icon={<Briefcase size={15} color="var(--yellow)"/>}
          title="Financial Profile"
          subtitle="BFIU §4.2 CDD — Source of funds mandatory for AML compliance"
        />
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
          <GlassSelect label="Profession" k="profession" required
            options={PROFESSIONS} form={form} errors={errors} onChange={set}
            icon={<Briefcase size={10}/>}/>
          <GlassField label="Monthly Income (BDT)" k="monthly_income" type="number"
            placeholder="e.g. 50000" form={form} errors={errors} onChange={set}/>
          <div style={{ gridColumn:"1/-1" }}>
            <GlassField label="Source of Funds" k="source_of_funds" required
              placeholder="e.g. Salary, Business income, Pension…"
              hint="Required by BFIU §4.2 — Anti-Money Laundering"
              form={form} errors={errors} onChange={set}/>
          </div>
        </div>
      </motion.div>

      {/* ── Nominee ── */}
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.25 }}
        className="glass" style={{ padding:"20px 22px" }}>
        <SectionHdr
          icon={<Users size={15} color="var(--accent)"/>}
          title="Nominee Details"
          subtitle="BFIU §6.1 — Nominee information for account/policy"
        />
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12 }}>
          <GlassField label="Nominee Name" k="nominee_name"
            form={form} errors={errors} onChange={set}/>
          <GlassField label="Relation" k="nominee_relation"
            placeholder="e.g. Spouse, Child" form={form} errors={errors} onChange={set}/>
          <GlassField label="Nominee DOB" k="nominee_dob" type="date"
            form={form} errors={errors} onChange={set}/>
        </div>
      </motion.div>

      {/* ── Risk params ── */}
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.30 }}
        className="glass" style={{ padding:"20px 22px" }}>
        <SectionHdr
          icon={<ShieldAlert size={15} color="var(--red)"/>}
          title="Risk Parameters"
          subtitle="BFIU §6.3 — 7-dimension risk grading engine"
        />
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:12 }}>
          <GlassSelect label="Institution Type" k="institution_type"
            options={["CMI","INSURANCE_LIFE","INSURANCE_NON_LIFE","BANK","MFI","NBFI"]}
            form={form} errors={errors} onChange={set}/>
          <GlassSelect label="Onboarding Channel" k="onboarding_channel"
            options={["AGENCY","BRANCH","DIGITAL","SELF_SERVICE"]}
            form={form} errors={errors} onChange={set}/>
          <GlassSelect label="Residency" k="residency"
            options={["RESIDENT","NON_RESIDENT","FOREIGNER"]}
            form={form} errors={errors} onChange={set}/>
          <GlassSelect label="Product Type" k="product_type"
            options={["BO_ACCOUNT","SAVINGS","CURRENT","INSURANCE","MUTUAL_FUND"]}
            form={form} errors={errors} onChange={set}/>
        </div>
        {/* PEP / Adverse Media toggles */}
        <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
          {[
            { k:"pep_flag",      label:"PEP / IP Status",      desc:"Politically Exposed Person" },
            { k:"adverse_media", label:"Adverse Media Flag",    desc:"Negative news detected" },
          ].map(({ k, label, desc }) => (
            <label key={k} style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 14px",
              borderRadius:"var(--radius-sm)", background:"var(--bg-glass2)",
              border:`1px solid ${form[k] ? "var(--red-border)" : "var(--border)"}`,
              backdropFilter:"blur(8px)", flex:1, minWidth:180 }}>
              <div style={{ position:"relative", width:36, height:20, flexShrink:0 }}>
                <input type="checkbox" checked={form[k]} onChange={e => set(k, e.target.checked)}
                  style={{ position:"absolute", opacity:0, width:"100%", height:"100%" }}/>
                <div style={{ width:36, height:20, borderRadius:10,
                  background: form[k] ? "var(--red)" : "var(--border-h)",
                  transition:"background 0.2s", position:"relative" }}>
                  <div style={{ position:"absolute", top:2, left: form[k] ? 18 : 2,
                    width:16, height:16, borderRadius:"50%", background:"#fff",
                    transition:"left 0.2s", boxShadow:"0 1px 4px rgba(0,0,0,0.2)" }}/>
                </div>
              </div>
              <div>
                <div style={{ fontSize:12, fontWeight:700, color: form[k] ? "var(--red)" : "var(--text)" }}>{label}</div>
                <div style={{ fontSize:10, color:"var(--text3)" }}>{desc}</div>
              </div>
            </label>
          ))}
        </div>

        {/* Risk result */}
        {riskResult && <RiskBadge riskResult={riskResult}/>}
        {riskError && (
          <div style={{ marginTop:8, fontSize:11, color:"var(--yellow)",
            padding:"8px 12px", borderRadius:"var(--radius-sm)",
            background:"var(--yellow-bg)", border:"1px solid var(--yellow-border)" }}>
            ⚠ {riskError}
          </div>
        )}
      </motion.div>

      {/* ── Actions ── */}
      <div style={{ display:"flex", gap:10, justifyContent:"flex-end", paddingBottom:8 }}>
        <button onClick={onBack} style={{ padding:"11px 20px", borderRadius:"var(--radius-sm)",
          background:"var(--bg-glass2)", backdropFilter:"blur(10px)",
          border:"1px solid var(--border)", color:"var(--text2)",
          fontSize:13, fontWeight:700, fontFamily:"var(--font)", transition:"all 0.2s" }}>
          ← Back
        </button>
        <button onClick={handleSubmit} disabled={grading} style={{ padding:"11px 28px",
          borderRadius:"var(--radius-sm)", border:"none",
          background: grading ? "var(--bg4)" : "linear-gradient(135deg, var(--accent), var(--blue))",
          color: grading ? "var(--text3)" : "#fff",
          fontSize:13, fontWeight:700, fontFamily:"var(--font)",
          boxShadow: grading ? "none" : "var(--shadow-accent)",
          display:"flex", alignItems:"center", gap:8, transition:"all 0.2s" }}>
          {grading ? <><Spinner size={13} color="var(--text3)"/> Grading Risk…</> : <>Continue to Signature →</>}
        </button>
      </div>
    </div>
  )
}
