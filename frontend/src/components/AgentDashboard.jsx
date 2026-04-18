import { useState } from "react"
import { Card, Btn, Badge, Spinner, SectionTitle, StatGrid, Divider, CheckItem } from "./ui"
import { API } from "../config.js"
import axios from "axios"
import {
  Users, Shield, FileText, Search, Bell, LogOut, ChevronRight,
  Plus, Eye, CheckCircle, XCircle, Clock, AlertTriangle,
  User, Phone, MapPin, Calendar, Fingerprint, Camera,
  TrendingUp, Activity, RefreshCw, Download, Filter,
  ChevronDown, Zap
} from "lucide-react"

const MOCK_SESSIONS = [
  { id:"S-2026-001", name:"Karim Uddin Ahmed",     nid:"1234567890123", type:"REGULAR",    status:"COMPLETED",   risk:"LOW",    time:"09:14", channel:"AGENCY",  verdict:"MATCHED",  confidence:72.4 },
  { id:"S-2026-002", name:"Fatema Begum",           nid:"9876543210987", type:"SIMPLIFIED", status:"PENDING",    risk:"MEDIUM", time:"09:41", channel:"WALK_IN", verdict:"REVIEW",   confidence:38.1 },
  { id:"S-2026-003", name:"Mohammad Hossain",       nid:"1111111111111", type:"REGULAR",    status:"FAILED",     risk:"HIGH",   time:"10:02", channel:"AGENCY",  verdict:"FAILED",   confidence:12.3 },
  { id:"S-2026-004", name:"Nasrin Sultana",          nid:"2222222222222", type:"SIMPLIFIED", status:"COMPLETED",  risk:"LOW",    time:"10:28", channel:"DIGITAL", verdict:"MATCHED",  confidence:81.9 },
  { id:"S-2026-005", name:"Abdul Rahman Chowdhury",  nid:"3333333333333", type:"REGULAR",    status:"COMPLETED",  risk:"MEDIUM", time:"11:05", channel:"AGENCY",  verdict:"MATCHED",  confidence:65.2 },
  { id:"S-2026-006", name:"Rohima Khatun",           nid:"4444444444444", type:"SIMPLIFIED", status:"IN_PROGRESS",risk:"LOW",    time:"11:33", channel:"WALK_IN", verdict:null,        confidence:null },
]
const MOCK_STATS = { today:{ total:6, completed:4, pending:1, failed:1 }, week:{ total:38, completed:31 }, success_rate:89.2, avg_time:"4m 22s" }
const statusColor = s => ({ COMPLETED:"green", PENDING:"yellow", FAILED:"red", IN_PROGRESS:"accent" }[s] || "accent")
const riskColor   = r => ({ LOW:"green", MEDIUM:"yellow", HIGH:"red" }[r] || "accent")
const verdictColor= v => ({ MATCHED:"green", REVIEW:"yellow", FAILED:"red" }[v] || "accent")

function Field({ label, type="text", value, onChange, placeholder, options }) {
  const base = { width:"100%", padding:"9px 12px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", fontSize:13, outline:"none" }
  return (
    <div>
      <label style={{ fontSize:11, fontWeight:600, color:"var(--text3)", display:"block", marginBottom:5, textTransform:"uppercase", letterSpacing:"0.05em" }}>{label}</label>
      {type === "select"
        ? <select value={value} onChange={e => onChange(e.target.value)} style={base}>{options.map(o => <option key={o} value={o}>{o.replace(/_/g," ")}</option>)}</select>
        : <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={base} onFocus={e=>e.target.style.borderColor="var(--accent)"} onBlur={e=>e.target.style.borderColor="var(--border)"} />}
    </div>
  )
}

function Sidebar({ active, setActive, agent }) {
  const nav = [
    { id:"dashboard", icon:Activity,     label:"Dashboard" },
    { id:"sessions",  icon:Users,        label:"Sessions" },
    { id:"new",       icon:Plus,         label:"New Session", accent:true },
    { id:"search",    icon:Search,       label:"NID Search" },
    { id:"reports",   icon:FileText,     label:"My Reports" },
    { id:"profile",   icon:User,         label:"My Profile" },
  ]
  return (
    <div style={{ width:220, flexShrink:0, background:"var(--bg2)", borderRight:"1px solid var(--border)", display:"flex", flexDirection:"column", height:"100vh", position:"sticky", top:0 }}>
      <div style={{ padding:"20px 20px 16px", borderBottom:"1px solid var(--border)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:34, height:34, borderRadius:10, background:"linear-gradient(135deg,var(--accent),var(--blue))", display:"flex", alignItems:"center", justifyContent:"center", boxShadow:"0 4px 12px rgba(99,88,255,0.3)" }}><Shield size={16} color="#fff" strokeWidth={2.5}/></div>
          <div><div style={{ fontSize:13, fontWeight:800, color:"var(--text)" }}>Xpert eKYC</div><div style={{ fontSize:10, color:"var(--text3)" }}>Agent Portal</div></div>
        </div>
      </div>
      <nav style={{ flex:1, padding:"12px 10px", overflowY:"auto" }}>
        {nav.map(({ id, icon:Icon, label, accent }) => {
          const on = active === id
          return (
            <button key={id} onClick={() => setActive(id)} style={{ width:"100%", display:"flex", alignItems:"center", gap:10, padding:"9px 12px", borderRadius:"var(--radius-sm)", marginBottom:2, background: on?(accent?"var(--accent)":"var(--accent-bg)"):accent?"var(--accent-bg)":"transparent", border: on&&accent?"none":on?"1px solid rgba(99,88,255,0.2)":"1px solid transparent", color: on?(accent?"#fff":"var(--accent)"):accent?"var(--accent)":"var(--text2)", fontFamily:"var(--font)", fontSize:13, fontWeight:on?700:500, cursor:"pointer", transition:"all 0.15s", textAlign:"left" }}
              <Icon size={15} strokeWidth={on?2.5:2}/>{label}{id==="new"&&<Zap size={11} style={{marginLeft:"auto"}} strokeWidth={2.5}/>}
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
        <button style={{ width:"100%", display:"flex", alignItems:"center", justifyContent:"center", gap:6, padding:7, borderRadius:"var(--radius-xs)", background:"var(--red-bg)", color:"var(--red)", border:"1px solid var(--red-border)", fontFamily:"var(--font)", fontSize:11, fontWeight:600, cursor:"pointer" }}><LogOut size={12}/> Sign Out</button>
      </div>
    </div>
  )
}

function SessionRow({ session:s, compact, onClick }) {
  return (
    <div onClick={onClick} style={{ display:"flex", alignItems:"center", gap:12, padding:compact?"10px 12px":"12px 16px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)", cursor:onClick?"pointer":"default", transition:"all 0.15s" }}
    onMouseEnter={e=>{ if(onClick) e.currentTarget.style.borderColor="var(--accent)" }} onMouseLeave={e=>{ e.currentTarget.style.borderColor="var(--border)" }}>
      <div style={{ width:36, height:36, borderRadius:99, flexShrink:0, background:"var(--accent-bg)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:13, fontWeight:700, color:"var(--accent)" }}>{s.name[0]}</div>
      <div style={{ flex:1, minWidth:0 }}>
        <div style={{ fontSize:12, fontWeight:700, color:"var(--text)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{s.name}</div>
        <div style={{ fontSize:11, color:"var(--text3)", marginTop:1 }}>{s.id} · {s.channel}</div>
      </div>
      <div style={{ display:"flex", alignItems:"center", gap:8, flexShrink:0 }}>
        <Badge color={riskColor(s.risk)}>{s.risk}</Badge>
        <Badge color={statusColor(s.status)}>{s.status.replace("_"," ")}</Badge>
        <span style={{ fontSize:11, color:"var(--text3)", fontFamily:"var(--font-mono)" }}>{s.time}</span>
      </div>
    </div>
  )
}

function SessionDetail({ session:s, onBack }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <div style={{ display:"flex", alignItems:"center", gap:12 }}>
        <Btn variant="ghost" size="sm" onClick={onBack}>Back</Btn>
        <span style={{ fontSize:14, fontWeight:700, color:"var(--text)" }}>{s.name}</span>
        <Badge color={statusColor(s.status)}>{s.status}</Badge>
        {s.verdict && <Badge color={verdictColor(s.verdict)}>{s.verdict}</Badge>}
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        <Card>
          <SectionTitle sub="KYC session details">Session Info</SectionTitle>
          <StatGrid items={[
            ["Session ID",s.id,"var(--text)"],["NID Number",s.nid.slice(0,6)+"*****","var(--text)"],
            ["Channel",s.channel,"var(--accent)"],["KYC Type",s.type,"var(--blue)"],
            ["Risk Grade",s.risk,s.risk==="LOW"?"var(--green)":s.risk==="HIGH"?"var(--red)":"var(--yellow)"],["Time",s.time,"var(--text3)"],
          ]}/>
        </Card>
        <Card>
          <SectionTitle sub="Biometric result">Verification Result</SectionTitle>
          {s.confidence ? (
            <div>
              <div style={{ textAlign:"center", padding:"20px 0" }}>
                <div style={{ fontSize:48, fontWeight:800, fontFamily:"var(--font-mono)", color:s.confidence>=45?"var(--green)":s.confidence>=25?"var(--yellow)":"var(--red)" }}>{s.confidence}%</div>
                <div style={{ fontSize:12, color:"var(--text3)", marginTop:4 }}>Confidence Score</div>
              </div>
              <CheckItem label="Face Detected" pass={true} value="Both faces" />
              <CheckItem label="Liveness Check" pass={s.status!=="FAILED"} value="4/4 checks" />
              <CheckItem label="UNSCR Screening" pass={true} value="CLEAR" />
            </div>
          ) : (
            <div style={{ textAlign:"center", padding:32, color:"var(--text3)" }}>
              <Activity size={24} style={{ marginBottom:8 }} /><div style={{ fontSize:13 }}>Session in progress</div>
            </div>
          )}
        </Card>
      </div>
      {s.status==="PENDING" && (
        <Card style={{ padding:"16px 20px" }}>
          <SectionTitle sub="Send for review">Actions</SectionTitle>
          <div style={{ display:"flex", gap:10 }}>
            <Btn variant="success"><CheckCircle size={13}/> Approve</Btn>
            <Btn variant="danger"><XCircle size={13}/> Reject</Btn>
            <Btn variant="ghost"><RefreshCw size={13}/> Re-verify</Btn>
          </div>
        </Card>
      )}
    </div>
  )
}

function SessionsTab({ sessions }) {
  const [filter, setFilter] = useState("ALL")
  const [selected, setSelected] = useState(null)
  const filters = ["ALL","COMPLETED","PENDING","FAILED","IN_PROGRESS"]
  const filtered = filter==="ALL" ? sessions : sessions.filter(s=>s.status===filter)
  if (selected) return <SessionDetail session={selected} onBack={()=>setSelected(null)} />
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
      <Card style={{ padding:"12px 16px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap" }}>
          <Filter size={13} color="var(--text3)" />
          {filters.map(f => (
            <button key={f} onClick={()=>setFilter(f)} style={{ padding:"5px 12px", borderRadius:99, background:filter===f?"var(--accent)":"var(--bg3)", color:filter===f?"#fff":"var(--text3)", border:filter===f?"none":"1px solid var(--border)", fontSize:11, fontWeight:600, cursor:"pointer", fontFamily:"var(--font)" }}>{f.replace("_"," ")}</button>
          ))}
          <span style={{ marginLeft:"auto", fontSize:11, color:"var(--text3)" }}>{filtered.length} sessions</span>
        </div>
      </Card>
      <Card>
        <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
          {filtered.map(s=><SessionRow key={s.id} session={s} onClick={()=>setSelected(s)} />)}
          {filtered.length===0 && <div style={{ textAlign:"center", padding:32, color:"var(--text3)", fontSize:13 }}>No sessions found</div>}
        </div>
      </Card>
    </div>
  )
}

function DashboardTab({ sessions, setActive }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
        {[
          { label:"Today Sessions", value:MOCK_STATS.today.total,    color:"var(--accent)", icon:Activity },
          { label:"Completed",      value:MOCK_STATS.today.completed,color:"var(--green)",  icon:CheckCircle },
          { label:"Pending Review", value:MOCK_STATS.today.pending,  color:"var(--yellow)", icon:Clock },
          { label:"Success Rate",   value:,color:"var(--blue)",icon:TrendingUp },
        ].map(({ label,value,color,icon:Icon })=>(
          <Card key={label} style={{ padding:"16px 18px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
              <div>
                <div style={{ fontSize:10, color:"var(--text3)", fontWeight:600, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:6 }}>{label}</div>
                <div style={{ fontSize:26, fontWeight:800, color, fontFamily:"var(--font-mono)", lineHeight:1 }}>{value}</div>
              </div>
              <div style={{ width:36, height:36, borderRadius:10, background:, display:"flex", alignItems:"center", justifyContent:"center" }}><Icon size={16} color={color} strokeWidth={2}/></div>
            </div>
          </Card>
        ))}
      </div>
      <Card style={{ padding:"16px 20px" }}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}><SectionTitle sub="Start or continue work">Quick Actions</SectionTitle></div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
          {[
            { label:"Start New eKYC",  sub:"Fingerprint or Face", color:"var(--accent)", icon:Plus,        action:"new" },
            { label:"Search NID",      sub:"Look up existing",    color:"var(--blue)",  icon:Search,      action:"search" },
            { label:"Pending Reviews", sub:"1 awaiting checker",  color:"var(--yellow)",icon:Clock,       action:"sessions" },
          ].map(({ label,sub,color,icon:Icon,action })=>(
            <button key={label} onClick={()=>setActive(action)} style={{ padding:"14px 16px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)", textAlign:"left", cursor:"pointer", transition:"all 0.15s", fontFamily:"var(--font)" }}
            onMouseEnter={e=>{ e.currentTarget.style.borderColor=color; e.currentTarget.style.background="var(--bg4)" }}
            onMouseLeave={e=>{ e.currentTarget.style.borderColor="var(--border)"; e.currentTarget.style.background="var(--bg3)" }}>
              <div style={{ width:30, height:30, borderRadius:8, background:, display:"flex", alignItems:"center", justifyContent:"center", marginBottom:10 }}><Icon size={14} color={color} strokeWidth={2.5}/></div>
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
          {sessions.slice(0,4).map(s=><SessionRow key={s.id} session={s} compact />)}
        </div>
      </Card>
    </div>
  )
}

function NewSessionTab() {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({ nid:"", dob:"", channel:"AGENCY", kyc_type:"SIMPLIFIED", product_type:"ORDINARY_LIFE", full_name:"", mobile:"", biometric:"FACE" })
  const [checking, setChecking] = useState(false)
  const [nidResult, setNidResult] = useState(null)
  const [error, setError] = useState("")
  const STEPS = [{n:1,label:"NID Verify"},{n:2,label:"Customer"},{n:3,label:"Biometric"},{n:4,label:"Submit"}]

  const verifyNID = async () => {
    setChecking(true); setError("")
    try {
      const r = await axios.post(API+"/api/v1/nid/verify", { nid_number:form.nid, session_id:"agent_"+Date.now() }, { headers:{ Authorization:"Bearer demo-token" }})
      setNidResult(r.data)
      if (r.data.ec_data) setForm(f=>({...f, full_name:r.data.ec_data.full_name_en||""}))
      setStep(2)
    } catch(e) {
      setNidResult({ ec_source:"DEMO", ec_data:{ full_name_en:"Demo Customer", date_of_birth:"1990-01-01" }})
      setStep(2)
    } finally { setChecking(false) }
  }

  return (
    <div style={{ maxWidth:680, margin:"0 auto", display:"flex", flexDirection:"column", gap:16 }}>
      <Card style={{ padding:"16px 20px" }}>
        <div style={{ display:"flex", alignItems:"center" }}>
          {STEPS.map((s,i)=>(
            <div key={s.n} style={{ display:"flex", alignItems:"center", flex:i<STEPS.length-1?1:"none" }}>
              <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:4 }}>
                <div style={{ width:28, height:28, borderRadius:99, background:step>s.n?"var(--green)":step===s.n?"var(--accent)":"var(--bg4)", color:step>=s.n?"#fff":"var(--text3)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700 }}>{step>s.n?"v":s.n}</div>
                <div style={{ fontSize:10, color:step===s.n?"var(--accent)":"var(--text3)", fontWeight:600, whiteSpace:"nowrap" }}>{s.label}</div>
              </div>
              {i<STEPS.length-1&&<div style={{ flex:1, height:2, background:step>s.n?"var(--green)":"var(--bg4)", margin:"0 8px", marginBottom:16, borderRadius:99 }}/>}
            </div>
          ))}
        </div>
      </Card>
      {step===1&&(
        <Card>
          <SectionTitle sub="Enter customer NID to begin">Step 1 - NID Verification</SectionTitle>
          {error&&<div style={{ padding:"10px 14px", background:"var(--red-bg)", border:"1px solid var(--red-border)", borderRadius:"var(--radius-xs)", fontSize:12, color:"var(--red)", marginBottom:12 }}>{error}</div>}
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            <Field label="NID Number" placeholder="13 or 17 digit NID" value={form.nid} onChange={v=>setForm(f=>({...f,nid:v}))} />
            <Field label="Date of Birth" type="date" value={form.dob} onChange={v=>setForm(f=>({...f,dob:v}))} />
            <Field label="Channel" type="select" value={form.channel} onChange={v=>setForm(f=>({...f,channel:v}))} options={["AGENCY","WALK_IN","DIGITAL_DIRECT","EMPLOYEE_GROUP"]} />
            <Field label="KYC Type" type="select" value={form.kyc_type} onChange={v=>setForm(f=>({...f,kyc_type:v}))} options={["SIMPLIFIED","REGULAR"]} />
          </div>
          <div style={{ marginTop:16 }}><Btn loading={checking} onClick={verifyNID}><Search size={13}/> Verify NID</Btn></div>
        </Card>
      )}
      {step===2&&(
        <Card>
          <SectionTitle sub="Review and complete">Step 2 - Customer Details</SectionTitle>
          {nidResult?.ec_data&&<div style={{ padding:"10px 14px", background:"var(--green-bg)", border:"1px solid var(--green-border)", borderRadius:"var(--radius-xs)", fontSize:12, color:"var(--green)", marginBottom:16 }}>NID verified via {nidResult.ec_source}</div>}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
            <Field label="Full Name" value={form.full_name} onChange={v=>setForm(f=>({...f,full_name:v}))} />
            <Field label="Mobile" placeholder="+8801XXXXXXXXX" value={form.mobile} onChange={v=>setForm(f=>({...f,mobile:v}))} />
            <Field label="Product Type" type="select" value={form.product_type} onChange={v=>setForm(f=>({...f,product_type:v}))} options={["ORDINARY_LIFE","UNIVERSAL_LIFE","TERM","GROUP","HEALTH"]} />
            <Field label="Biometric" type="select" value={form.biometric} onChange={v=>setForm(f=>({...f,biometric:v}))} options={["FACE","FINGERPRINT"]} />
          </div>
          <div style={{ marginTop:16, display:"flex", gap:10 }}>
            <Btn variant="ghost" onClick={()=>setStep(1)}>Back</Btn>
            <Btn onClick={()=>setStep(3)}><Camera size={13}/> Continue</Btn>
          </div>
        </Card>
      )}
      {step===3&&(
        <Card>
          <SectionTitle sub="Capture biometric">Step 3 - Biometric</SectionTitle>
          <div style={{ textAlign:"center", padding:"32px 0" }}>
            <div style={{ width:80, height:80, borderRadius:99, margin:"0 auto 16px", background:"var(--accent-bg)", border:"2px dashed var(--accent)", display:"flex", alignItems:"center", justifyContent:"center" }}>
              {form.biometric==="FACE"?<Camera size={32} color="var(--accent)"/>:<Fingerprint size={32} color="var(--accent)"/>}
            </div>
            <div style={{ fontSize:14, fontWeight:700, color:"var(--text)", marginBottom:8 }}>{form.biometric==="FACE"?"Face Matching":"Fingerprint Scan"}</div>
            <div style={{ fontSize:12, color:"var(--text3)", marginBottom:24 }}>{form.biometric==="FACE"?"Direct customer to self check-in portal":"Connect scanner and capture fingerprint"}</div>
            <div style={{ display:"flex", gap:10, justifyContent:"center" }}>
              <Btn variant="ghost" onClick={()=>setStep(2)}>Back</Btn>
              <Btn variant="success" onClick={()=>setStep(4)}><CheckCircle size={13}/> Mark Captured</Btn>
            </div>
          </div>
        </Card>
      )}
      {step===4&&(
        <Card>
          <SectionTitle sub="Confirm and submit">Step 4 - Review</SectionTitle>
          <StatGrid items={[
            ["NID",form.nid.slice(0,6)+"*****","var(--text)"],["Name",form.full_name||"--","var(--text)"],
            ["Mobile",form.mobile||"--","var(--text)"],["Channel",form.channel,"var(--accent)"],
            ["KYC Type",form.kyc_type,"var(--blue)"],["Biometric",form.biometric,"var(--accent)"],
          ]}/>
          <Divider label="BFIU CHECKS"/>
          <CheckItem label="UNSCR Screening" pass={true} value="CLEAR" />
          <CheckItem label="NID Verified" pass={true} value={nidResult?.ec_source||"DEMO"} />
          <CheckItem label="Session Limit" pass={true} value="1/2 today" />
          <div style={{ marginTop:16, display:"flex", gap:10 }}>
            <Btn variant="ghost" onClick={()=>setStep(3)}>Back</Btn>
            <Btn variant="success" onClick={()=>{ setStep(1); setForm(f=>({...f,nid:"",dob:"",full_name:"",mobile:""})); setNidResult(null) }}><CheckCircle size={13}/> Submit</Btn>
          </div>
        </Card>
      )}
    </div>
  )
}

function SearchTab() {
  const [query, setQuery] = useState("")
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const search = async () => {
    try {
      const r = await axios.post(API+"/api/v1/nid/verify", { nid_number:query, session_id:"search_"+Date.now() }, { headers:{ Authorization:"Bearer demo-token" }})
      setResult(r.data)
    } catch(e) { setResult({ found:false, ec_source:"DEMO", reason:"NID not found" }) }
    finally { setLoading(false) }
  }
  return (
    <div style={{ maxWidth:600, margin:"0 auto", display:"flex", flexDirection:"column", gap:16 }}>
      <Card>
        <SectionTitle sub="Look up in EC database">NID Search</SectionTitle>
        <div style={{ display:"flex", gap:10 }}>
          <input value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&search()} placeholder="Enter NID number (10, 13 or 17 digits)" style={{ flex:1, padding:"10px 14px", borderRadius:"var(--radius-sm)", background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", fontSize:13, outline:"none" }}/>
          <Btn loading={loading} onClick={search}><Search size={13}/> Search</Btn>
        </div>
        <div style={{ fontSize:11, color:"var(--text3)", marginTop:8 }}>Try: 1234567890123 or 9876543210987</div>
      </Card>
      {result&&(
        <Card>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:16 }}>
            <Badge color={result.found!==false?"green":"red"}>{result.found!==false?"FOUND":"NOT FOUND"}</Badge>
            <span style={{ fontSize:11, color:"var(--text3)" }}>Source: {result.ec_source}</span>
          </div>
          {result.ec_data&&<StatGrid items={[["Full Name",result.ec_data.full_name_en||"--","var(--text)"],["Date of Birth",result.ec_data.date_of_birth||"--","var(--text)"],["Gender",result.ec_data.gender||"--","var(--text)"],["Father",result.ec_data.fathers_name||"--","var(--text)"],["Mother",result.ec_data.mothers_name||"--","var(--text)"],["Blood Group",result.ec_data.blood_group||"--","var(--red)"],]}/>}
          {result.found===false&&<div style={{ textAlign:"center", padding:24, color:"var(--text3)", fontSize:13 }}>{result.reason||"Not found"}</div>}
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
          <div style={{ fontSize:12, color:"var(--text3)", marginTop:2 }}>Agent - MAKER role</div>
        </div>
        <Divider/>
        <StatGrid items={[["Agent Code",agent.code,"var(--accent)"],["Zone",agent.zone,"var(--text)"],["Institution","Demo Insurance","var(--text)"],["Sessions Today","6","var(--blue)"],["This Month","38","var(--text)"],["Success Rate","89.2%","var(--green)"],]}/>
      </Card>
      <Card>
        <SectionTitle sub="BFIU daily limits">Session Limits</SectionTitle>
        <CheckItem label="Max Attempts/Session" pass={true} value="10 (BFIU 3.2)" />
        <CheckItem label="Max Sessions/Day" pass={true} value="2 per NID" />
        <CheckItem label="Today Sessions" pass={true} value="6 completed" />
      </Card>
    </div>
  )
}

function ReportsTab({ sessions }) {
  const c=sessions.filter(s=>s.status==="COMPLETED").length
  const f=sessions.filter(s=>s.status==="FAILED").length
  const p=sessions.filter(s=>s.status==="PENDING").length
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
          <SectionTitle sub="This week">Performance</SectionTitle>
          <Btn variant="ghost" size="sm"><Download size={12}/> Export</Btn>
        </div>
        <StatGrid items={[["Total",MOCK_STATS.week.total,"var(--text)"],["Verified",MOCK_STATS.week.completed,"var(--green)"],["Success Rate",MOCK_STATS.success_rate+"%","var(--green)"],["Avg Time",MOCK_STATS.avg_time,"var(--blue)"],["REGULAR","12","var(--accent)"],["SIMPLIFIED","26","var(--text3)"],]}/>
      </Card>
    </div>
  )
}

export default function AgentDashboard() {
  const [active, setActive] = useState("dashboard")
  const agent = { name:"Eshan Barua", code:"AGT-2026-042", zone:"Chittagong Sadar" }
  const tabs = { dashboard:<DashboardTab sessions={MOCK_SESSIONS} setActive={setActive}/>, sessions:<SessionsTab sessions={MOCK_SESSIONS}/>, new:<NewSessionTab/>, search:<SearchTab/>, reports:<ReportsTab sessions={MOCK_SESSIONS}/>, profile:<ProfileTab agent={agent}/> }
  return (
    <div style={{ display:"flex", minHeight:"100vh", background:"var(--bg)" }}>
      <Sidebar active={active} setActive={setActive} agent={agent}/>
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
            <button style={{ width:34, height:34, borderRadius:99, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer" }}><Bell size={14} color="var(--text3)"/></button>
          </div>
        </div>
        <div style={{ padding:24 }}>{tabs[active]||tabs.dashboard}</div>
      </div>
    </div>
  )
}
