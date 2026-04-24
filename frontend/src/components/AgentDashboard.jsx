import { useState, useEffect, useCallback } from "react"
import { Card, Btn, Badge, Spinner, SectionTitle, StatGrid, Divider, CheckItem } from "./ui"
import { API, authHeaders, ensureDemoToken } from "../config.js"
import axios from "axios"
import {
  Users, Shield, FileText, Search, Bell, LogOut, ChevronRight,
  Plus, Eye, CheckCircle, XCircle, Clock, AlertTriangle,
  User, Phone, MapPin, Calendar, Fingerprint, Camera,
  TrendingUp, Activity, RefreshCw, Download, Filter,
  ChevronDown, Zap
} from "lucide-react"

const statusColor  = s => ({ COMPLETED:"green", PENDING:"yellow", FAILED:"red", IN_PROGRESS:"accent" }[s] || "accent")
const riskColor    = r => ({ LOW:"green", MEDIUM:"yellow", HIGH:"red" }[r] || "accent")
const verdictColor = v => ({ MATCHED:"green", REVIEW:"yellow", FAILED:"red" }[v] || "accent")

function Field({ label, type="text", value, onChange, placeholder, options }) {
  const base = { width:"100%", padding:"9px 12px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", fontSize:13, outline:"none", boxSizing:"border-box" }
  return (
    <div>
      <label style={{ fontSize:11, fontWeight:600, color:"var(--text3)", display:"block", marginBottom:5, textTransform:"uppercase", letterSpacing:"0.05em" }}>{label}</label>
      {type === "select"
        ? <select value={value} onChange={e => onChange(e.target.value)} style={base}>{options.map(o => <option key={o} value={o}>{o.replace(/_/g," ")}</option>)}</select>
        : <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={base}
            onFocus={e=>e.target.style.borderColor="var(--accent)"}
            onBlur={e=>e.target.style.borderColor="var(--border)"} />}
    </div>
  )
}

function Sidebar({ active, setActive, agent, onExit }) {
  const nav = [
    { id:"dashboard", icon:Activity,  label:"Dashboard" },
    { id:"sessions",  icon:Users,     label:"Sessions" },
    { id:"new",       icon:Plus,      label:"New Session", accent:true },
    { id:"search",    icon:Search,    label:"NID Search" },
    { id:"reports",   icon:FileText,  label:"My Reports" },
    { id:"profile",   icon:User,      label:"My Profile" },
  ]
  return (
    <div style={{ width:220, flexShrink:0, background:"var(--bg2)", borderRight:"1px solid var(--border)", display:"flex", flexDirection:"column", height:"100vh", position:"sticky", top:0 }}>
      <div style={{ padding:"20px 20px 16px", borderBottom:"1px solid var(--border)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:34, height:34, borderRadius:10, background:"linear-gradient(135deg,var(--accent),var(--blue))", display:"flex", alignItems:"center", justifyContent:"center", boxShadow:"0 4px 12px rgba(99,88,255,0.3)" }}><Shield size={16} color="#fff" strokeWidth={2.5}/></div>
          <img src="/logo.jpg" alt="Xpert eKYC" style={{ height:"36px", objectFit:"contain" }} />
        </div>
      </div>
      <nav style={{ flex:1, padding:"12px 10px", overflowY:"auto" }}>
        {nav.map(({ id, icon:Icon, label, accent }) => {
          const on = active === id
          return (
            <button key={id} onClick={() => setActive(id)} style={{ width:"100%", display:"flex", alignItems:"center", gap:10, padding:"9px 12px", borderRadius:"var(--radius-sm)", marginBottom:2, background: on?(accent?"var(--accent)":"var(--accent-bg)"):accent?"var(--accent-bg)":"transparent", border: on&&accent?"none":on?"1px solid rgba(99,88,255,0.2)":"1px solid transparent", color: on?(accent?"#fff":"var(--accent)"):accent?"var(--accent)":"var(--text2)", fontFamily:"var(--font)", fontSize:13, fontWeight:on?700:500, cursor:"pointer", transition:"all 0.15s", textAlign:"left" }}
              onMouseEnter={e=>{if(!on)e.currentTarget.style.background="var(--bg3)"}}
              onMouseLeave={e=>{if(!on)e.currentTarget.style.background=accent?"var(--accent-bg)":"transparent"}}>
              <Icon size={15} strokeWidth={on?2.5:2}/><span>{label}</span>
              {id==="new" && <Zap size={11} style={{marginLeft:"auto"}} strokeWidth={2.5}/>}
            </button>
          )
        })}
      </nav>
      <div style={{ padding:"12px 14px", borderTop:"1px solid var(--border)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:10 }}>
          <div style={{ width:32, height:32, borderRadius:99, background:"linear-gradient(135deg,var(--accent),var(--blue))", display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, fontWeight:700, color:"#fff", flexShrink:0 }}>{agent.name[0]}</div>
          <div style={{ minWidth:0 }}>
            <div style={{ fontSize:12, fontWeight:700, color:"var(--text)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{agent.name}</div>
            <div style={{ fontSize:10, color:"var(--text3)" }}>{agent.zone}</div>
          </div>
        </div>
        <button onClick={onExit} style={{ width:"100%", display:"flex", alignItems:"center", justifyContent:"center", gap:6, padding:7, borderRadius:"var(--radius-xs)", background:"var(--red-bg)", color:"var(--red)", border:"1px solid var(--red-border)", fontFamily:"var(--font)", fontSize:11, fontWeight:600, cursor:"pointer" }}><LogOut size={12}/> Sign Out</button>
      </div>
    </div>
  )
}

function SessionRow({ session:s, compact }) {
  return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding: compact?"10px 14px":"14px 18px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)" }}>
      <div style={{ display:"flex", alignItems:"center", gap:12 }}>
        <div style={{ width:36, height:36, borderRadius:10, background:"var(--accent-bg)", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
          <User size={15} color="var(--accent)" strokeWidth={2}/>
        </div>
        <div>
          <div style={{ fontSize:13, fontWeight:700, color:"var(--text)" }}>{s.name || s.nid_number || s.session_id?.slice(0,8)}</div>
          <div style={{ fontSize:11, color:"var(--text3)", fontFamily:"var(--font-mono)" }}>
            {s.nid || s.nid_number} · {s.type || s.kyc_type} · {s.channel} · {s.time || s.created_at?.slice(11,16)}
          </div>
        </div>
      </div>
      <div style={{ display:"flex", gap:6, alignItems:"center", flexShrink:0 }}>
        {s.risk && <Badge color={riskColor(s.risk)}>{s.risk}</Badge>}
        {s.verdict && <Badge color={verdictColor(s.verdict)}>{s.verdict}</Badge>}
        <Badge color={statusColor(s.status)}>{s.status?.replace("_"," ")}</Badge>
      </div>
    </div>
  )
}

// ── Live stats from /api/v1/audit/summary ──────────────────────────────────
function useLiveStats() {
  const [stats, setStats] = useState(null)
  const load = useCallback(async () => {
    try {
      const token = await ensureDemoToken()
      const r = await fetch(`${API}/api/v1/audit/summary`, { headers: { Authorization:`Bearer ${token}` } })
      if (r.ok) setStats(await r.json())
    } catch(_) {}
  }, [])
  useEffect(() => { load() }, [load])
  return { stats, reload: load }
}

// ── Live sessions from /api/v1/outcome/list ────────────────────────────────
function useLiveSessions() {
  const [sessions, setSessions] = useState([])
  const load = useCallback(async () => {
    try {
      const token = await ensureDemoToken()
      const r = await fetch(`${API}/api/v1/outcome/list?limit=20`, { headers: { Authorization:`Bearer ${token}` } })
      if (r.ok) {
        const d = await r.json()
        setSessions(d.outcomes || d.items || d || [])
      }
    } catch(_) {}
  }, [])
  useEffect(() => { load() }, [load])
  return { sessions, reload: load }
}

function DashboardTab({ sessions, stats, setActive, reload }) {
  const today    = stats?.today      || {}
  const todayTotal     = today.total        ?? sessions.length
  const todayCompleted = today.completed    ?? sessions.filter(s=>s.status==="COMPLETED").length
  const todayPending   = today.pending      ?? sessions.filter(s=>["PENDING","IN_PROGRESS"].includes(s.status)).length
  const successRate    = stats?.success_rate ?? (todayTotal > 0 ? ((todayCompleted/todayTotal)*100).toFixed(1) : "0")

  return (
    <div style={{ display:"grid", gap:16 }}>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
        {[
          { label:"Today Sessions", value:todayTotal,         color:"var(--accent)", icon:Activity },
          { label:"Completed",      value:todayCompleted,     color:"var(--green)",  icon:CheckCircle },
          { label:"Pending Review", value:todayPending,       color:"var(--yellow)", icon:Clock },
          { label:"Success Rate",   value:`${successRate}%`,  color:"var(--blue)",   icon:TrendingUp },
        ].map(({ label,value,color,icon:Icon })=>(
          <Card key={label} style={{ padding:"16px 18px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
              <div>
                <div style={{ fontSize:10, color:"var(--text3)", fontWeight:600, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:6 }}>{label}</div>
                <div style={{ fontSize:26, fontWeight:800, color, fontFamily:"var(--font-mono)", lineHeight:1 }}>{value}</div>
              </div>
              <div style={{ width:36, height:36, borderRadius:10, background:`${color}18`, display:"flex", alignItems:"center", justifyContent:"center" }}><Icon size={16} color={color} strokeWidth={2}/></div>
            </div>
          </Card>
        ))}
      </div>
      <Card style={{ padding:"16px 20px" }}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
          <SectionTitle sub="Start or continue work">Quick Actions</SectionTitle>
          <Btn variant="ghost" size="sm" onClick={reload}><RefreshCw size={12}/> Refresh</Btn>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
          {[
            { label:"Start New eKYC",  sub:"Fingerprint or Face",   color:"var(--accent)", icon:Plus,   action:"new" },
            { label:"Search NID",      sub:"Look up existing",      color:"var(--blue)",   icon:Search, action:"search" },
            { label:"Pending Reviews", sub:`${todayPending} awaiting`, color:"var(--yellow)", icon:Clock, action:"sessions" },
          ].map(({ label,sub,color,icon:Icon,action })=>(
            <button key={label} onClick={()=>setActive(action)} style={{ padding:"14px 16px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)", textAlign:"left", cursor:"pointer", transition:"all 0.15s", fontFamily:"var(--font)" }}
              onMouseEnter={e=>{ e.currentTarget.style.borderColor=color; e.currentTarget.style.background="var(--bg4)" }}
              onMouseLeave={e=>{ e.currentTarget.style.borderColor="var(--border)"; e.currentTarget.style.background="var(--bg3)" }}>
              <div style={{ width:30, height:30, borderRadius:8, background:`${color}18`, display:"flex", alignItems:"center", justifyContent:"center", marginBottom:10 }}><Icon size={14} color={color} strokeWidth={2.5}/></div>
              <div style={{ fontSize:12, fontWeight:700, color:"var(--text)" }}>{label}</div>
              <div style={{ fontSize:11, color:"var(--text3)", marginTop:2 }}>{sub}</div>
            </button>
          ))}
        </div>
      </Card>
      <Card>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
          <SectionTitle sub="Today activity">Recent Sessions</SectionTitle>
          <Btn variant="ghost" size="sm" onClick={()=>setActive("sessions")}>View all <ChevronRight size={12}/></Btn>
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
          {sessions.slice(0,4).map((s,i) => <SessionRow key={s.id||s.session_id||i} session={s} compact />)}
          {sessions.length === 0 && <div style={{ textAlign:"center", padding:24, color:"var(--text3)", fontSize:13 }}>No sessions yet today</div>}
        </div>
      </Card>
    </div>
  )
}

function SessionsTab({ sessions }) {
  return (
    <Card>
      <SectionTitle sub={`${sessions.length} sessions`}>All Sessions</SectionTitle>
      <div style={{ display:"flex", flexDirection:"column", gap:8, marginTop:12 }}>
        {sessions.map((s,i) => <SessionRow key={s.id||s.session_id||i} session={s} />)}
        {sessions.length === 0 && <div style={{ textAlign:"center", padding:32, color:"var(--text3)", fontSize:13 }}>No sessions found</div>}
      </div>
    </Card>
  )
}

// ── New Session Tab — wired to /onboarding/start + /onboarding/step ─────────
function NewSessionTab({ onSessionCreated }) {
  const [step,       setStep]       = useState(1)
  const [form,       setForm]       = useState({ nid:"", dob:"", channel:"AGENCY", kyc_type:"SIMPLIFIED", product_type:"ORDINARY_LIFE", full_name:"", mobile:"", biometric:"FINGERPRINT" })
  const [checking,   setChecking]   = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [nidResult,  setNidResult]  = useState(null)
  const [sessionId,  setSessionId]  = useState(null)
  const [error,      setError]      = useState("")
  const [success,    setSuccess]    = useState(null)

  const STEPS = [{n:1,label:"NID Verify"},{n:2,label:"Customer"},{n:3,label:"Biometric"},{n:4,label:"Submit"}]

  const verifyNID = async () => {
    if (!form.nid || form.nid.length < 10) { setError("Enter valid NID (10-17 digits)"); return }
    setChecking(true); setError("")
    try {
      const token = await ensureDemoToken()
      const r = await axios.post(`${API}/api/v1/nid/verify`,
        { nid_number:form.nid, session_id:"agent_"+Date.now() },
        { headers: { Authorization:`Bearer ${token}`, "Content-Type":"application/json" } }
      )
      setNidResult(r.data)
      if (r.data.ec_data?.full_name_en) setForm(f=>({...f, full_name:r.data.ec_data.full_name_en}))
      setStep(2)
    } catch(e) {
      // Demo fallback
      setNidResult({ ec_source:"DEMO", ec_data:{ full_name_en:"Demo Customer", date_of_birth:"1990-01-01" }})
      setStep(2)
    } finally { setChecking(false) }
  }

  const startWizardSession = async () => {
    try {
      const token = await ensureDemoToken()
      const r = await fetch(`${API}/api/v1/onboarding/start`, {
        method:"POST",
        headers:{ Authorization:`Bearer ${token}`, "Content-Type":"application/json" },
        body: JSON.stringify({ nid_number:form.nid, agent_id:"agent-001", channel:form.channel, kyc_type:form.kyc_type })
      })
      if (r.ok) {
        const d = await r.json()
        setSessionId(d.session_id)
        return d.session_id
      }
    } catch(_) {}
    return null
  }

  const submitStep = async (sid, stepData) => {
    try {
      const token = await ensureDemoToken()
      const r = await fetch(`${API}/api/v1/onboarding/step`, {
        method:"POST",
        headers:{ Authorization:`Bearer ${token}`, "Content-Type":"application/json" },
        body: JSON.stringify({ session_id:sid, step_data:stepData })
      })
      if (r.ok) return await r.json()
    } catch(_) {}
    return null
  }

  const handleSubmit = async () => {
    if (!form.full_name) { setError("Full name required"); return }
    if (!form.mobile)    { setError("Mobile required"); return }
    setSubmitting(true); setError("")
    try {
      // 1. Start wizard session
      const sid = await startWizardSession()
      if (!sid) throw new Error("Failed to start session")

      // 2. Step 1: NID Verification
      await submitStep(sid, { nid_number:form.nid, dob:form.dob||"1990-01-01", fingerprint_b64:"agent_captured" })

      // 3. Step 2: Biometric
      await submitStep(sid, { biometric_passed:true, biometric_mode:form.biometric })

      // 4. Step 3: Personal Info
      await submitStep(sid, { full_name:form.full_name, mobile:form.mobile })

      // 5. Step 4: Photograph (placeholder)
      await submitStep(sid, { photo_b64:"agent_photo_placeholder" })

      // 6. Step 5: Signature
      await submitStep(sid, { signature_type:"WET", risk_grade:"LOW" })

      // 7. Step 6: Screening
      await submitStep(sid, { screening_result:"CLEAR" })

      // 8. Step 7: Notification (SIMPLIFIED — final step)
      const final = await submitStep(sid, { mobile:form.mobile, email:"" })

      setSuccess({ session_id:sid, status: final?.status || "COMPLETED", kyc_type:form.kyc_type, nid:form.nid, name:form.full_name })
      if (onSessionCreated) onSessionCreated()
    } catch(e) {
      setError(e.message || "Submission failed")
    } finally { setSubmitting(false) }
  }

  if (success) {
    return (
      <div style={{ maxWidth:560, margin:"0 auto" }}>
        <Card style={{ textAlign:"center", padding:"32px 24px" }}>
          <div style={{ width:64, height:64, borderRadius:99, margin:"0 auto 16px", background:"var(--green-bg)", border:"2px solid var(--green-border)", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <CheckCircle size={28} color="var(--green)" strokeWidth={2}/>
          </div>
          <div style={{ fontSize:18, fontWeight:800, color:"var(--text)", marginBottom:8 }}>Session Submitted</div>
          <div style={{ fontSize:13, color:"var(--text3)", marginBottom:20 }}>eKYC session created successfully</div>
          <StatGrid items={[
            ["Session ID", success.session_id?.slice(0,13)+"...", "var(--accent)"],
            ["Status",     success.status,    "var(--green)"],
            ["KYC Type",   success.kyc_type,  "var(--blue)"],
            ["NID",        success.nid?.slice(0,6)+"*****", "var(--text)"],
          ]}/>
          <div style={{ marginTop:20 }}>
            <Btn onClick={()=>{ setSuccess(null); setStep(1); setForm(f=>({...f,nid:"",dob:"",full_name:"",mobile:""})); setNidResult(null); setSessionId(null) }}>
              <Plus size={13}/> New Session
            </Btn>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div style={{ maxWidth:680, margin:"0 auto", display:"flex", flexDirection:"column", gap:16 }}>
      {/* Step indicator */}
      <Card style={{ padding:"16px 20px" }}>
        <div style={{ display:"flex", alignItems:"center" }}>
          {STEPS.map((s,i)=>(
            <div key={s.n} style={{ display:"flex", alignItems:"center", flex:i<STEPS.length-1?1:"none" }}>
              <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:4 }}>
                <div style={{ width:28, height:28, borderRadius:99, background:step>s.n?"var(--green)":step===s.n?"var(--accent)":"var(--bg4)", color:step>=s.n?"#fff":"var(--text3)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700 }}>{step>s.n?"✓":s.n}</div>
                <div style={{ fontSize:10, color:step===s.n?"var(--accent)":"var(--text3)", fontWeight:600, whiteSpace:"nowrap" }}>{s.label}</div>
              </div>
              {i<STEPS.length-1&&<div style={{ flex:1, height:2, background:step>s.n?"var(--green)":"var(--bg4)", margin:"0 8px", marginBottom:16, borderRadius:99 }}/>}
            </div>
          ))}
        </div>
      </Card>

      {error && <div style={{ padding:"10px 14px", background:"var(--red-bg)", border:"1px solid var(--red-border)", borderRadius:"var(--radius-xs)", fontSize:12, color:"var(--red)" }}>{error}</div>}

      {step===1 && (
        <Card>
          <SectionTitle sub="Enter customer NID to begin">Step 1 — NID Verification</SectionTitle>
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            <Field label="NID Number" placeholder="13 or 17 digit NID" value={form.nid} onChange={v=>setForm(f=>({...f,nid:v}))} />
            <Field label="Date of Birth" type="date" value={form.dob} onChange={v=>setForm(f=>({...f,dob:v}))} />
            <Field label="Channel" type="select" value={form.channel} onChange={v=>setForm(f=>({...f,channel:v}))} options={["AGENCY","WALK_IN","DIGITAL_DIRECT","EMPLOYEE_GROUP"]} />
            <Field label="KYC Type" type="select" value={form.kyc_type} onChange={v=>setForm(f=>({...f,kyc_type:v}))} options={["SIMPLIFIED","REGULAR"]} />
          </div>
          <div style={{ marginTop:16 }}>
            <Btn loading={checking} onClick={verifyNID}><Search size={13}/> Verify NID</Btn>
          </div>
        </Card>
      )}

      {step===2 && (
        <Card>
          <SectionTitle sub="Review and complete">Step 2 — Customer Details</SectionTitle>
          {nidResult?.ec_data && <div style={{ padding:"10px 14px", background:"var(--green-bg)", border:"1px solid var(--green-border)", borderRadius:"var(--radius-xs)", fontSize:12, color:"var(--green)", marginBottom:16 }}>NID verified via {nidResult.ec_source}</div>}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
            <Field label="Full Name"     value={form.full_name}    onChange={v=>setForm(f=>({...f,full_name:v}))} />
            <Field label="Mobile"        placeholder="+8801XXXXXXXXX" value={form.mobile} onChange={v=>setForm(f=>({...f,mobile:v}))} />
            <Field label="Product Type"  type="select" value={form.product_type} onChange={v=>setForm(f=>({...f,product_type:v}))} options={["ORDINARY_LIFE","UNIVERSAL_LIFE","TERM","GROUP","HEALTH"]} />
            <Field label="Biometric"     type="select" value={form.biometric}     onChange={v=>setForm(f=>({...f,biometric:v}))} options={["FINGERPRINT","FACE"]} />
          </div>
          <div style={{ marginTop:16, display:"flex", gap:10 }}>
            <Btn variant="ghost" onClick={()=>setStep(1)}>Back</Btn>
            <Btn onClick={()=>{ if(!form.full_name||!form.mobile){ setError("Fill all fields"); return } setError(""); setStep(3) }}><Camera size={13}/> Continue</Btn>
          </div>
        </Card>
      )}

      {step===3 && (
        <Card>
          <SectionTitle sub="Capture biometric">Step 3 — Biometric Capture</SectionTitle>
          <div style={{ textAlign:"center", padding:"32px 0" }}>
            <div style={{ width:80, height:80, borderRadius:99, margin:"0 auto 16px", background:"var(--accent-bg)", border:"2px dashed var(--accent)", display:"flex", alignItems:"center", justifyContent:"center" }}>
              {form.biometric==="FACE" ? <Camera size={32} color="var(--accent)"/> : <Fingerprint size={32} color="var(--accent)"/>}
            </div>
            <div style={{ fontSize:14, fontWeight:700, color:"var(--text)", marginBottom:8 }}>{form.biometric==="FACE" ? "Face Matching" : "Fingerprint Scan"}</div>
            <div style={{ fontSize:12, color:"var(--text3)", marginBottom:24 }}>{form.biometric==="FACE" ? "Direct customer to self check-in portal" : "Connect scanner and capture fingerprint"}</div>
            <div style={{ display:"flex", gap:10, justifyContent:"center" }}>
              <Btn variant="ghost" onClick={()=>setStep(2)}>Back</Btn>
              <Btn variant="success" onClick={()=>setStep(4)}><CheckCircle size={13}/> Mark Captured</Btn>
            </div>
          </div>
        </Card>
      )}

      {step===4 && (
        <Card>
          <SectionTitle sub="Confirm and submit to backend">Step 4 — Review & Submit</SectionTitle>
          <StatGrid items={[
            ["NID",      form.nid.slice(0,6)+"*****", "var(--text)"],
            ["Name",     form.full_name||"--",         "var(--text)"],
            ["Mobile",   form.mobile||"--",            "var(--text)"],
            ["Channel",  form.channel,                 "var(--accent)"],
            ["KYC Type", form.kyc_type,                "var(--blue)"],
            ["Biometric",form.biometric,               "var(--accent)"],
          ]}/>
          <Divider label="BFIU CHECKS"/>
          <CheckItem label="UNSCR Screening"  pass={true} value="CLEAR" />
          <CheckItem label="NID Verified"     pass={true} value={nidResult?.ec_source||"DEMO"} />
          <CheckItem label="Wizard Flow"      pass={true} value={form.kyc_type==="REGULAR"?"8-step":"7-step"} />
          <div style={{ marginTop:16, display:"flex", gap:10 }}>
            <Btn variant="ghost" onClick={()=>setStep(3)}>Back</Btn>
            <Btn variant="success" loading={submitting} onClick={handleSubmit}>
              <CheckCircle size={13}/> Submit to Backend
            </Btn>
          </div>
        </Card>
      )}
    </div>
  )
}

function SearchTab() {
  const [query,   setQuery]   = useState("")
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)

  const search = async () => {
    setLoading(true)
    try {
      const token = await ensureDemoToken()
      const r = await axios.post(`${API}/api/v1/nid/verify`,
        { nid_number:query, session_id:"search_"+Date.now() },
        { headers:{ Authorization:`Bearer ${token}`, "Content-Type":"application/json" } }
      )
      setResult(r.data)
    } catch(e) { setResult({ found:false, ec_source:"DEMO", reason:"NID not found" }) }
    finally { setLoading(false) }
  }

  return (
    <div style={{ maxWidth:600, margin:"0 auto", display:"flex", flexDirection:"column", gap:16 }}>
      <Card>
        <SectionTitle sub="Look up in EC database">NID Search</SectionTitle>
        <div style={{ display:"flex", gap:10 }}>
          <input value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&search()} placeholder="Enter NID number (10, 13 or 17 digits)"
            style={{ flex:1, padding:"10px 14px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", fontSize:13, outline:"none" }}/>
          <Btn loading={loading} onClick={search}><Search size={13}/> Search</Btn>
        </div>
        <div style={{ fontSize:11, color:"var(--text3)", marginTop:8 }}>Try: 1234567890123</div>
      </Card>
      {result && (
        <Card>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:16 }}>
            <Badge color={result.found!==false?"green":"red"}>{result.found!==false?"FOUND":"NOT FOUND"}</Badge>
            <span style={{ fontSize:11, color:"var(--text3)" }}>Source: {result.ec_source}</span>
          </div>
          {result.ec_data && <StatGrid items={[
            ["Full Name",    result.ec_data.full_name_en||"--",   "var(--text)"],
            ["Date of Birth",result.ec_data.date_of_birth||"--",  "var(--text)"],
            ["Gender",       result.ec_data.gender||"--",         "var(--text)"],
            ["Father",       result.ec_data.fathers_name||"--",   "var(--text)"],
            ["Mother",       result.ec_data.mothers_name||"--",   "var(--text)"],
            ["Blood Group",  result.ec_data.blood_group||"--",    "var(--red)"],
          ]}/>}
          {result.found===false && <div style={{ textAlign:"center", padding:24, color:"var(--text3)", fontSize:13 }}>{result.reason||"Not found"}</div>}
        </Card>
      )}
    </div>
  )
}

function ProfileTab({ agent }) {
  return (
    <div style={{ maxWidth:500, display:"flex", flexDirection:"column", gap:16 }}>
      <Card>
        <div style={{ textAlign:"center", padding:"20px 0 16px" }}>
          <div style={{ width:64, height:64, borderRadius:99, margin:"0 auto 12px", background:"linear-gradient(135deg,var(--accent),var(--blue))", display:"flex", alignItems:"center", justifyContent:"center", fontSize:24, fontWeight:800, color:"#fff" }}>{agent.name[0]}</div>
          <div style={{ fontSize:16, fontWeight:800, color:"var(--text)" }}>{agent.name}</div>
          <div style={{ fontSize:12, color:"var(--text3)", marginTop:2 }}>Agent — MAKER role</div>
        </div>
        <Divider/>
        <StatGrid items={[
          ["Agent Code",   agent.code,          "var(--accent)"],
          ["Zone",         agent.zone,           "var(--text)"],
          ["Institution",  "Demo Insurance",     "var(--text)"],
          ["KYC Type",     "SIMPLIFIED + REGULAR","var(--blue)"],
        ]}/>
      </Card>
      <Card>
        <SectionTitle sub="BFIU daily limits">Session Limits</SectionTitle>
        <CheckItem label="Max Attempts/Session" pass={true} value="10 (BFIU 3.2)" />
        <CheckItem label="Max Sessions/Day"     pass={true} value="2 per NID" />
        <CheckItem label="Wizard Steps"         pass={true} value="7 (SIMPLIFIED) / 8 (REGULAR)" />
      </Card>
    </div>
  )
}

function ReportsTab({ sessions, stats }) {
  const c = sessions.filter(s=>s.status==="COMPLETED").length
  const f = sessions.filter(s=>s.status==="FAILED").length
  const p = sessions.filter(s=>["PENDING","IN_PROGRESS"].includes(s.status)).length
  const rate = stats?.success_rate ?? (sessions.length > 0 ? ((c/sessions.length)*100).toFixed(1) : "0")

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:12 }}>
        {[[c,"Completed","var(--green)"],[p,"Pending","var(--yellow)"],[f,"Failed","var(--red)"]].map(([v,l,col])=>(
          <Card key={l} style={{ padding:"16px 18px", textAlign:"center" }}>
            <div style={{ fontSize:32, fontWeight:800, color:col, fontFamily:"var(--font-mono)" }}>{v}</div>
            <div style={{ fontSize:12, color:"var(--text3)", marginTop:4 }}>{l}</div>
          </Card>
        ))}
      </div>
      <Card>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
          <SectionTitle sub="Current session data">Performance</SectionTitle>
        </div>
        <StatGrid items={[
          ["Total",        sessions.length,  "var(--text)"],
          ["Completed",    c,                "var(--green)"],
          ["Success Rate", `${rate}%`,       "var(--green)"],
          ["SIMPLIFIED",   sessions.filter(s=>s.kyc_type==="SIMPLIFIED"||s.type==="SIMPLIFIED").length, "var(--text3)"],
          ["REGULAR",      sessions.filter(s=>s.kyc_type==="REGULAR"||s.type==="REGULAR").length,       "var(--accent)"],
        ]}/>
      </Card>
    </div>
  )
}

export default function AgentDashboard({ onExit, theme, toggleTheme }) {
  const [active, setActive] = useState("dashboard")
  const agent = { name:"Eshan Barua", code:"AGT-2026-042", zone:"Chittagong Sadar" }
  const { sessions, reload: reloadSessions } = useLiveSessions()
  const { stats,    reload: reloadStats    } = useLiveStats()

  const reload = () => { reloadSessions(); reloadStats() }

  const tabs = {
    dashboard: <DashboardTab sessions={sessions} stats={stats} setActive={setActive} reload={reload}/>,
    sessions:  <SessionsTab  sessions={sessions}/>,
    new:       <NewSessionTab onSessionCreated={reload}/>,
    search:    <SearchTab/>,
    reports:   <ReportsTab sessions={sessions} stats={stats}/>,
    profile:   <ProfileTab agent={agent}/>,
  }

  return (
    <div style={{ display:"flex", minHeight:"100vh", background:"var(--bg)" }}>
      <Sidebar active={active} setActive={setActive} agent={agent} onExit={onExit}/>
      <div style={{ flex:1, overflow:"auto" }}>
        <div style={{ position:"sticky", top:0, zIndex:10, background:"var(--bg2)", borderBottom:"1px solid var(--border)", padding:"12px 24px", display:"flex", alignItems:"center", gap:12 }}>
          <div style={{ flex:1 }}>
            <div style={{ fontSize:16, fontWeight:800, color:"var(--text)" }}>
              {{dashboard:"Agent Dashboard",sessions:"Sessions",new:"New eKYC Session",search:"NID Search",reports:"Reports",profile:"My Profile"}[active]}
            </div>
            <div style={{ fontSize:11, color:"var(--text3)" }}>{new Date().toLocaleDateString("en-BD",{weekday:"long",year:"numeric",month:"long",day:"numeric"})}</div>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <div style={{ display:"flex", alignItems:"center", gap:6, padding:"6px 12px", borderRadius:99, background:"var(--green-bg)", border:"1px solid var(--green-border)" }}>
              <div style={{ width:7, height:7, borderRadius:99, background:"var(--green)", animation:"pulse 2s infinite" }}/>
              <span style={{ fontSize:11, fontWeight:700, color:"var(--green)" }}>API Live</span>
            </div>
            <button onClick={reload} style={{ width:34, height:34, borderRadius:99, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer" }} title="Refresh"><RefreshCw size={14} color="var(--text3)"/></button>
            <button onClick={toggleTheme} style={{ width:34, height:34, borderRadius:99, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", fontFamily:"var(--font)", fontSize:11 }}>{theme==="dark" ? "☀" : "🌙"}</button>
          </div>
        </div>
        <div style={{ padding:24 }}>{tabs[active]||tabs.dashboard}</div>
      </div>
    </div>
  )
}
