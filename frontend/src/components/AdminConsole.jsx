
import { useState, useEffect, useCallback } from "react"
import {
  Building2, Users, Sliders, Webhook, Activity,
  ClipboardList, ChevronLeft, Plus, Trash2, RefreshCw,
  CheckCircle2, XCircle, Download, AlertTriangle, Shield,
} from "lucide-react"
import {
  Card, Btn, Badge, Spinner, SectionTitle,
  StatGrid, Divider, CheckItem,
} from "./ui"
import { API, authHeaders, getToken, setToken, ensureAdminToken } from "../config"
import SettingsPanel from "./SettingsPanel"

const TABS = [
  { id:"institutions", label:"Institutions",   icon: Building2    },
  { id:"users",        label:"Users",           icon: Users        },
  { id:"thresholds",   label:"Thresholds",      icon: Sliders      },
  { id:"webhooks",     label:"Webhooks",        icon: Webhook      },
  { id:"health",       label:"System Health",   icon: Activity     },
  { id:"auditlogs",    label:"Audit Logs",      icon: ClipboardList},
  { id:"settings",     label:"Settings",         icon: Sliders      },
]

function TabNav({ active, setActive }) {
  return (
    <div style={{ display:"flex", gap:4, padding:"4px", background:"var(--bg3)",
                  borderRadius:"var(--radius)", border:"1px solid var(--border)",
                  flexWrap:"wrap", overflowX:"auto", scrollbarWidth:"none" }}>
      {TABS.map(t => {
        const Icon = t.icon
        const on = active === t.id
        return (
          <button key={t.id} onClick={() => setActive(t.id)} style={{
            display:"flex", alignItems:"center", gap:6,
            padding:"8px 14px", borderRadius:"var(--radius-sm)",
            fontSize:12, fontWeight:700, fontFamily:"var(--font)",
            border:"none", cursor:"pointer", transition:"all 0.15s",
            background: on ? "var(--accent)" : "transparent",
            color: on ? "#fff" : "var(--text2)",
          }}>
            <Icon size={13} strokeWidth={2.2} />{t.label}
          </button>
        )
      })}
    </div>
  )
}

// ── shared fetch helper ─────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  await ensureAdminToken()
  const r = await fetch(`${API}${path}`, {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers || {}) },
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

// ══════════════════════════════════════════════════════════════════════════
// TAB 1 — Institution Management
// ══════════════════════════════════════════════════════════════════════════
function InstitutionsTab() {
  const [list, setList]   = useState([])
  const [form, setForm]   = useState({ name:"", short_code:"", ip_whitelist:"", active:true })
  const [loading, setLoading] = useState(false)
  const [err, setErr]     = useState("")

  const load = useCallback(async () => {
    try { const d = await apiFetch("/api/v1/admin/institutions"); setList(d.institutions) }
    catch(e) { setErr(e.message) }
  }, [])

  useEffect(() => { load() }, [load])

  const submit = async () => {
    setLoading(true); setErr("")
    try {
      await apiFetch("/api/v1/admin/institutions", {
        method:"POST",
        body: JSON.stringify({ ...form,
          ip_whitelist: form.ip_whitelist.split(",").map(s=>s.trim()).filter(Boolean) }),
      })
      setForm({ name:"", short_code:"", ip_whitelist:"", active:true })
      await load()
    } catch(e) { setErr(e.message) }
    setLoading(false)
  }

  const del = async (id) => {
    if (!confirm("Delete institution?")) return
    try { await apiFetch(`/api/v1/admin/institutions/${id}`, { method:"DELETE" }); await load() }
    catch(e) { setErr(e.message) }
  }

  return (
    <div style={{ display:"grid", gap:16 }}>
      <Card>
        <SectionTitle sub="Register a new reporting entity">Add Institution</SectionTitle>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
          {[["name","Institution Name"],["short_code","Short Code"],["ip_whitelist","IP Whitelist (comma-sep)"]].map(([k,ph]) => (
            <input key={k} placeholder={ph} value={form[k]} onChange={e=>setForm(f=>({...f,[k]:e.target.value}))}
              style={{ gridColumn: k==="ip_whitelist"?"1/-1":"auto",
                padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13,
                background:"var(--bg3)", border:"1px solid var(--border)",
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}/>
          ))}
        </div>
        {err && <div style={{color:"var(--red)",fontSize:12,marginTop:8}}>{err}</div>}
        <div style={{marginTop:12}}>
          <Btn onClick={submit} loading={loading}><Plus size={13}/>Add Institution</Btn>
        </div>
      </Card>

      <Card>
        <SectionTitle sub={`${list.length} registered`}>Institutions</SectionTitle>
        {list.length === 0
          ? <div style={{color:"var(--text3)",fontSize:13,textAlign:"center",padding:24}}>No institutions yet</div>
          : list.map(inst => (
            <div key={inst.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
              padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:6,
              background:"var(--bg3)", border:"1px solid var(--border)" }}>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:"var(--text)"}}>{inst.name}</div>
                <div style={{fontSize:11,color:"var(--text3)",fontFamily:"var(--font-mono)"}}>
                  schema: {inst.schema_name} · code: {inst.short_code}
                </div>
                {inst.ip_whitelist?.length > 0 &&
                  <div style={{fontSize:10,color:"var(--blue)",marginTop:2}}>
                    IPs: {inst.ip_whitelist.join(", ")}
                  </div>}
              </div>
              <div style={{display:"flex",gap:8,alignItems:"center"}}>
                <Badge color={inst.active?"green":"red"}>{inst.active?"Active":"Inactive"}</Badge>
                <Btn size="sm" variant="danger" onClick={()=>del(inst.id)}><Trash2 size={11}/></Btn>
              </div>
            </div>
          ))}
      </Card>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// TAB 2 — User Management
// ══════════════════════════════════════════════════════════════════════════
const ROLES = ["admin","checker","maker","agent","auditor"]
const ROLE_COLORS = { admin:"accent", checker:"yellow", maker:"blue", agent:"green", auditor:"red" }

function UsersTab() {
  const [users, setUsers]   = useState([])
  const [form,  setForm]    = useState({ full_name:"", email:"", role:"agent", institution_id:"inst-demo-001", phone:"01700000000", password:"Demo@12345", active:true })
  const [loading, setLoading] = useState(false)
  const [err, setErr]       = useState("")
  const [filterRole, setFilterRole] = useState("")

  const load = useCallback(async () => {
    try {
      const q = filterRole ? `?role=${filterRole}` : ""
      const d = await apiFetch(`/api/v1/admin/users${q}`)
      setUsers(d.users)
    } catch(e) { setErr(e.message) }
  }, [filterRole])

  useEffect(() => { load() }, [load])

  const submit = async () => {
    setLoading(true); setErr("")
    try {
      await apiFetch("/api/v1/admin/users", { method:"POST", body: JSON.stringify(form) })
      setForm({ full_name:"", email:"", role:"agent", institution_id:"inst-demo-001", phone:"01700000000", password:"Demo@12345", active:true })
      await load()
    } catch(e) { setErr(e.message) }
    setLoading(false)
  }

  const toggle = async (uid, active) => {
    try { await apiFetch(`/api/v1/admin/users/${uid}/${active ? "deactivate" : "activate"}`, { method: active ? "PATCH" : "PUT" }); await load() }
    catch(e) { setErr(e.message) }
  }

  const del = async (uid) => {
    if (!confirm("Delete user?")) return
    try { await apiFetch(`/api/v1/admin/users/${uid}`, { method:"DELETE" }); await load() }
    catch(e) { setErr(e.message) }
  }

  return (
    <div style={{display:"grid",gap:16}}>
      <Card>
        <SectionTitle sub="Assign role and institution">Create User</SectionTitle>
        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:10}}>
          {[["full_name","Full Name"],["email","Email"],["phone","Phone (01XXXXXXXXX)"]].map(([k,ph])=>(
            <input key={k} placeholder={ph} value={form[k]} onChange={e=>setForm(f=>({...f,[k]:e.target.value}))}
              style={{ padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13,
                background:"var(--bg3)", border:"1px solid var(--border)",
                color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}/>
          ))}
          <select value={form.role} onChange={e=>setForm(f=>({...f,role:e.target.value}))} style={{
            padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13,
            background:"var(--bg3)", border:"1px solid var(--border)",
            color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
            {ROLES.map(r=><option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        {err && <div style={{color:"var(--red)",fontSize:12,marginTop:8}}>{err}</div>}
        <div style={{marginTop:12}}>
          <Btn onClick={submit} loading={loading}><Plus size={13}/>Create User</Btn>
        </div>
      </Card>

      <Card>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14}}>
          <SectionTitle sub={`${users.length} users`}>User List</SectionTitle>
          <div style={{display:"flex",gap:6}}>
            {["","admin","checker","maker","agent","auditor"].map(r=>(
              <button key={r} onClick={()=>setFilterRole(r)} style={{
                padding:"4px 10px", fontSize:11, fontWeight:700, borderRadius:99,
                border:"1px solid var(--border)", cursor:"pointer",
                background: filterRole===r?"var(--accent)":"var(--bg3)",
                color: filterRole===r?"#fff":"var(--text2)", fontFamily:"var(--font)" }}>
                {r||"All"}
              </button>
            ))}
          </div>
        </div>
        {users.length === 0
          ? <div style={{color:"var(--text3)",fontSize:13,textAlign:"center",padding:24}}>No users</div>
          : users.map(u=>(
            <div key={u.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
              padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:6,
              background:"var(--bg3)", border:"1px solid var(--border)" }}>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:"var(--text)"}}>{u.username}</div>
                <div style={{fontSize:11,color:"var(--text3)"}}>{u.email}</div>
              </div>
              <div style={{display:"flex",gap:8,alignItems:"center"}}>
                <Badge color={ROLE_COLORS[u.role]||"accent"}>{u.role}</Badge>
                <Badge color={u.active?"green":"red"}>{u.active?"Active":"Off"}</Badge>
                <Btn size="sm" variant="ghost" onClick={()=>toggle(u.id,u.active)}>
                  {u.active ? <XCircle size={11}/> : <CheckCircle2 size={11}/>}
                </Btn>
                <Btn size="sm" variant="danger" onClick={()=>del(u.id)}><Trash2 size={11}/></Btn>
              </div>
            </div>
          ))}
      </Card>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// TAB 3 — Threshold Editor
// ══════════════════════════════════════════════════════════════════════════
const THRESHOLD_META = {
  simplified_max_amount:  { label:"Simplified Max Amount (BDT)", unit:"৳",  desc:"Max transaction for simplified KYC" },
  regular_min_amount:     { label:"Regular Min Amount (BDT)",    unit:"৳",  desc:"Threshold above which regular KYC applies" },
  edd_risk_score:         { label:"EDD Trigger Score",           unit:"pts", desc:"Risk score at which EDD is triggered" },
  high_risk_review_years: { label:"High-Risk Review (years)",    unit:"yr",  desc:"Periodic review interval for high-risk customers" },
  med_risk_review_years:  { label:"Medium-Risk Review (years)",  unit:"yr",  desc:"Periodic review interval for medium-risk customers" },
  low_risk_review_years:  { label:"Low-Risk Review (years)",     unit:"yr",  desc:"Periodic review interval for low-risk customers" },
  max_nid_attempts:       { label:"Max NID Attempts",            unit:"",    desc:"Max NID lookup attempts per session" },
  max_sessions:           { label:"Max Concurrent Sessions",     unit:"",    desc:"Max simultaneous verification sessions" },
}

function ThresholdsTab() {
  const [data,    setData]    = useState({})
  const [editing, setEditing] = useState({})
  const [saving,  setSaving]  = useState("")
  const [msg,     setMsg]     = useState("")

  const load = async () => {
    try { const d = await apiFetch("/api/v1/admin/thresholds"); setData(d.thresholds); setEditing({...d.thresholds}) }
    catch(e) { setMsg(e.message) }
  }

  useEffect(() => { load() }, [])

  const save = async (key) => {
    setSaving(key); setMsg("")
    try {
      await apiFetch("/api/v1/admin/thresholds", { method:"PUT",
        body: JSON.stringify({ key, value: Number(editing[key]) }) })
      setData(d=>({...d,[key]:Number(editing[key])}))
      setMsg(`✓ ${key} updated`)
    } catch(e) { setMsg(e.message) }
    setSaving("")
  }

  const reset = async () => {
    if (!confirm("Reset all thresholds to BFIU defaults?")) return
    try {
      const d = await apiFetch("/api/v1/admin/thresholds/reset", { method:"POST" })
      setData(d.thresholds); setEditing({...d.thresholds})
      setMsg("✓ All thresholds reset to defaults")
    } catch(e) { setMsg(e.message) }
  }

  return (
    <Card>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16}}>
        <SectionTitle sub="Zero-code BFIU threshold deployment">BFIU Risk Thresholds</SectionTitle>
        <Btn size="sm" variant="ghost" onClick={reset}><RefreshCw size={12}/>Reset Defaults</Btn>
      </div>
      {msg && <div style={{fontSize:12,color:msg.startsWith("✓")?"var(--green)":"var(--red)",marginBottom:12}}>{msg}</div>}
      <div style={{display:"grid",gap:10}}>
        {Object.entries(editing).map(([key,val]) => {
          const meta = THRESHOLD_META[key] || {label:key,unit:"",desc:""}
          const changed = val !== data[key]
          return (
            <div key={key} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
              padding:"12px 14px", borderRadius:"var(--radius-sm)",
              background: changed?"var(--accent-bg)":"var(--bg3)",
              border:`1px solid ${changed?"var(--accent)":"var(--border)"}`,
              transition:"all 0.2s" }}>
              <div style={{flex:1}}>
                <div style={{fontSize:13,fontWeight:700,color:"var(--text)"}}>{meta.label}</div>
                <div style={{fontSize:11,color:"var(--text3)"}}>{meta.desc}</div>
              </div>
              <div style={{display:"flex",alignItems:"center",gap:8}}>
                {meta.unit && <span style={{fontSize:12,color:"var(--text3)"}}>{meta.unit}</span>}
                <input type="number" value={val} onChange={e=>setEditing(ed=>({...ed,[key]:e.target.value}))}
                  style={{ width:90, padding:"6px 10px", textAlign:"right",
                    borderRadius:"var(--radius-sm)", fontSize:13, fontWeight:700,
                    fontFamily:"var(--font-mono)",
                    background:"var(--bg2)", border:`1px solid ${changed?"var(--accent)":"var(--border)"}`,
                    color:"var(--text)", outline:"none" }}/>
                {changed &&
                  <Btn size="sm" onClick={()=>save(key)} loading={saving===key}>Save</Btn>}
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// TAB 4 — Webhook Management
// ══════════════════════════════════════════════════════════════════════════
const WEBHOOK_EVENTS = [
  "kyc.onboarding.completed","kyc.onboarding.failed",
  "risk.edd.triggered","screening.sanctions.hit",
  "lifecycle.review.due","auth.login.failed",
]

function WebhooksTab() {
  const [hooks, setHooks] = useState([])
  const [logs,  setLogs]  = useState([])
  const [form,  setForm]  = useState({ url:"", events:[], secret:"", active:true })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState("")

  const loadHooks = async () => {
    try { const d = await apiFetch("/api/v1/admin/webhooks"); setHooks(d.webhooks) } catch(e) { setErr(e.message) }
  }
  const loadLogs = async () => {
    try { const d = await apiFetch("/api/v1/admin/webhooks/logs"); setLogs(d.logs || []) } catch(e) {}
  }

  useEffect(() => { loadHooks(); loadLogs() }, [])

  const toggleEvent = (ev) => setForm(f=>({...f, events: f.events.includes(ev) ? f.events.filter(e=>e!==ev) : [...f.events,ev]}))

  const submit = async () => {
    if (!form.url || form.events.length===0) { setErr("URL and at least one event required"); return }
    setLoading(true); setErr("")
    try {
      await apiFetch("/api/v1/admin/webhooks", { method:"POST", body: JSON.stringify(form) })
      setForm({ url:"", events:[], secret:"", active:true }); await loadHooks()
    } catch(e) { setErr(e.message) }
    setLoading(false)
  }

  const del = async (id) => {
    try { await apiFetch(`/api/v1/admin/webhooks/${id}`, { method:"DELETE" }); await loadHooks() }
    catch(e) { setErr(e.message) }
  }

  return (
    <div style={{display:"grid",gap:16}}>
      <Card>
        <SectionTitle sub="Register endpoint to receive eKYC events">Register Webhook</SectionTitle>
        <input placeholder="https://your-endpoint.com/webhook" value={form.url}
          onChange={e=>setForm(f=>({...f,url:e.target.value}))}
          style={{ width:"100%", padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13, boxSizing:"border-box",
            background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", outline:"none", marginBottom:10 }}/>
        <div style={{fontSize:11,fontWeight:700,color:"var(--text2)",marginBottom:6}}>Events</div>
        <div style={{display:"flex",flexWrap:"wrap",gap:6,marginBottom:12}}>
          {WEBHOOK_EVENTS.map(ev=>(
            <button key={ev} onClick={()=>toggleEvent(ev)} style={{
              padding:"4px 10px", fontSize:11, fontWeight:700, borderRadius:99,
              border:`1px solid ${form.events.includes(ev)?"var(--accent)":"var(--border)"}`,
              background: form.events.includes(ev)?"var(--accent-bg)":"var(--bg3)",
              color: form.events.includes(ev)?"var(--accent)":"var(--text2)",
              cursor:"pointer", fontFamily:"var(--font)" }}>{ev}</button>
          ))}
        </div>
        <input placeholder="Secret (optional)" value={form.secret}
          onChange={e=>setForm(f=>({...f,secret:e.target.value}))}
          style={{ width:"100%", padding:"9px 12px", borderRadius:"var(--radius-sm)", fontSize:13, boxSizing:"border-box",
            background:"var(--bg3)", border:"1px solid var(--border)", color:"var(--text)", fontFamily:"var(--font)", outline:"none", marginBottom:10 }}/>
        {err && <div style={{color:"var(--red)",fontSize:12,marginBottom:8}}>{err}</div>}
        <Btn onClick={submit} loading={loading}><Plus size={13}/>Register</Btn>
      </Card>

      <Card>
        <SectionTitle sub={`${hooks.length} registered`}>Active Webhooks</SectionTitle>
        {hooks.length===0
          ? <div style={{color:"var(--text3)",fontSize:13,textAlign:"center",padding:24}}>No webhooks registered</div>
          : hooks.map(h=>(
            <div key={h.id} style={{ padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:6,
              background:"var(--bg3)", border:"1px solid var(--border)",
              display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <div>
                <div style={{fontSize:12,fontWeight:700,color:"var(--text)",fontFamily:"var(--font-mono)"}}>{h.url}</div>
                <div style={{fontSize:11,color:"var(--text3)",marginTop:2}}>
                  {h.events.join(" · ")}
                </div>
              </div>
              <div style={{display:"flex",gap:8,alignItems:"center"}}>
                <Badge color={h.active?"green":"red"}>{h.active?"Live":"Off"}</Badge>
                <Btn size="sm" variant="danger" onClick={()=>del(h.id)}><Trash2 size={11}/></Btn>
              </div>
            </div>
          ))}
      </Card>

      <Card>
        <SectionTitle sub="Recent delivery attempts">Delivery Logs</SectionTitle>
        {logs.map(l=>(
          <div key={l.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
            padding:"8px 12px", borderRadius:"var(--radius-sm)", marginBottom:4,
            background:"var(--bg3)", border:"1px solid var(--border)" }}>
            <div style={{display:"flex",alignItems:"center",gap:8}}>
              <div style={{width:8,height:8,borderRadius:"50%",background:l.status===200?"var(--green)":"var(--red)",flexShrink:0}}/>
              <span style={{fontSize:12,color:"var(--text)"}}>{l.event}</span>
            </div>
            <div style={{display:"flex",gap:12,alignItems:"center"}}>
              <span style={{fontSize:11,fontFamily:"var(--font-mono)",color:l.status===200?"var(--green)":"var(--red)"}}>{l.status}</span>
              <span style={{fontSize:11,color:"var(--text3)"}}>{l.duration_ms}ms</span>
              <span style={{fontSize:10,color:"var(--text3)"}}>{l.timestamp?.slice(11,19)}</span>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// TAB 5 — System Health
// ══════════════════════════════════════════════════════════════════════════
function HealthTab() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr]       = useState("")

  const load = async () => {
    setLoading(true)
    try { const d = await apiFetch("/api/v1/admin/health"); setData(d) }
    catch(e) { setErr(e.message) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  if (loading) return <div style={{display:"flex",justifyContent:"center",padding:40}}><Spinner/></div>
  if (err || !data) return <Card><div style={{color:"var(--red)"}}>{err||"Failed to load"}</div></Card>

  return (
    <div style={{display:"grid",gap:16}}>
      <Card glow={data.status==="healthy"}>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16}}>
          <SectionTitle sub={`Checked: ${(data.timestamp||data.checked_at||"")?.slice(11,19)} UTC`}>System Status</SectionTitle>
          <div style={{display:"flex",gap:8}}>
            <Badge color={data.status==="healthy"?"green":"red"}>{data.status?.toUpperCase()}</Badge>
            <Btn size="sm" variant="ghost" onClick={load}><RefreshCw size={12}/>Refresh</Btn>
          </div>
        </div>
        <StatGrid items={[
          ["Version",  data.version  || "1.0.0",    "var(--accent)"],
          ["DB",       data.db_name  || data.db || "unknown",  "var(--blue)"],
          ["BFIU Ref", "Circular 29",               "var(--text2)"],
        ]}/>
      </Card>

      <Card>
        <SectionTitle sub="All backend modules">Module Status</SectionTitle>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(160px,1fr))",gap:6}}>
          {Object.entries(data.modules||{}).map(([mod,status])=>(
            <CheckItem key={mod} label={mod} pass={status==="ok"} value={status}/>
          ))}
        </div>
      </Card>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        <Card>
          <SectionTitle sub="BFIU session limits">Rate Limits</SectionTitle>
          {Object.entries(data.rate_limits||{}).map(([k,v])=>(
            <div key={k} style={{display:"flex",justifyContent:"space-between",alignItems:"center",
              padding:"7px 10px",borderRadius:"var(--radius-sm)",marginBottom:4,
              background:"var(--bg3)",border:"1px solid var(--border)"}}>
              <span style={{fontSize:12,color:"var(--text2)"}}>{k.replace(/_/g," ")}</span>
              <span style={{fontSize:12,fontFamily:"var(--font-mono)",fontWeight:700,color:"var(--accent)"}}>{typeof v==="object" ? `${v.requests}/${v.window_seconds}s` : v}</span>
            </div>
          ))}
        </Card>
        <Card>
          <SectionTitle sub="PII data residency enforcement">Whitelisted Domains</SectionTitle>
          {(data.whitelisted_domains||[]).map(d=>(
            <div key={d} style={{display:"flex",alignItems:"center",gap:8,
              padding:"7px 10px",borderRadius:"var(--radius-sm)",marginBottom:4,
              background:"var(--bg3)",border:"1px solid var(--border)"}}>
              <div style={{width:6,height:6,borderRadius:"50%",background:"var(--green)",flexShrink:0}}/>
              <span style={{fontSize:12,fontFamily:"var(--font-mono)",color:"var(--text)"}}>{d}</span>
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// TAB 6 — Audit Log Viewer
// ══════════════════════════════════════════════════════════════════════════
const SEV_COLORS = { info:"blue", warning:"yellow", critical:"red" }
const SEV_OPTS   = ["","info","warning","critical"]

function AuditLogsTab() {
  const [logs,  setLogs]  = useState([])
  const [total, setTotal] = useState(0)
  const [evFilter, setEvFilter]   = useState("")
  const [sevFilter, setSevFilter] = useState("")
  const [loading, setLoading]     = useState(false)
  const [err, setErr]             = useState("")
  const [page, setPage]           = useState(1)
  const PAGE_SIZE = 20

  const load = useCallback(async () => {
    setLoading(true); setErr("")
    try {
      const q = new URLSearchParams()
      if (evFilter)  q.set("event_type", evFilter)
      if (sevFilter) q.set("severity", sevFilter)
      q.set("limit", PAGE_SIZE)
      q.set("offset", (page-1)*PAGE_SIZE)
      q.set("limit", PAGE_SIZE)
      q.set("offset", (page-1)*PAGE_SIZE)
      const d = await apiFetch(`/api/v1/admin/audit-logs?${q}`)
      setLogs(d.entries || d.logs || []); setTotal(d.total || 0)
    } catch(e) { setErr(e.message) }
    setLoading(false)
  }, [evFilter, sevFilter])

  useEffect(() => { load() }, [load])

  const exportLogs = async (fmt) => {
    try {
      const d = await apiFetch(`/api/v1/admin/audit-logs/export?fmt=${fmt}`)
      const blob = new Blob([typeof d.data==="string" ? d.data : JSON.stringify(d.data,null,2)],
        { type: fmt==="csv"?"text/csv":"application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a"); a.href=url; a.download=`audit-logs.${fmt}`; a.click()
    } catch(e) { setErr(e.message) }
  }

  return (
    <Card>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14,flexWrap:"wrap",gap:8}}>
        <SectionTitle sub={`${total} entries`}>Immutable Audit Trail</SectionTitle>
        <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
          <input placeholder="Filter by event type" value={evFilter}
            onChange={e=>setEvFilter(e.target.value)}
            style={{ padding:"6px 10px", borderRadius:"var(--radius-sm)", fontSize:12,
              background:"var(--bg3)", border:"1px solid var(--border)",
              color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}/>
          <select value={sevFilter} onChange={e=>setSevFilter(e.target.value)} style={{
            padding:"6px 10px", borderRadius:"var(--radius-sm)", fontSize:12,
            background:"var(--bg3)", border:"1px solid var(--border)",
            color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
            {SEV_OPTS.map(s=><option key={s} value={s}>{s||"All Severity"}</option>)}
          </select>
          <Btn size="sm" variant="ghost" onClick={()=>exportLogs("json")}><Download size={11}/>JSON</Btn>
          <Btn size="sm" variant="ghost" onClick={()=>exportLogs("csv")} ><Download size={11}/>CSV</Btn>
        </div>
      </div>
      {err && <div style={{color:"var(--red)",fontSize:12,marginBottom:8}}>{err}</div>}
      {loading
        ? <div style={{display:"flex",justifyContent:"center",padding:32}}><Spinner/></div>
        : logs.length===0
          ? <div style={{color:"var(--text3)",fontSize:13,textAlign:"center",padding:24}}>No logs match the filter</div>
          : <>
            {logs.map(l=>(
              <div key={l.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
                padding:"10px 14px", borderRadius:"var(--radius-sm)", marginBottom:5,
                background:"var(--bg3)", border:"1px solid var(--border)" }}>
                <div style={{display:"flex",alignItems:"center",gap:10}}>
                  <div style={{width:8,height:8,borderRadius:"50%",flexShrink:0,
                    background: l.severity==="critical"?"var(--red)":l.severity==="warning"?"var(--yellow)":"var(--blue)"}}/>
                  <div>
                    <div style={{fontSize:12,fontWeight:700,color:"var(--text)",fontFamily:"var(--font-mono)"}}>{l.event_type}</div>
                    <div style={{fontSize:11,color:"var(--text3)"}}>actor: {l.actor_id || l.actor}</div>
                  </div>
                </div>
                <div style={{display:"flex",gap:8,alignItems:"center"}}>
                  <Badge color={SEV_COLORS[l.severity]||"blue"}>{l.severity||"info"}</Badge>
                  <span style={{fontSize:10,color:"var(--text3)",fontFamily:"var(--font-mono)"}}>{l.timestamp?.slice(0,19).replace("T"," ")}</span>
                </div>
              </div>
            ))}
            {total > PAGE_SIZE && (
              <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginTop:12,paddingTop:12,borderTop:"1px solid var(--border)"}}>
                <span style={{fontSize:12,color:"var(--text3)"}}>
                  Showing {(page-1)*PAGE_SIZE+1}–{Math.min(page*PAGE_SIZE,total)} of {total}
                </span>
                <div style={{display:"flex",gap:6}}>
                  <Btn size="sm" variant="ghost" onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={page===1}>← Prev</Btn>
                  <span style={{fontSize:12,color:"var(--text2)",padding:"4px 10px",background:"var(--bg3)",borderRadius:"var(--radius-sm)",border:"1px solid var(--border)"}}>
                    {page} / {Math.ceil(total/PAGE_SIZE)}
                  </span>
                  <Btn size="sm" variant="ghost" onClick={()=>setPage(p=>p+1)} disabled={page*PAGE_SIZE>=total}>Next →</Btn>
                </div>
              </div>
            )}
          </>}
    </Card>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// ROOT
// ══════════════════════════════════════════════════════════════════════════
export default function AdminConsole({ onExit, theme, toggleTheme, externalTab, onTabChange }) {
  const [tab, setTab] = useState(() => externalTab || "institutions")

  const TAB_CONTENT = {
    institutions: <InstitutionsTab/>,
    users:        <UsersTab/>,
    thresholds:   <ThresholdsTab/>,
    webhooks:     <WebhooksTab/>,
    health:       <HealthTab/>,
    auditlogs:    <AuditLogsTab/>,
    settings:     <SettingsPanel/>,
  }

  return (
    <div style={{ fontFamily:"var(--font)", background: externalTab ? "transparent" : "var(--bg)", minHeight: externalTab ? "auto" : "100vh" }}>
      {!externalTab && <header style={{ background:"var(--bg2)", borderBottom:"1px solid var(--border)", position:"sticky", top:0, zIndex:100 }}><div style={{ maxWidth:1100, margin:"0 auto", padding:"0 24px", height:60, display:"flex", alignItems:"center", justifyContent:"space-between" }}><button onClick={onExit} style={{ padding:"5px 10px", borderRadius:8, fontSize:12, fontWeight:600, background:"var(--bg3)", border:"1px solid var(--border)", cursor:"pointer", color:"var(--text2)", fontFamily:"var(--font)", display:"flex", alignItems:"center", gap:5 }}><ChevronLeft size={13}/> Exit</button><button onClick={toggleTheme} style={{ padding:"6px 11px", borderRadius:8, fontSize:12, background:"var(--bg3)", border:"1px solid var(--border)", cursor:"pointer", color:"var(--text2)", fontFamily:"var(--font)" }}>{theme==="light"?"🌙 Dark":"☀️ Light"}</button></div></header>}

      <main style={{ maxWidth: externalTab ? "100%" : 1100, margin:"0 auto", padding: externalTab ? "0" : "28px 24px" }}>
{!externalTab && <div style={{ marginBottom:20 }}><h1 style={{ fontSize:26, fontWeight:800, color:"var(--text)", letterSpacing:"-0.03em", marginBottom:4 }}>Admin Console</h1><p style={{ fontSize:13, color:"var(--text2)" }}>Institution management · User RBAC · BFIU threshold editor · Webhooks · System health · Audit trail</p></div>}
        {!externalTab && <div style={{ marginBottom:20 }}><TabNav active={tab} setActive={setTab}/></div>}
        {TAB_CONTENT[tab]}
      </main>
    </div>
  )
}
