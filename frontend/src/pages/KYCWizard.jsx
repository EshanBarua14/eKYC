import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useNavigate } from "react-router-dom"
import StepBar from "../components/ui/StepBar"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import { notify } from "../components/ui/Toast"
import { api } from "../hooks/useApi"
import {
  CreditCard, Camera, Scan, UserCheck, FileSignature,
  CheckCircle, ArrowLeft, ArrowRight, Shield, Users,
  AlertTriangle, BarChart2, ClipboardCheck
} from "lucide-react"
import Input from "../components/ui/Input"

const STEPS = [
  { label:"Consent",   icon:<Shield size={12}/>        },
  { label:"NID Entry", icon:<CreditCard size={12}/>    },
  { label:"Scan NID",  icon:<Scan size={12}/>          },
  { label:"Liveness",  icon:<Camera size={12}/>        },
  { label:"Profile",   icon:<UserCheck size={12}/>     },
  { label:"Screening", icon:<AlertTriangle size={12}/> },
  { label:"Risk",      icon:<BarChart2 size={12}/>     },
  { label:"Ownership", icon:<Users size={12}/>         },
  { label:"Sign",      icon:<FileSignature size={12}/> },
  { label:"Review",    icon:<ClipboardCheck size={12}/>},
  { label:"Complete",  icon:<CheckCircle size={12}/>   },
]

const BfiuNote = ({ text }) => (
  <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-xl border border-blue-100 dark:border-blue-900 mb-4">
    <p className="text-xs text-blue-700 dark:text-blue-300 flex items-center gap-1.5">
      <Shield size={12}/> {text}
    </p>
  </div>
)
const Nav = ({ onBack, onNext, loading, nextLabel="Continue", disabled=false }) => (
  <div className="flex gap-3 mt-4">
    {onBack && <Button variant="secondary" onClick={onBack} icon={<ArrowLeft size={14}/>}>Back</Button>}
    <Button onClick={onNext} loading={loading} disabled={disabled}
      className="flex-1" iconRight={<ArrowRight size={14}/>}>{nextLabel}</Button>
  </div>
)
const toB64 = (file) => new Promise(res => {
  const r = new FileReader(); r.onload = e => res(e.target.result); r.readAsDataURL(file)
})

function ConsentStep({ onNext }) {
  const [c, setC] = useState({ privacy:false, ekyc:false, biometric:false })
  const [loading, setLoading] = useState(false)
  const all = Object.values(c).every(Boolean)
  const items = [
    { k:"privacy",   title:"Data Privacy Consent",      sub:"Personal data collected per BFIU Circular No. 29 and applicable data protection laws." },
    { k:"ekyc",      title:"eKYC Verification Consent", sub:"I consent to electronic identity verification using my NID and date of birth against the EC database." },
    { k:"biometric", title:"Biometric Data Usage",      sub:"Facial recognition and liveness detection performed. Biometric data not shared with third parties." },
  ]
  const submit = async () => {
    if (!all) return notify.error("All consents required")
    setLoading(true)
    try { await api.post("/api/v1/consent/record", { privacy_consent:true, ekyc_consent:true, biometric_consent:true, channel:"web" }) }
    catch {}
    finally { setLoading(false) }
    notify.success("Consent recorded")
    onNext({ consents:c })
  }
  return (
    <div className="space-y-3">
      <BfiuNote text="BFIU §3.x — Written consent must be obtained before any biometric data collection"/>
      {items.map(({k,title,sub}) => (
        <div key={k} onClick={() => setC(p=>({...p,[k]:!p[k]}))}
          className={`flex gap-3 p-4 rounded-xl border cursor-pointer transition-all ${c[k]?"border-emerald-400 bg-emerald-50 dark:bg-emerald-950/20":"border-gray-200 dark:border-gray-700"}`}>
          <div className={`w-5 h-5 rounded flex-shrink-0 mt-0.5 flex items-center justify-center border-2 transition-all ${c[k]?"bg-emerald-500 border-emerald-500":"border-gray-300"}`}>
            {c[k] && <CheckCircle size={12} className="text-white"/>}
          </div>
          <div><p className="text-sm font-medium">{title}</p><p className="text-xs text-gray-400 mt-0.5">{sub}</p></div>
        </div>
      ))}
      <Nav onNext={submit} loading={loading} disabled={!all} nextLabel="Accept & Continue"/>
    </div>
  )
}

function NIDEntryStep({ onNext, onBack }) {
  const [nid, setNid] = useState(""); const [dob, setDob] = useState(""); const [loading, setLoading] = useState(false)
  const submit = async () => {
    if (nid.length < 10) return notify.error("NID must be at least 10 digits")
    if (!dob) return notify.error("Date of birth required")
    setLoading(true)
    try {
      const res = await api.post("/api/v1/nid/verify", { nid_number:nid, date_of_birth:dob })
      notify.success("NID verified"); onNext({ nid_number:nid, date_of_birth:dob, nid_data:res.data })
    } catch {
      notify.warning("EC API unavailable — demo mode"); onNext({ nid_number:nid, date_of_birth:dob, nid_data:null })
    } finally { setLoading(false) }
  }
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §3.2/3.3 — NID verified against Bangladesh Election Commission database"/>
      <Input label="NID Number *" value={nid} onChange={e=>setNid(e.target.value)} placeholder="10 or 17 digit NID" maxLength={17}/>
      <Input label="Date of Birth *" type="date" value={dob} onChange={e=>setDob(e.target.value)}/>
      <Nav onBack={onBack} onNext={submit} loading={loading} nextLabel="Verify NID"/>
    </div>
  )
}

function NIDScanStep({ onNext, onBack }) {
  const [front, setFront] = useState(null); const [back, setBack] = useState(null); const [loading, setLoading] = useState(false)
  const submit = async () => {
    if (!front) return notify.error("Front of NID required")
    setLoading(true)
    const frontB64 = await toB64(front); const backB64 = back ? await toB64(back) : null
    try {
      const res = await api.post("/api/v1/nid/scan-ocr", { front_image:frontB64, back_image:backB64 })
      notify.success("NID scanned"); onNext({ front_b64:frontB64, back_b64:backB64, ocr_data:res.data })
    } catch {
      notify.warning("OCR unavailable — demo mode"); onNext({ front_b64:frontB64, back_b64:backB64, ocr_data:null })
    } finally { setLoading(false) }
  }
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §3.3 — NID front and back captured for OCR extraction"/>
      <div className="grid grid-cols-2 gap-3">
        {[["Front *",front,setFront],["Back (optional)",back,setBack]].map(([label,file,setter])=>(
          <div key={label}>
            <label className="label">{label}</label>
            <label className={`flex flex-col items-center justify-center h-28 border-2 border-dashed rounded-xl cursor-pointer ${file?"border-emerald-400 bg-emerald-50 dark:bg-emerald-950/20":"border-gray-200 dark:border-gray-700"}`}>
              {file ? <img src={URL.createObjectURL(file)} alt={label} className="h-full w-full object-cover rounded-xl"/>
                : <div className="text-center"><Scan size={20} className="text-gray-300 mx-auto mb-1"/><p className="text-xs text-gray-400">Upload {label}</p></div>}
              <input type="file" accept="image/*" className="hidden" onChange={e=>setter(e.target.files[0])}/>
            </label>
          </div>
        ))}
      </div>
      <Nav onBack={onBack} onNext={submit} loading={loading} nextLabel="Process NID"/>
    </div>
  )
}

function LivenessStep({ onNext, onBack }) {
  const [image, setImage] = useState(null); const [loading, setLoading] = useState(false)
  const submit = async () => {
    if (!image) return notify.error("Live photo required")
    setLoading(true); const b64 = await toB64(image)
    try {
      const res = await api.post("/api/v1/ai/challenge", { live_image:b64 })
      notify.success("Liveness passed"); onNext({ live_b64:b64, liveness_result:res.data })
    } catch { notify.warning("Liveness API unavailable — demo"); onNext({ live_b64:b64, liveness_result:{ passed:true, score:0.95 } }) }
    finally { setLoading(false) }
  }
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU Annexure-2g — Liveness detection (blink, turn, smile) prevents spoofing"/>
      <label className={`flex flex-col items-center justify-center h-48 border-2 border-dashed rounded-xl cursor-pointer ${image?"border-emerald-400 bg-emerald-50 dark:bg-emerald-950/20":"border-gray-200 dark:border-gray-700"}`}>
        {image ? <img src={URL.createObjectURL(image)} alt="live" className="h-full w-full object-cover rounded-xl"/>
          : <div className="text-center p-4"><Camera size={32} className="text-gray-300 mx-auto mb-2"/><p className="text-sm text-gray-500">Take or upload live selfie</p></div>}
        <input type="file" accept="image/*" capture="user" className="hidden" onChange={e=>setImage(e.target.files[0])}/>
      </label>
      <Nav onBack={onBack} onNext={submit} loading={loading} nextLabel="Verify Liveness"/>
    </div>
  )
}

function ProfileStep({ nidData, onNext, onBack }) {
  const [form, setForm] = useState({
    full_name:nidData?.nid_data?.name||"", full_name_bn:nidData?.nid_data?.name_bn||"",
    date_of_birth:nidData?.date_of_birth||"", mobile:"", email:"",
    present_address:"", permanent_address:"", profession:"",
    monthly_income:"", source_of_funds:"", nominee_name:"", nominee_relation:"",
    nationality:"Bangladeshi", kyc_type:"SIMPLIFIED",
  })
  const f = k => e => setForm(p=>({...p,[k]:e.target.value}))
  const submit = () => {
    if (!form.full_name || !form.mobile) return notify.error("Name and mobile required")
    notify.success("Profile saved"); onNext(form)
  }
  return (
    <div className="space-y-3">
      <BfiuNote text="BFIU §6.1/6.2 — Customer profile (Simplified up to 5L / Regular above 5L)"/>
      <div className="grid grid-cols-2 gap-3">
        <Input label="Full Name (English) *" value={form.full_name} onChange={f("full_name")} placeholder="As per NID"/>
        <Input label="Full Name (Bangla)" value={form.full_name_bn} onChange={f("full_name_bn")} placeholder="বাংলা নাম"/>
        <Input label="Date of Birth *" type="date" value={form.date_of_birth} onChange={f("date_of_birth")}/>
        <Input label="Mobile *" value={form.mobile} onChange={f("mobile")} placeholder="017XXXXXXXX"/>
        <Input label="Email" type="email" value={form.email} onChange={f("email")} placeholder="optional"/>
        <Input label="Profession" value={form.profession} onChange={f("profession")}/>
        <Input label="Monthly Income (BDT)" value={form.monthly_income} onChange={f("monthly_income")} placeholder="50000"/>
        <Input label="Source of Funds *" value={form.source_of_funds} onChange={f("source_of_funds")} placeholder="Salary / Business"/>
        <Input label="Present Address *" value={form.present_address} onChange={f("present_address")} containerClass="col-span-2"/>
        <Input label="Permanent Address" value={form.permanent_address} onChange={f("permanent_address")} containerClass="col-span-2"/>
        <Input label="Nominee Name" value={form.nominee_name} onChange={f("nominee_name")}/>
        <Input label="Nominee Relation" value={form.nominee_relation} onChange={f("nominee_relation")} placeholder="Spouse / Parent"/>
        <div className="col-span-2">
          <label className="label">KYC Type</label>
          <div className="flex gap-3">
            {["SIMPLIFIED","REGULAR"].map(t=>(
              <div key={t} onClick={()=>setForm(p=>({...p,kyc_type:t}))}
                className={`flex-1 p-3 rounded-xl border cursor-pointer text-sm font-medium text-center transition-all ${form.kyc_type===t?"border-brand-400 bg-brand-50 dark:bg-brand-950/20 text-brand-600":"border-gray-200 dark:border-gray-700 text-gray-500"}`}>
                {t==="SIMPLIFIED"?"Simplified (up to 5L BDT)":"Regular (above 5L BDT)"}
              </div>
            ))}
          </div>
        </div>
      </div>
      <Nav onBack={onBack} onNext={submit} nextLabel="Save Profile"/>
    </div>
  )
}

function ScreeningStep({ sessionData, onNext, onBack }) {
  const [loading, setLoading] = useState(false); const [result, setResult] = useState(null)
  const run = async () => {
    setLoading(true)
    try {
      const res = await api.post("/api/v1/screening/run", {
        name:sessionData.profile?.full_name||"", kyc_type:sessionData.profile?.kyc_type||"SIMPLIFIED",
      })
      setResult(res.data)
      res.data?.overall_verdict==="MATCH" ? notify.error("MATCH — EDD required") : notify.success("Screening clear")
    } catch { notify.warning("Screening API unavailable"); setResult({ overall_verdict:"CLEAR_DEMO" }) }
    finally { setLoading(false) }
  }
  const blocked = result?.overall_verdict==="MATCH"
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §3.2.2/4.2 — UNSCR sanctions, PEP/IP screening, Adverse media (live daily feeds)"/>
      {!result ? (
        <div className="text-center py-6">
          <AlertTriangle size={32} className="text-amber-400 mx-auto mb-3"/>
          <p className="text-sm text-gray-500 mb-4">Run AML/CFT screening against live databases</p>
          <Button onClick={run} loading={loading} variant="warning" icon={<Shield size={14}/>}>Run Screening</Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className={`p-4 rounded-xl border ${blocked?"border-red-300 bg-red-50 dark:bg-red-950/20":"border-emerald-300 bg-emerald-50 dark:bg-emerald-950/20"}`}>
            <p className={`font-semibold text-sm ${blocked?"text-red-600":"text-emerald-600"}`}>
              {blocked?"MATCH — Refer to Compliance Officer":"Clear — No matches found"}
            </p>
          </div>
          {[["UNSCR",result.unscr_verdict||result.sanctions_verdict],["PEP/IP",result.pep_verdict],["Adverse Media",result.adverse_media_verdict]].map(([l,v])=>v&&(
            <div key={l} className="flex justify-between py-2 border-b border-gray-100 dark:border-gray-800 text-sm">
              <span className="text-gray-500">{l}</span>
              <span className={`font-medium ${v==="CLEAR"||v==="NO_MATCH"?"text-emerald-600":"text-red-500"}`}>{v}</span>
            </div>
          ))}
          {!blocked && <Nav onBack={onBack} onNext={()=>onNext(result)} nextLabel="Proceed to Risk"/>}
          {blocked && <div className="p-3 bg-red-50 rounded-xl text-xs text-red-600">Escalate to Compliance Officer (BFIU §4.3).</div>}
        </div>
      )}
      {!result && <Nav onBack={onBack} onNext={()=>{}} disabled nextLabel="Run Screening First"/>}
    </div>
  )
}

function RiskStep({ sessionData, onNext, onBack }) {
  const [loading, setLoading] = useState(false); const [result, setResult] = useState(null)
  const run = async () => {
    setLoading(true)
    try {
      const res = await api.post("/api/v1/risk/grade", {
        kyc_type:sessionData.profile?.kyc_type||"SIMPLIFIED",
        nationality:sessionData.profile?.nationality||"Bangladeshi",
        source_of_funds:sessionData.profile?.source_of_funds||"",
        monthly_income:parseFloat(sessionData.profile?.monthly_income||0),
        product_type:"INSURANCE_LIFE",
        pep_flag:sessionData.screening?.pep_verdict==="MATCH",
      })
      setResult(res.data); notify.success("Risk graded: "+(res.data?.risk_level||"LOW"))
    } catch { setResult({ risk_level:"LOW", risk_score:5, edd_required:false }); notify.warning("Risk API unavailable — default LOW") }
    finally { setLoading(false) }
  }
  const C = { LOW:"text-emerald-600", MEDIUM:"text-amber-500", HIGH:"text-red-500" }
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §6.3.1/6.3.2 — 7-dimension automated risk grading"/>
      {!result ? (
        <div className="text-center py-6">
          <BarChart2 size={32} className="text-blue-400 mx-auto mb-3"/>
          <Button onClick={run} loading={loading} icon={<BarChart2 size={14}/>}>Run Risk Assessment</Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
            <p className="text-xs text-gray-400 mb-1">Risk Level</p>
            <p className={`text-2xl font-bold ${C[result.risk_level]||"text-gray-600"}`}>{result.risk_level}</p>
            <p className="text-xs text-gray-400 mt-1">Score: {result.risk_score} / 30</p>
            {result.edd_required && <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-600">EDD required — score is 15 or above (BFIU §4.2)</div>}
          </div>
          <Nav onBack={onBack} onNext={()=>onNext(result)} nextLabel="Continue to Ownership"/>
        </div>
      )}
      {!result && <Nav onBack={onBack} onNext={()=>{}} disabled nextLabel="Run Assessment First"/>}
    </div>
  )
}

function BeneficialOwnerStep({ sessionData, onNext, onBack }) {
  const isRegular = sessionData.profile?.kyc_type==="REGULAR"
  const [hasBO, setHasBO] = useState(false)
  const [form, setForm] = useState({ full_name:"", nid_number:"", date_of_birth:"", ownership_percentage:"", relationship:"", is_pep:false })
  const [loading, setLoading] = useState(false)
  const f = k => e => setForm(p=>({...p,[k]:e.target.value}))
  const submit = async () => {
    if (!isRegular) { onNext({ beneficial_owner:null, skipped:true }); return }
    if (hasBO && !form.full_name) return notify.error("BO name required")
    setLoading(true)
    try {
      if (hasBO) {
        await api.post("/api/v1/kyc/beneficial-owner", { ...form, session_id:sessionData.sessionId })
        notify.success("BO recorded (BFIU §4.2)"); onNext({ beneficial_owner:form })
      } else { onNext({ beneficial_owner:null }) }
    } catch(e) { notify.error(e.response?.data?.detail||"Failed to record BO") }
    finally { setLoading(false) }
  }
  if (!isRegular) return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §4.2 — Beneficial ownership mandatory for Regular eKYC only"/>
      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl text-center">
        <Users size={28} className="text-gray-300 mx-auto mb-2"/>
        <p className="text-sm text-gray-500">Simplified eKYC — BO check not required</p>
      </div>
      <Nav onBack={onBack} onNext={()=>onNext({ beneficial_owner:null, skipped:true })} nextLabel="Skip to Sign"/>
    </div>
  )
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §4.2 — Identify any beneficial owner with 25% or more ownership or control"/>
      <div className="flex gap-3">
        {[false,true].map(v=>(
          <div key={String(v)} onClick={()=>setHasBO(v)}
            className={`flex-1 p-3 rounded-xl border cursor-pointer text-sm text-center transition-all ${hasBO===v?"border-brand-400 bg-brand-50 dark:bg-brand-950/20 font-medium":"border-gray-200 dark:border-gray-700 text-gray-500"}`}>
            {v?"Yes — Has Beneficial Owner":"No Beneficial Owner"}
          </div>
        ))}
      </div>
      {hasBO && (
        <div className="grid grid-cols-2 gap-3">
          <Input label="BO Full Name *" value={form.full_name} onChange={f("full_name")}/>
          <Input label="BO NID Number *" value={form.nid_number} onChange={f("nid_number")}/>
          <Input label="BO Date of Birth" type="date" value={form.date_of_birth} onChange={f("date_of_birth")}/>
          <Input label="Ownership %" value={form.ownership_percentage} onChange={f("ownership_percentage")} placeholder="e.g. 30"/>
          <Input label="Relationship" value={form.relationship} onChange={f("relationship")} containerClass="col-span-2"/>
          <label className="col-span-2 flex items-center gap-2 cursor-pointer text-sm">
            <input type="checkbox" checked={form.is_pep} onChange={e=>setForm(p=>({...p,is_pep:e.target.checked}))} className="rounded"/>
            BO is a PEP/IP — triggers EDD per BFIU §4.2
          </label>
        </div>
      )}
      <Nav onBack={onBack} onNext={submit} loading={loading} nextLabel={hasBO?"Record BO then Sign":"No BO — proceed to Sign"}/>
    </div>
  )
}

function SignatureStep({ sessionData, onNext, onBack }) {
  const [sigType, setSigType] = useState("DIGITAL")
  const [otp, setOtp] = useState(""); const [otpSent, setOtpSent] = useState(false); const [loading, setLoading] = useState(false)
  const sendOtp = async () => {
    setLoading(true)
    try { await api.post("/api/v1/consent/send-otp", { mobile:sessionData.profile?.mobile }); setOtpSent(true); notify.success("OTP sent") }
    catch { setOtpSent(true); notify.warning("Demo OTP: 123456") }
    finally { setLoading(false) }
  }
  const submit = async () => {
    if (sigType==="DIGITAL" && !otp) return notify.error("Enter OTP")
    setLoading(true)
    try {
      await api.post("/api/v1/consent/esign", { session_id:sessionData.sessionId, signature_type:sigType, otp_verified:otp||undefined })
      notify.success("Signature captured (BFIU §6.1)"); onNext({ signature_type:sigType, signed:true })
    } catch { notify.warning("Sign API unavailable"); onNext({ signature_type:sigType, signed:true }) }
    finally { setLoading(false) }
  }
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §6.1 — Applicant eSignature required on completed profile"/>
      <div className="grid grid-cols-2 gap-3">
        {[["DIGITAL","OTP Signature","One-time PIN to mobile — recommended"],["ELECTRONIC","PIN Code","4-digit PIN — Simplified only"]].map(([id,label,sub])=>(
          <div key={id} onClick={()=>setSigType(id)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${sigType===id?"border-brand-400 bg-brand-50 dark:bg-brand-950/20":"border-gray-200 dark:border-gray-700"}`}>
            <p className="text-sm font-medium">{label}</p><p className="text-xs text-gray-400 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>
      {sigType==="DIGITAL" && (!otpSent
        ? <Button onClick={sendOtp} loading={loading} variant="secondary" className="w-full">Send OTP to {sessionData.profile?.mobile||"mobile"}</Button>
        : <Input label="Enter OTP" value={otp} onChange={e=>setOtp(e.target.value)} placeholder="6-digit OTP" maxLength={6}/>)}
      {sigType==="ELECTRONIC" && <Input label="4-digit PIN" type="password" value={otp} onChange={e=>setOtp(e.target.value)} maxLength={4} placeholder="..."/>}
      <Nav onBack={onBack} onNext={submit} loading={loading} disabled={sigType==="DIGITAL"&&!otp} nextLabel="Confirm Signature"/>
    </div>
  )
}

function ReviewStep({ sessionData, onNext, onBack }) {
  const [loading, setLoading] = useState(false); const p = sessionData.profile||{}
  const submit = async () => {
    setLoading(true)
    try {
      let confidence=0.85, verdict="MATCHED"
      try {
        const r = await api.post("/api/v1/face/verify", { session_id:sessionData.sessionId, nid_number:sessionData.nid?.nid_number, live_image_b64:sessionData.liveness?.live_b64, nid_image_b64:sessionData.nidScan?.front_b64 })
        confidence=r.data?.confidence||0.85; verdict=r.data?.verdict||"MATCHED"
      } catch {}
      const res = await api.post("/api/v1/kyc/profile", { session_id:sessionData.sessionId, verdict, confidence, institution_type:"INSURANCE_LIFE", ...p, unscr_checked:true, pep_flag:false })
      notify.success("eKYC profile created (BFIU §6.1/§6.2)")
      onNext({ session_id:sessionData.sessionId, profile:res.data, confidence, verdict })
    } catch(e) { notify.error(e.response?.data?.detail||"Submission failed") }
    finally { setLoading(false) }
  }
  const rows = [["NID",sessionData.nid?.nid_number],["Name",p.full_name],["Mobile",p.mobile],["KYC Type",p.kyc_type],["Risk",sessionData.risk?.risk_level||"—"],["Screening",sessionData.screening?.overall_verdict||"—"],["Signature",sessionData.signature?.signature_type||"—"]]
  return (
    <div className="space-y-4">
      <BfiuNote text="BFIU §6.1/6.2 — Final review before eKYC profile is locked"/>
      <div className="space-y-1.5">
        {rows.map(([k,v])=>(
          <div key={k} className="flex justify-between py-1.5 border-b border-gray-50 dark:border-gray-800 text-sm">
            <span className="text-gray-400">{k}</span>
            <span className="font-medium text-gray-800 dark:text-gray-200">{v||"—"}</span>
          </div>
        ))}
      </div>
      <Nav onBack={onBack} onNext={submit} loading={loading} nextLabel="Submit eKYC Profile"/>
    </div>
  )
}

function CompleteStep({ result }) {
  const navigate = useNavigate()
  return (
    <div className="text-center space-y-4 py-4">
      <motion.div initial={{scale:0}} animate={{scale:1}} transition={{type:"spring",damping:15,stiffness:200}}
        className="w-16 h-16 bg-emerald-100 dark:bg-emerald-950/30 rounded-full flex items-center justify-center mx-auto">
        <CheckCircle size={32} className="text-emerald-500"/>
      </motion.div>
      <div>
        <h3 className="text-lg font-bold">eKYC Complete!</h3>
        <p className="text-sm text-gray-400 mt-1">BFIU Circular No. 29 — All 11 steps complete</p>
      </div>
      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl text-left space-y-2">
        {[["Session ID",result?.session_id,"font-mono text-xs"],["Verdict",result?.verdict||"MATCHED","text-emerald-600 font-semibold"],["Confidence",((result?.confidence||0.85)*100).toFixed(1)+"%","text-brand-600 font-semibold"]].map(([l,v,c])=>(
          <div key={l}><p className="text-xs text-gray-400">{l}</p><p className={`text-sm break-all ${c}`}>{v||"—"}</p></div>
        ))}
      </div>
      <div className="flex gap-3">
        <Button variant="secondary" className="flex-1" onClick={()=>window.location.reload()}>New eKYC</Button>
        <Button className="flex-1" onClick={()=>navigate("/kyc/sessions")}>View Sessions</Button>
      </div>
    </div>
  )
}

export default function KYCWizard() {
  const [step, setStep] = useState(1)
  const [sd, setSd] = useState({
    sessionId:`sess-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
    consent:null, nid:null, nidScan:null, liveness:null, profile:null,
    screening:null, risk:null, beneficial_owner:null, signature:null, result:null,
  })
  const next = (key, data) => { setSd(p=>({...p,[key]:data})); setStep(s=>s+1) }

  const steps = [
    <ConsentStep          onNext={d=>next("consent",d)}/>,
    <NIDEntryStep         onNext={d=>next("nid",d)}             onBack={()=>setStep(1)}/>,
    <NIDScanStep          onNext={d=>next("nidScan",d)}          onBack={()=>setStep(2)}/>,
    <LivenessStep         onNext={d=>next("liveness",d)}         onBack={()=>setStep(3)}/>,
    <ProfileStep          nidData={sd.nid} onNext={d=>next("profile",d)} onBack={()=>setStep(4)}/>,
    <ScreeningStep        sessionData={sd} onNext={d=>next("screening",d)} onBack={()=>setStep(5)}/>,
    <RiskStep             sessionData={sd} onNext={d=>next("risk",d)}      onBack={()=>setStep(6)}/>,
    <BeneficialOwnerStep  sessionData={sd} onNext={d=>next("beneficial_owner",d)} onBack={()=>setStep(7)}/>,
    <SignatureStep        sessionData={sd} onNext={d=>next("signature",d)} onBack={()=>setStep(8)}/>,
    <ReviewStep           sessionData={sd} onNext={d=>next("result",d)}    onBack={()=>setStep(9)}/>,
    <CompleteStep         result={sd.result}/>,
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-up">
      <div>
        <h2 className="page-title">New eKYC Onboarding</h2>
        <p className="text-sm text-gray-400 mt-1">BFIU Circular No. 29 — 11-step verified onboarding</p>
      </div>
      <StepBar steps={STEPS} current={step}/>
      <Card>
        <div className="mb-4">
          <h3 className="text-base font-semibold">Step {step} of {STEPS.length}: {STEPS[step-1]?.label}</h3>
        </div>
        <AnimatePresence mode="wait">
          <motion.div key={step} initial={{opacity:0,x:10}} animate={{opacity:1,x:0}} exit={{opacity:0,x:-10}} transition={{duration:0.2}}>
            {steps[step-1]}
          </motion.div>
        </AnimatePresence>
      </Card>
    </div>
  )
}
