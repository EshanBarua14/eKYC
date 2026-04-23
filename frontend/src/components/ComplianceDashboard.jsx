
import { useState, useEffect, useCallback } from "react"
import {
  ChevronLeft, Shield, RefreshCw, Download,
  AlertTriangle, Users, Activity, XCircle,
  ClipboardList, TrendingUp, Eye,
} from "lucide-react"
import { Card, Btn, Badge, Spinner, SectionTitle, StatGrid, Divider } from "./ui"
import { API } from "../config"

const TABS = [
  { id:"posture",   label:"Posture",          icon: Activity      },
  { id:"queues",    label:"KYC Queues",        icon: Users         },
  { id:"edd",       label:"EDD Cases",         icon: AlertTriangle },
  { id:"screening", label:"Screening Hits",    icon: Eye           },
  { id:"failed",    label:"Failed Onboarding", icon: XCircle       },
  { id:"export",    label:"BFIU Export",       icon: Download      },
]

async function apiFetch(path) {
  const r = await fetch(`${API}${path}`)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

function TabNav({ active, setActive }) {
  return (
    <div style={{ display:"flex", gap:4, padding:4, background:"var(--bg3)",
                  borderRadius:"var(--radius)", border:"1px solid var(--border)", flexWrap:"wrap", overflowX:"auto", scrollbarWidth:"none" }}>
      {TABS.map(t => {
        const Icon = t.icon; const on = active === t.id
        return (
          <button key={t.id} onClick={() => setActive(t.id)} style={{
            display:"flex", alignItems:"center", gap:6, padding:"8px 14px",
            borderRadius:"var(--radius-sm)", fontSize:12, fontWeight:700,
            fontFamily:"var(--font)", border:"none", cursor:"pointer", transition:"all 0.15s",
            background: on ? "var(--accent)" : "transparent",
            color: on ? "#fff" : "var(--text2)",
          }}>
            <Icon size={13} strokeWidth={2.2}/>{t.label}
          </button>
        )
      })}
    </div>
  )
}

const GRADE_COLOR = { HIGH:"red", MEDIUM:"yellow", LOW:"green" }
const VERDICT_COLOR = { BLOCKED:"red", REVIEW:"yellow", CLEAR:"green" }
const EDD_COLOR = { OPEN:"red", IN_REVIEW:"yellow", ESCALATED:"red", CLOSED:"green" }
const STATUS_COLOR = { OVERDUE:"red", DUE_TODAY:"yellow", PENDING:"blue" }

// ── Posture Tab ─────────────────────────────────────────────────────────────
function PostureTab() {
  const [data, setData]       = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr]         = useState("")

  const load = async () => {
    setLoading(true); setErr("")
    try {
      const [p, m] = await Promise.all([
        apiFetch("/api/v1/compliance/posture"),
        apiFetch("/api/v1/compliance/metrics"),
      ])
      setData(p); setMetrics(m)
    } catch(e) { setErr(e.message) }
    setLoading(false)
  }
  useEffect(() => { load() }, [])

  if (loading) return <div style={{display:"flex",justifyContent:"center",padding:48}}><Spinner/></div>
  if (err || !data) return <Card><div style={{color:"var(--red)"}}>{err||"Failed"}</div></Card>

  const statusColor = data.overall_status === "ACTION_REQUIRED" ? "var(--red)" : "var(--yellow)"

  return (
    <div style={{display:"grid",gap:16}}>
      {/* Overall status banner */}
      <div style={{ padding:"14px 20px", borderRadius:"var(--radius)",
        background: data.overall_status==="ACTION_REQUIRED" ? "var(--red-bg)" : "var(--yellow-bg)",
        border:`1px solid ${data.overall_status==="ACTION_REQUIRED" ? "var(--red-border)" : "var(--yellow-border)"}`,
        display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <AlertTriangle size={18} color={statusColor}/>
          <div>
            <div style={{fontSize:14,fontWeight:800,color:statusColor}}>{data.overall_status.replace("_"," ")}</div>
            <div style={{fontSize:11,color:"var(--text3)"}}>Generated: {data.generated_at?.slice(0,19).replace("T"," ")} UTC · {data.bfiu_ref}</div>
          </div>
        </div>
        <Btn size="sm" variant="ghost" onClick={load}><RefreshCw size={12}/>Refresh</Btn>
      </div>

      {/* Stats row */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        {[
          ["KYC Reviews Pending", data.kyc_reviews.total_pending, data.kyc_reviews.overdue+" overdue", "var(--accent)"],
          ["EDD Cases Open",      data.edd.total_open,            data.edd.escalated+" escalated",     "var(--red)"],
          ["Screening Hits",      data.screening.total_hits,      data.screening.blocked+" blocked",   "var(--yellow)"],
          ["Failed Onboarding",   data.failed_onboarding.total,   data.failed_onboarding.last_24h+" today","var(--blue)"],
        ].map(([label,val,sub,color])=>(
          <Card key={label} style={{padding:"16px 18px"}}>
            <div style={{fontSize:11,color:"var(--text3)",fontWeight:600,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:6}}>{label}</div>
            <div style={{fontSize:32,fontWeight:800,color,fontFamily:"var(--font-mono)",lineHeight:1}}>{val}</div>
            <div style={{fontSize:11,color:"var(--text3)",marginTop:4}}>{sub}</div>
          </Card>
        ))}
      </div>

      {/* KYC risk breakdown */}
      <Card>
        <SectionTitle sub="Periodic review queue by risk grade">KYC Review Queue</SectionTitle>
        <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10}}>
          {[
            ["HIGH RISK",   data.kyc_reviews.high_risk,   "1-year review",   "var(--red)"],
            ["MEDIUM RISK", data.kyc_reviews.medium_risk, "2-year review",   "var(--yellow)"],
            ["LOW RISK",    data.kyc_reviews.low_risk,    "5-year review",   "var(--green)"],
          ].map(([grade,count,freq,color])=>(
            <div key={grade} style={{ padding:"14px", borderRadius:"var(--radius-sm)",
              background:"var(--bg3)", border:`2px solid ${color}33`, textAlign:"center" }}>
              <div style={{fontSize:10,fontWeight:700,color,letterSpacing:"0.08em",marginBottom:4}}>{grade}</div>
              <div style={{fontSize:28,fontWeight:800,color,fontFamily:"var(--font-mono)"}}>{count}</div>
              <div style={{fontSize:10,color:"var(--text3)",marginTop:2}}>{freq}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Sparkline bar chart — last 30 days */}
      {metrics && (
        <Card>
          <SectionTitle sub="Last 30 days — daily onboarding activity">Activity Trend</SectionTitle>
          <div style={{display:"flex",alignItems:"flex-end",gap:3,height:60,marginTop:8}}>
            {metrics.days.map((d,i)=>{
              const total = d.onboarding_ok + d.onboarding_fail
              const maxH  = 52
              const okH   = total > 0 ? Math.round((d.onboarding_ok/total)*maxH) : 2
              const failH = Math.max(2, maxH - okH - (d.screening_hits*4))
              return (
                <div key={i} title={`${d.date}: ${d.onboarding_ok} ok, ${d.onboarding_fail} fail`}
                  style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:1,cursor:"default"}}>
                  <div style={{width:"100%",background:"var(--green)",borderRadius:"2px 2px 0 0",height:okH,opacity:0.8,transition:"height 0.3s"}}/>
                  {d.onboarding_fail>0 && <div style={{width:"100%",background:"var(--red)",height:Math.max(3,d.onboarding_fail*4),opacity:0.7}}/>}
                </div>
              )
            })}
          </div>
          <div style={{display:"flex",gap:16,marginTop:8}}>
            {[["var(--green)","Successful"],["var(--red)","Failed"]].map(([c,l])=>(
              <div key={l} style={{display:"flex",alignItems:"center",gap:5}}>
                <div style={{width:10,height:10,borderRadius:2,background:c}}/>
                <span style={{fontSize:11,color:"var(--text3)"}}>{l}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── KYC Queues Tab ──────────────────────────────────────────────────────────
function QueuesTab() {
  const [data, setData]         = useState(null)
  const [gradeFilter, setGrade] = useState("")
  const [loading, setLoading]   = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const q = gradeFilter ? `?grade=${gradeFilter}` : ""
      const d = await apiFetch(`/api/v1/compliance/kyc-queues${q}`)
      setData(d)
    } catch(e) {}
    setLoading(false)
  }, [gradeFilter])

  useEffect(() => { load() }, [load])

  return (
    <div style={{display:"grid",gap:16}}>
      <Card>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14,flexWrap:"wrap",gap:8}}>
          <SectionTitle sub={data ? `${data.total} pending reviews` : "Loading..."}>Periodic Review Queue</SectionTitle>
          <div style={{display:"flex",gap:6}}>
            {["","HIGH","MEDIUM","LOW"].map(g=>(
              <button key={g} onClick={()=>setGrade(g)} style={{
                padding:"4px 12px", fontSize:11, fontWeight:700, borderRadius:99,
                border:"1px solid var(--border)", cursor:"pointer", fontFamily:"var(--font)",
                background: gradeFilter===g ? "var(--accent)" : "var(--bg3)",
                color: gradeFilter===g ? "#fff" : "var(--text2)" }}>
                {g||"All"}
              </button>
            ))}
          </div>
        </div>
        {data && (
          <StatGrid items={[
            ["High Risk",   data.summary?.HIGH,   "var(--red)"],
            ["Medium Risk", data.summary?.MEDIUM, "var(--yellow)"],
            ["Low Risk",    data.summary?.LOW,    "var(--green)"],
            ["Overdue",     data.summary?.OVERDUE,"var(--red)"],
          ]}/>
        )}
        <Divider/>
        {loading
          ? <div style={{display:"flex",justifyContent:"center",padding:24}}><Spinner/></div>
          : (data?.queues||[]).map(k=>(
            <div key={k.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
              padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:6,
              background:"var(--bg3)", border:"1px solid var(--border)" }}>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:"var(--text)"}}>{k.customer_name}</div>
                <div style={{fontSize:11,color:"var(--text3)",fontFamily:"var(--font-mono)"}}>
                  NID: {k.nid} · Score: {k.score} · {k.kyc_type} · Agent: {k.agent}
                </div>
              </div>
              <div style={{display:"flex",gap:6,alignItems:"center",flexShrink:0}}>
                <Badge color={GRADE_COLOR[k.risk_grade]||"accent"}>{k.risk_grade}</Badge>
                <Badge color={STATUS_COLOR[k.status]||"accent"}>{k.status?.replace("_"," ")}</Badge>
              </div>
            </div>
          ))}
      </Card>
    </div>
  )
}

// ── EDD Cases Tab ───────────────────────────────────────────────────────────
const EDD_ACTIONS = {
  OPEN:      [{ action:"START_REVIEW", label:"Start Review", color:"var(--accent)" }, { action:"CLOSE_OPEN", label:"Close", color:"var(--green)" }],
  IN_REVIEW: [{ action:"ESCALATE",     label:"Escalate",     color:"var(--red)"    }, { action:"CLOSE",      label:"Close", color:"var(--green)" }],
  ESCALATED: [],
  CLOSED:    [],
}

function EDDTab() {
  const [data, setData]     = useState(null)
  const [statusFilter, setStatus] = useState("")
  const [acting, setActing] = useState(null)
  const [note,   setNote]   = useState("")

  const load = useCallback(async () => {
    try {
      const q = statusFilter ? `?status=${statusFilter}` : ""
      const d = await apiFetch(`/api/v1/compliance/edd-cases${q}`)
      setData(d)
    } catch(e) {}
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  const doAction = async (caseId, action) => {
    try {
      const r = await fetch(`${API}/api/v1/compliance/edd-cases/${caseId}/action`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ action, note, actor:"checker_01" })
      })
      if (r.ok) { setActing(null); setNote(""); load() }
    } catch(_) {}
  }

  return (
    <Card>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14,flexWrap:"wrap",gap:8}}>
        <SectionTitle sub={data ? `${data.total} EDD cases` : "Loading..."}>Enhanced Due Diligence Cases</SectionTitle>
        <div style={{display:"flex",gap:6}}>
          {["","OPEN","IN_REVIEW","ESCALATED","CLOSED"].map(s=>(
            <button key={s} onClick={()=>setStatus(s)} style={{
              padding:"4px 12px", fontSize:11, fontWeight:700, borderRadius:99,
              border:"1px solid var(--border)", cursor:"pointer", fontFamily:"var(--font)",
              background: statusFilter===s ? "var(--accent)" : "var(--bg3)",
              color: statusFilter===s ? "#fff" : "var(--text2)" }}>
              {s||"All"}
            </button>
          ))}
        </div>
      </div>
      {(data?.cases||[]).map(e=>(
        <div key={e.id} style={{ padding:"12px 14px", borderRadius:"var(--radius-sm)", marginBottom:8,
          background: e.status==="ESCALATED"?"var(--red-bg)":e.status==="CLOSED"?"var(--green-bg)":"var(--bg3)",
          border:`1px solid ${e.status==="ESCALATED"?"var(--red-border)":e.status==="CLOSED"?"var(--green-border)":"var(--border)"}` }}>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:6}}>
            <div style={{fontSize:13,fontWeight:700,color:"var(--text)"}}>{e.customer_name}</div>
            <div style={{display:"flex",gap:6,alignItems:"center"}}>
              {e.pep           && <Badge color="red">PEP</Badge>}
              {e.adverse_media && <Badge color="yellow">Adverse Media</Badge>}
              <Badge color={EDD_COLOR[e.status]||"accent"}>{e.status?.replace("_"," ")}</Badge>
            </div>
          </div>
          <div style={{display:"flex",gap:16,flexWrap:"wrap",marginBottom:8}}>
            {[["Trigger",e.trigger?.replace(/_/g," ")],["Risk Score",e.risk_score],["Assigned",e.assigned_to],["Opened",e.opened?.slice(0,10)]].map(([l,v])=>(
              <div key={l}>
                <div style={{fontSize:10,color:"var(--text3)",fontWeight:600,textTransform:"uppercase",letterSpacing:"0.05em"}}>{l}</div>
                <div style={{fontSize:12,color:"var(--text)",fontWeight:600,fontFamily:"var(--font-mono)"}}>{v}</div>
              </div>
            ))}
          </div>
          {e.last_action && (
            <div style={{fontSize:11,color:"var(--text3)",marginBottom:8,fontStyle:"italic"}}>
              Last: {e.last_action.action} by {e.last_action.actor} — {e.last_action.at?.slice(0,19).replace("T"," ")}
              {e.last_action.note && ` — "${e.last_action.note}"`}
            </div>
          )}
          {(EDD_ACTIONS[e.status]||[]).length > 0 && (
            acting === e.id ? (
              <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
                <input value={note} onChange={ev=>setNote(ev.target.value)} placeholder="Note (optional)"
                  style={{flex:1,minWidth:160,padding:"6px 10px",borderRadius:"var(--radius-xs)",background:"var(--bg2)",border:"1px solid var(--border)",color:"var(--text)",fontFamily:"var(--font)",fontSize:12,outline:"none"}}/>
                {(EDD_ACTIONS[e.status]||[]).map(({action,label,color})=>(
                  <button key={action} onClick={()=>doAction(e.id,action)} style={{
                    padding:"5px 12px",borderRadius:"var(--radius-xs)",fontSize:11,fontWeight:700,
                    background:color+"22",border:`1px solid ${color}`,color,cursor:"pointer",fontFamily:"var(--font)"}}>
                    {label}
                  </button>
                ))}
                <button onClick={()=>setActing(null)} style={{padding:"5px 10px",borderRadius:"var(--radius-xs)",fontSize:11,background:"var(--bg3)",border:"1px solid var(--border)",color:"var(--text3)",cursor:"pointer",fontFamily:"var(--font)",fontWeight:600}}>Cancel</button>
              </div>
            ) : (
              <button onClick={()=>{setActing(e.id);setNote("")}} style={{
                padding:"5px 14px",borderRadius:"var(--radius-xs)",fontSize:11,fontWeight:700,
                background:"var(--accent-bg)",border:"1px solid rgba(99,88,255,0.3)",color:"var(--accent)",
                cursor:"pointer",fontFamily:"var(--font)"}}>
                Take Action
              </button>
            )
          )}
        </div>
      ))}
      {(data?.cases||[]).length===0 && <div style={{textAlign:"center",padding:32,color:"var(--text3)",fontSize:13}}>No EDD cases match filter</div>}
    </Card>
  )
}

// ── Screening Hits Tab ──────────────────────────────────────────────────────
function ScreeningTab() {
  const [data, setData]             = useState(null)
  const [verdictFilter, setVerdict] = useState("")

  const load = useCallback(async () => {
    try {
      const q = verdictFilter ? `?verdict=${verdictFilter}` : ""
      const d = await apiFetch(`/api/v1/compliance/screening-hits${q}`)
      setData(d)
    } catch(e) {}
  }, [verdictFilter])

  useEffect(() => { load() }, [load])

  return (
    <Card>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14,flexWrap:"wrap",gap:8}}>
        <SectionTitle sub={data ? `${data.total} hits` : "Loading..."}>Sanctions & Screening Hits</SectionTitle>
        <div style={{display:"flex",gap:6}}>
          {["","BLOCKED","REVIEW"].map(v=>(
            <button key={v} onClick={()=>setVerdict(v)} style={{
              padding:"4px 12px", fontSize:11, fontWeight:700, borderRadius:99,
              border:"1px solid var(--border)", cursor:"pointer", fontFamily:"var(--font)",
              background: verdictFilter===v ? "var(--accent)" : "var(--bg3)",
              color: verdictFilter===v ? "#fff" : "var(--text2)" }}>
              {v||"All"}
            </button>
          ))}
        </div>
      </div>
      {(data?.hits||[]).map(s=>(
        <div key={s.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
          padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:6,
          background: s.verdict==="BLOCKED" ? "var(--red-bg)" : "var(--yellow-bg)",
          border:`1px solid ${s.verdict==="BLOCKED" ? "var(--red-border)" : "var(--yellow-border)"}` }}>
          <div>
            <div style={{fontSize:13,fontWeight:700,color:"var(--text)"}}>{s.customer_name}</div>
            <div style={{fontSize:11,color:"var(--text3)"}}>
              {s.matched_list} · Match: {(s.match_score*100).toFixed(0)}% · Agent: {s.agent}
            </div>
          </div>
          <div style={{display:"flex",gap:6,alignItems:"center",flexShrink:0}}>
            <Badge color="blue">{s.check_type}</Badge>
            <Badge color={VERDICT_COLOR[s.verdict]||"accent"}>{s.verdict}</Badge>
            <span style={{fontSize:10,color:"var(--text3)",fontFamily:"var(--font-mono)"}}>{s.timestamp?.slice(0,10)}</span>
          </div>
        </div>
      ))}
    </Card>
  )
}

// ── Failed Onboarding Tab ───────────────────────────────────────────────────
const STEP_COLORS = {
  NID_VERIFICATION:"red", FACE_MATCH:"yellow", LIVENESS:"yellow",
  FINGERPRINT:"blue", SCREENING:"red",
}

function FailedTab() {
  const [data, setData] = useState(null)

  useEffect(() => {
    apiFetch("/api/v1/compliance/failed-onboarding").then(setData).catch(()=>{})
  }, [])

  return (
    <div style={{display:"grid",gap:16}}>
      {data?.by_step && (
        <Card>
          <SectionTitle sub="Failures by step">Failure Breakdown</SectionTitle>
          <StatGrid items={Object.entries(data.by_step).map(([step,count])=>[
            step.replace(/_/g," "), count, `var(--${STEP_COLORS[step]||"text"})` ])}/>
        </Card>
      )}
      <Card>
        <SectionTitle sub={data ? `${data.total} failures` : "Loading..."}>Failed Sessions</SectionTitle>
        {(data?.failures||[]).map(f=>(
          <div key={f.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
            padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:6,
            background:"var(--bg3)", border:"1px solid var(--border)" }}>
            <div>
              <div style={{fontSize:12,fontWeight:700,color:"var(--text)"}}>{f.reason}</div>
              <div style={{fontSize:11,color:"var(--text3)"}}>
                Agent: {f.agent} · Attempts: {f.attempts} · {f.timestamp?.slice(0,10)}
              </div>
            </div>
            <Badge color={STEP_COLORS[f.step]||"accent"}>{f.step?.replace(/_/g," ")}</Badge>
          </div>
        ))}
      </Card>
    </div>
  )
}

// ── BFIU Export Tab ─────────────────────────────────────────────────────────
function ExportTab() {
  const [fmt,      setFmt]      = useState("json")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo,   setDateTo]   = useState("")
  const [loading,  setLoading]  = useState(false)
  const [msg,      setMsg]      = useState("")

  const doExport = async () => {
    setLoading(true); setMsg("")
    try {
      const q = new URLSearchParams({ fmt })
      if (dateFrom) q.set("date_from", dateFrom)
      if (dateTo)   q.set("date_to",   dateTo)
      const d = await apiFetch(`/api/v1/compliance/export?${q}`)
      const content = typeof d.data === "string" ? d.data : JSON.stringify(d.data, null, 2)
      const blob = new Blob([content], { type: fmt==="csv" ? "text/csv" : "application/json" })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement("a")
      a.href = url; a.download = `bfiu_compliance_report_${new Date().toISOString().slice(0,10)}.${fmt}`; a.click()
      setMsg(`✓ Downloaded bfiu_compliance_report.${fmt}`)
    } catch(e) { setMsg(`Error: ${e.message}`) }
    setLoading(false)
  }

  return (
    <Card>
      <SectionTitle sub="BFIU Circular No. 29 — compliance data export">BFIU Report Export</SectionTitle>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,marginBottom:16}}>
        <div>
          <div style={{fontSize:11,fontWeight:700,color:"var(--text2)",marginBottom:6}}>Format</div>
          <div style={{display:"flex",gap:8}}>
            {["json","csv"].map(f=>(
              <button key={f} onClick={()=>setFmt(f)} style={{
                flex:1, padding:"9px", borderRadius:"var(--radius-sm)", fontSize:13,
                fontWeight:700, fontFamily:"var(--font)", cursor:"pointer",
                background: fmt===f ? "var(--accent)" : "var(--bg3)",
                border:`1px solid ${fmt===f ? "var(--accent)" : "var(--border)"}`,
                color: fmt===f ? "#fff" : "var(--text2)" }}>
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div style={{fontSize:11,fontWeight:700,color:"var(--text2)",marginBottom:6}}>Date From</div>
          <input type="date" value={dateFrom} onChange={e=>setDateFrom(e.target.value)} style={{
            width:"100%", padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13, boxSizing:"border-box",
            background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}/>
        </div>
        <div>
          <div style={{fontSize:11,fontWeight:700,color:"var(--text2)",marginBottom:6}}>Date To</div>
          <input type="date" value={dateTo} onChange={e=>setDateTo(e.target.value)} style={{
            width:"100%", padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13, boxSizing:"border-box",
            background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}/>
        </div>
      </div>
      <Divider label="Export includes: EDD cases · Screening hits · Failed onboarding"/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(2,1fr)",gap:10,marginBottom:16}}>
        {[
          ["EDD Cases",         "Open, in-review, escalated cases"],
          ["Screening Hits",    "UNSCR, PEP, adverse media, exit list"],
          ["Failed Onboarding", "All failed sessions with reason codes"],
          ["KYC Queue Summary", "Pending reviews by risk grade"],
        ].map(([title,desc])=>(
          <div key={title} style={{ padding:"10px 14px", borderRadius:"var(--radius-sm)",
            background:"var(--bg3)", border:"1px solid var(--border)" }}>
            <div style={{fontSize:12,fontWeight:700,color:"var(--text)"}}>{title}</div>
            <div style={{fontSize:11,color:"var(--text3)",marginTop:2}}>{desc}</div>
          </div>
        ))}
      </div>
      {msg && <div style={{fontSize:12,color:msg.startsWith("✓")?"var(--green)":"var(--red)",marginBottom:12}}>{msg}</div>}
      <Btn onClick={doExport} loading={loading} size="lg">
        <Download size={14}/>Export BFIU Report ({fmt.toUpperCase()})
      </Btn>
    </Card>
  )
}

// ── ROOT ─────────────────────────────────────────────────────────────────────
export default function ComplianceDashboard({ onExit, theme, toggleTheme }) {
  const [tab, setTab] = useState("posture")

  const TAB_CONTENT = {
    posture:   <PostureTab/>,
    queues:    <QueuesTab/>,
    edd:       <EDDTab/>,
    screening: <ScreeningTab/>,
    failed:    <FailedTab/>,
    export:    <ExportTab/>,
  }

  return (
    <div style={{ minHeight:"100vh", background:"var(--bg)", fontFamily:"var(--font)" }}>
      <header style={{ background:"var(--bg2)", borderBottom:"1px solid var(--border)",
                       position:"sticky", top:0, zIndex:100, boxShadow:"var(--shadow-sm)" }}>
        <div style={{ maxWidth:1100, margin:"0 auto", padding:"0 24px", height:60,
                      display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <button onClick={onExit} style={{ display:"flex", alignItems:"center", gap:5,
              padding:"5px 10px", borderRadius:"var(--radius-sm)", fontSize:12, fontWeight:600,
              background:"var(--bg3)", border:"1px solid var(--border)",
              cursor:"pointer", color:"var(--text2)", fontFamily:"var(--font)" }}>
              <ChevronLeft size={13}/> Exit
            </button>
            <div style={{ width:1, height:20, background:"var(--border)" }}/>
            <div style={{ width:32, height:32, borderRadius:9,
              background:"linear-gradient(135deg,var(--green),var(--blue))",
              display:"flex", alignItems:"center", justifyContent:"center" }}>
              <Shield size={15} color="#fff" strokeWidth={2.5}/>
            </div>
            <div>
              <div style={{fontSize:13,fontWeight:800,color:"var(--text)",lineHeight:1.1}}>Compliance Dashboard</div>
              <div style={{fontSize:9,color:"var(--text3)",fontWeight:600,letterSpacing:"0.1em",textTransform:"uppercase"}}>BFIU Circular No. 29 · M14</div>
            </div>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <Badge color="green">● Live</Badge>
            <button onClick={toggleTheme} style={{
              padding:"6px 11px", borderRadius:"var(--radius-xs)", fontSize:12, fontWeight:600,
              background:"var(--bg3)", border:"1px solid var(--border)",
              cursor:"pointer", color:"var(--text2)", fontFamily:"var(--font)" }}>
              {theme==="light" ? "🌙 Dark" : "☀️ Light"}
            </button>
          </div>
        </div>
      </header>

      <main style={{ maxWidth:1100, margin:"0 auto", padding:"28px 24px" }}>
        <div style={{ marginBottom:20 }}>
          <h1 style={{ fontSize:26, fontWeight:800, color:"var(--text)", letterSpacing:"-0.03em", marginBottom:4 }}>
            Compliance{" "}
            <span style={{ background:"linear-gradient(135deg,var(--green),var(--blue))",
              WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>Dashboard</span>
          </h1>
          <p style={{ fontSize:13, color:"var(--text2)" }}>
            KYC review queues · EDD cases · Screening hits · Failed onboarding · BFIU export
          </p>
        </div>
        <div style={{ marginBottom:20 }}><TabNav active={tab} setActive={setTab}/></div>
        {TAB_CONTENT[tab]}
      </main>
    </div>
  )
}
