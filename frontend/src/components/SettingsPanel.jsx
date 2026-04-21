
import { useState, useEffect } from "react"
import { Card, Btn, SectionTitle, Divider, Badge, Spinner } from "./ui"
import {
  Settings, Key, MessageSquare, Mail, Shield, Sliders,
  Building2, Save, RotateCcw, CheckCircle, AlertCircle,
  Eye, EyeOff, RefreshCw, Wifi, WifiOff, Zap
} from "lucide-react"
import { API } from "../config"

function Section({ icon: Icon, title, sub, children }) {
  return (
    <Card style={{ marginBottom: 14 }}>
      <div style={{ display:"flex", alignItems:"center", gap:9, marginBottom:16 }}>
        <div style={{ width:32, height:32, borderRadius:9, background:"var(--accent-bg2)",
          display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
          <Icon size={15} color="var(--accent)" strokeWidth={2.2}/>
        </div>
        <div>
          <div style={{ fontSize:13, fontWeight:800, color:"var(--text)" }}>{title}</div>
          {sub && <div style={{ fontSize:11, color:"var(--text3)", marginTop:1 }}>{sub}</div>}
        </div>
      </div>
      {children}
    </Card>
  )
}

function Field({ label, k, value, onChange, type="text", hint, password, required, options, mono }) {
  const [show, setShow] = useState(false)
  const isPass = password || type === "password"
  return (
    <div style={{ marginBottom:12 }}>
      <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
        textTransform:"uppercase", letterSpacing:"0.05em",
        display:"flex", alignItems:"center", gap:5, marginBottom:5 }}>
        {label}{required && <span style={{ color:"var(--red)" }}>*</span>}
      </label>
      {options ? (
        <select value={value} onChange={e => onChange(k, e.target.value)}
          style={{ width:"100%", padding:"9px 12px", borderRadius:"var(--radius-sm)",
            fontSize:13, background:"var(--bg2)", border:"1px solid var(--border)",
            color:"var(--text)", fontFamily:"var(--font)", outline:"none" }}>
          {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      ) : (
        <div style={{ position:"relative" }}>
          <input
            type={isPass && !show ? "password" : "text"}
            value={value || ""}
            onChange={e => onChange(k, e.target.value)}
            style={{ width:"100%", padding:`9px ${isPass?"38px":"12px"} 9px 12px`,
              borderRadius:"var(--radius-sm)", fontSize:13, boxSizing:"border-box",
              background:"var(--bg2)", border:"1px solid var(--border)",
              color:"var(--text)", fontFamily: mono ? "var(--font-mono)" : "var(--font)",
              outline:"none", letterSpacing: mono ? "0.05em" : "normal" }}
          />
          {isPass && (
            <button onClick={() => setShow(s => !s)}
              style={{ position:"absolute", right:10, top:"50%", transform:"translateY(-50%)",
                background:"none", border:"none", cursor:"pointer", color:"var(--text3)" }}>
              {show ? <EyeOff size={14}/> : <Eye size={14}/>}
            </button>
          )}
        </div>
      )}
      {hint && <div style={{ fontSize:10, color:"var(--text3)", marginTop:3 }}>{hint}</div>}
    </div>
  )
}

export default function SettingsPanel({ onBack }) {
  const [settings, setSettings] = useState(null)
  const [status,   setStatus]   = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [saving,   setSaving]   = useState(false)
  const [saved,    setSaved]    = useState(false)
  const [error,    setError]    = useState("")
  const [testResults, setTestResults] = useState({})

  useEffect(() => { fetchSettings() }, [])

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const [s, st] = await Promise.all([
        fetch(`${API}/api/v1/settings`).then(r => r.json()),
        fetch(`${API}/api/v1/settings/status`).then(r => r.json()),
      ])
      setSettings(s.settings)
      setStatus(st)
    } catch(e) {
      setError("Could not load settings: " + e.message)
    }
    setLoading(false)
  }

  const set = (k, v) => setSettings(s => ({ ...s, [k]: v }))

  const save = async () => {
    setSaving(true); setSaved(false); setError("")
    try {
      const r = await fetch(`${API}/api/v1/settings`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(settings)
      })
      if (r.ok) { setSaved(true); setTimeout(() => setSaved(false), 3000); fetchSettings() }
      else setError("Save failed: " + r.statusText)
    } catch(e) { setError("Save failed: " + e.message) }
    setSaving(false)
  }

  const testConnection = async (type) => {
    setTestResults(t => ({ ...t, [type]: "testing" }))
    try {
      const r = await fetch(`${API}/api/v1/settings/status`)
      const d = await r.json()
      let result = "unknown"
      if (type === "nid")   result = d.has_ec_credentials ? "configured" : "no_key"
      if (type === "sms")   result = d.has_sms  ? "configured" : "no_key"
      if (type === "smtp")  result = d.has_smtp ? "configured" : "no_key"
      if (type === "api")   result = r.ok ? "ok" : "error"
      setTestResults(t => ({ ...t, [type]: result }))
    } catch(e) {
      setTestResults(t => ({ ...t, [type]: "error" }))
    }
  }

  const StatusDot = ({ type }) => {
    const r = testResults[type]
    if (r === "testing")    return <Spinner size={12}/>
    if (r === "ok" || r === "configured") return <CheckCircle size={13} color="var(--green)"/>
    if (r === "no_key")     return <AlertCircle size={13} color="var(--yellow)"/>
    if (r === "error")      return <AlertCircle size={13} color="var(--red)"/>
    return <div style={{ width:8, height:8, borderRadius:"50%", background:"var(--bg5)", flexShrink:0 }}/>
  }

  if (loading) return (
    <div style={{ display:"flex", justifyContent:"center", padding:60 }}>
      <Spinner size={32}/>
    </div>
  )

  return (
    <div style={{ animation:"fadeUp 0.2s ease both" }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
        marginBottom:20, flexWrap:"wrap", gap:10 }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <Settings size={20} color="var(--accent)"/>
          <div>
            <div style={{ fontSize:16, fontWeight:800, color:"var(--text)" }}>Platform Settings</div>
            <div style={{ fontSize:11, color:"var(--text3)" }}>Runtime configuration — no server restart required</div>
          </div>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <Btn size="sm" variant="ghost" onClick={fetchSettings}>
            <RefreshCw size={12}/> Refresh
          </Btn>
          <Btn size="sm" variant="ghost" onClick={async () => {
            if (!confirm("Reset all settings to defaults?")) return
            await fetch(`${API}/api/v1/settings/reset`, { method:"POST" })
            fetchSettings()
          }}>
            <RotateCcw size={12}/> Reset
          </Btn>
          <Btn size="md" onClick={save} loading={saving} variant={saved ? "success" : "primary"}>
            {saved ? <><CheckCircle size={13}/> Saved!</> : <><Save size={13}/> Save All Settings</>}
          </Btn>
        </div>
      </div>

      {error && (
        <div style={{ padding:"10px 14px", marginBottom:14, borderRadius:"var(--radius-sm)",
          background:"var(--red-bg)", border:"1px solid var(--red-border)",
          fontSize:12, color:"var(--red)" }}>{error}</div>
      )}

      {/* Live Status Banner */}
      {status && (
        <div style={{ padding:"14px 18px", marginBottom:20, borderRadius:"var(--radius)",
          background: status.demo_mode ? "var(--yellow-bg)" : "var(--green-bg)",
          border:`1px solid ${status.demo_mode ? "var(--yellow-border)" : "var(--green-border)"}`,
          display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:10 }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            {status.demo_mode
              ? <AlertCircle size={18} color="var(--yellow)"/>
              : <Zap size={18} color="var(--green)"/>}
            <div>
              <div style={{ fontSize:13, fontWeight:800,
                color: status.demo_mode ? "var(--yellow)" : "var(--green)" }}>
                {status.demo_mode ? "DEMO MODE — Not connected to live EC API" : "LIVE MODE — Connected to EC Database"}
              </div>
              <div style={{ fontSize:11, color:"var(--text2)", marginTop:1 }}>
                Institution: {status.institution} ·
                Match threshold: {status.match_threshold}% ·
                Max attempts: {status.bfiu_max_attempts}/session
              </div>
            </div>
          </div>
          <div style={{ display:"flex", gap:6 }}>
            <Badge color={status.has_ec_credentials ? "green" : "yellow"}>
              {status.has_ec_credentials ? "EC ✓" : "EC: No Key"}
            </Badge>
            <Badge color={status.has_sms ? "green" : "red"}>
              {status.has_sms ? "SMS ✓" : "SMS: Not Set"}
            </Badge>
            <Badge color={status.has_smtp ? "green" : "red"}>
              {status.has_smtp ? "Email ✓" : "Email: Not Set"}
            </Badge>
          </div>
        </div>
      )}

      {settings && (
        <>
          {/* 1. Institution */}
          <Section icon={Building2} title="Institution Details"
            sub="Your organization's registration information">
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <Field label="Institution Name" k="institution_name" value={settings.institution_name} onChange={set} required/>
              <Field label="Institution Type" k="institution_type" value={settings.institution_type} onChange={set}
                options={[
                ["bank","Bank (Scheduled Bank — BB)"],
                ["insurance","Insurance (Life/Non-Life — IDRA)"],
                ["cmi","Capital Market Intermediary (BSEC)"],
                ["mfi","Microfinance Institution (MRA)"],
                ["nbfi","Non-Bank Financial Institution (BB)"],
                ["ngo","NGO (NGO Affairs Bureau)"],
                ["cooperative","Cooperative Society"],
                ["leasing","Leasing Company (BB)"],
                ["exchange","Money Exchange House (BB)"],
                ["brokerage","Stock Broker/Dealer (BSEC)"],
                ["merchant_bank","Merchant Bank (BSEC)"],
              ]}/>
              <Field label="Institution Code" k="institution_code" value={settings.institution_code} onChange={set} mono
                hint="Short code used in session IDs and reports"/>
              <Field label="Helpdesk Phone" k="helpdesk_number" value={settings.helpdesk_number} onChange={set}
                hint="Shown to customers on failure notification"/>
              <div style={{ gridColumn:"1/-1" }}>
                <Field label="Helpdesk Email" k="helpdesk_email" value={settings.helpdesk_email} onChange={set}/>
              </div>
            </div>
            <Divider/>
            <div style={{ display:"flex", gap:10 }}>
              <div style={{ flex:1, padding:"10px 14px", borderRadius:"var(--radius-sm)",
                background:"var(--bg3)", border:"1px solid var(--border)",
                display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                <div>
                  <div style={{ fontSize:11, fontWeight:700, color:"var(--text2)" }}>DEMO MODE</div>
                  <div style={{ fontSize:10, color:"var(--text3)" }}>All verifications use mock data</div>
                </div>
                <button onClick={() => set("demo_mode", !settings.demo_mode)} style={{
                  width:44, height:24, borderRadius:12,
                  background: settings.demo_mode ? "var(--yellow)" : "var(--green)",
                  border:"none", cursor:"pointer", position:"relative", transition:"all 0.2s",
                }}>
                  <div style={{
                    width:18, height:18, borderRadius:"50%", background:"#fff",
                    position:"absolute", top:3, transition:"all 0.2s",
                    left: settings.demo_mode ? 3 : 23,
                  }}/>
                </button>
              </div>
              <div style={{ flex:1, padding:"10px 14px", borderRadius:"var(--radius-sm)",
                background:"var(--bg3)", border:"1px solid var(--border)",
                display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                <div>
                  <div style={{ fontSize:11, fontWeight:700, color:"var(--text2)" }}>MAINTENANCE MODE</div>
                  <div style={{ fontSize:10, color:"var(--text3)" }}>Block all new onboardings</div>
                </div>
                <button onClick={() => set("maintenance_mode", !settings.maintenance_mode)} style={{
                  width:44, height:24, borderRadius:12,
                  background: settings.maintenance_mode ? "var(--red)" : "var(--bg4)",
                  border:"none", cursor:"pointer", position:"relative", transition:"all 0.2s",
                }}>
                  <div style={{
                    width:18, height:18, borderRadius:"50%", background:"#fff",
                    position:"absolute", top:3, transition:"all 0.2s",
                    left: settings.maintenance_mode ? 23 : 3,
                  }}/>
                </button>
              </div>
            </div>
          </Section>

          {/* 2. EC / NID API */}
          <Section icon={Key} title="EC / NID API Configuration"
            sub="Bangladesh Election Commission — Porichoy API credentials">
            <div style={{ padding:"10px 14px", marginBottom:14, borderRadius:"var(--radius-sm)",
              background:"var(--blue-bg)", border:"1px solid var(--blue-border)",
              fontSize:11, color:"var(--blue)", lineHeight:1.7 }}>
              Apply for EC API access at <strong>nid@ec.gov.bd</strong> or through Bangladesh Bank's BFIU channel.
              Approval typically takes 4–12 weeks. Until then, keep DEMO mode ON.
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <Field label="API Mode" k="nid_api_mode" value={settings.nid_api_mode} onChange={set}
                options={[["DEMO","DEMO — Mock responses"],["LIVE","LIVE — Real EC Database"],["STAGING","STAGING — Test environment"]]}/>
              <Field label="API Base URL" k="nid_api_base_url" value={settings.nid_api_base_url} onChange={set} mono/>
              <Field label="API Key" k="nid_api_key" value={settings.nid_api_key} onChange={set} password required mono
                hint="Provided by Election Commission"/>
              <Field label="API Secret" k="nid_api_secret" value={settings.nid_api_secret} onChange={set} password required mono
                hint="Keep strictly confidential"/>
            </div>
            <div style={{ display:"flex", alignItems:"center", gap:8, marginTop:4 }}>
              <Btn size="sm" variant="ghost" onClick={() => testConnection("nid")}>
                <Wifi size={11}/> Test Connection
              </Btn>
              <StatusDot type="nid"/>
              {testResults.nid === "no_key" && <span style={{ fontSize:11, color:"var(--yellow)" }}>API key not configured</span>}
              {testResults.nid === "configured" && <span style={{ fontSize:11, color:"var(--green)" }}>Credentials saved</span>}
            </div>
          </Section>

          {/* 3. SMS */}
          <Section icon={MessageSquare} title="SMS Gateway"
            sub="Account opening notifications via registered SIM (BFIU §3.3 Step 5)">
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <Field label="SMS Provider" k="sms_provider" value={settings.sms_provider} onChange={set}
                options={[["ssl_wireless","SSL Wireless (Bangladesh)"],["infobip","Infobip"],["twilio","Twilio"],["bdsms","BDSms"],["custom","Custom"]]}/>
              <Field label="Sender ID" k="sms_sender_id" value={settings.sms_sender_id} onChange={set}
                hint="Displayed as sender on customer's phone"/>
              <Field label="API URL" k="sms_api_url" value={settings.sms_api_url} onChange={set} mono/>
              <Field label="API Key" k="sms_api_key" value={settings.sms_api_key} onChange={set} password mono
                hint="From your SMS gateway dashboard"/>
            </div>
            <Btn size="sm" variant="ghost" onClick={() => testConnection("sms")} style={{ marginTop:4 }}>
              <MessageSquare size={11}/> Test SMS Config <StatusDot type="sms"/>
            </Btn>
          </Section>

          {/* 4. SMTP Email */}
          <Section icon={Mail} title="Email (SMTP)"
            sub="Secondary notification channel — optional per BFIU">
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              <Field label="SMTP Host" k="smtp_host" value={settings.smtp_host} onChange={set} mono/>
              <Field label="SMTP Port" k="smtp_port" value={String(settings.smtp_port)} onChange={(k,v) => set(k, parseInt(v)||587)}/>
              <Field label="SMTP User / Email" k="smtp_user" value={settings.smtp_user} onChange={set}/>
              <Field label="App Password" k="smtp_password" value={settings.smtp_password} onChange={set} password
                hint="Use App Password for Gmail (not your login password)"/>
              <div style={{ gridColumn:"1/-1" }}>
                <Field label="From Address" k="smtp_from" value={settings.smtp_from} onChange={set}
                  hint="Displayed as sender in customer emails"/>
              </div>
            </div>
            <Btn size="sm" variant="ghost" onClick={() => testConnection("smtp")} style={{ marginTop:4 }}>
              <Mail size={11}/> Test Email Config <StatusDot type="smtp"/>
            </Btn>
          </Section>

          {/* 5. Biometric Thresholds */}
          <Section icon={Sliders} title="Biometric & BFIU Thresholds"
            sub="Face matching confidence and session limits per BFIU §3.3">
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))", gap:12 }}>
              <div>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                  textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                  Match Threshold (%)
                </label>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <input type="range" min="20" max="80" step="1"
                    value={settings.match_threshold} onChange={e => set("match_threshold", parseFloat(e.target.value))}
                    style={{ flex:1 }}/>
                  <div style={{ fontSize:16, fontWeight:800, color:"var(--green)",
                    fontFamily:"var(--font-mono)", minWidth:44, textAlign:"center" }}>
                    {settings.match_threshold}%
                  </div>
                </div>
                <div style={{ fontSize:10, color:"var(--text3)", marginTop:3 }}>
                  Above this → MATCHED. Default: 45%. Lower = more lenient, Higher = stricter.
                </div>
              </div>
              <div>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                  textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                  Review Threshold (%)
                </label>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <input type="range" min="10" max="50" step="1"
                    value={settings.review_threshold} onChange={e => set("review_threshold", parseFloat(e.target.value))}
                    style={{ flex:1 }}/>
                  <div style={{ fontSize:16, fontWeight:800, color:"var(--yellow)",
                    fontFamily:"var(--font-mono)", minWidth:44, textAlign:"center" }}>
                    {settings.review_threshold}%
                  </div>
                </div>
                <div style={{ fontSize:10, color:"var(--text3)", marginTop:3 }}>
                  Between review & match → REVIEW (manual checker queue). Default: 30%.
                </div>
              </div>
              <div>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                  textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                  Max Attempts / Session
                </label>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <input type="range" min="3" max="10" step="1"
                    value={settings.bfiu_max_attempts} onChange={e => set("bfiu_max_attempts", parseInt(e.target.value))}
                    style={{ flex:1 }}/>
                  <div style={{ fontSize:16, fontWeight:800, color:"var(--accent)",
                    fontFamily:"var(--font-mono)", minWidth:44, textAlign:"center" }}>
                    {settings.bfiu_max_attempts}
                  </div>
                </div>
                <div style={{ fontSize:10, color:"var(--text3)", marginTop:3 }}>
                  BFIU §3.3 mandates max 10 per session.
                </div>
              </div>
              <div>
                <label style={{ fontSize:11, fontWeight:700, color:"var(--text2)",
                  textTransform:"uppercase", letterSpacing:"0.05em", display:"block", marginBottom:5 }}>
                  Max Sessions / Day
                </label>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <input type="range" min="1" max="3" step="1"
                    value={settings.bfiu_max_sessions} onChange={e => set("bfiu_max_sessions", parseInt(e.target.value))}
                    style={{ flex:1 }}/>
                  <div style={{ fontSize:16, fontWeight:800, color:"var(--accent)",
                    fontFamily:"var(--font-mono)", minWidth:44, textAlign:"center" }}>
                    {settings.bfiu_max_sessions}
                  </div>
                </div>
                <div style={{ fontSize:10, color:"var(--text3)", marginTop:3 }}>
                  BFIU §3.3 mandates max 2 sessions per day.
                </div>
              </div>
            </div>
          </Section>

          {/* 6. Security */}
          <Section icon={Shield} title="Security & Access"
            sub="CORS, API access, and allowed origins">
            <Field label="Allowed Origins (comma-separated)" k="allowed_origins"
              value={settings.allowed_origins} onChange={set} mono
              hint="e.g. https://ekyc.yourcompany.com,https://agent.yourcompany.com"/>
            <div style={{ padding:"10px 14px", borderRadius:"var(--radius-sm)",
              background:"var(--bg3)", border:"1px solid var(--border)",
              fontSize:11, color:"var(--text3)", lineHeight:1.7 }}>
              ⚠️ In production, restrict origins to your institution's domains only.
              Never use * (wildcard) in production per BFIU §4.5 security requirements.
            </div>
          </Section>

          {/* Save button */}
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end", marginTop:8 }}>
            <Btn size="lg" variant="ghost" onClick={fetchSettings}>
              <RotateCcw size={13}/> Discard Changes
            </Btn>
            <Btn size="lg" onClick={save} loading={saving} variant={saved ? "success" : "primary"}>
              {saved
                ? <><CheckCircle size={14}/> All Settings Saved!</>
                : <><Save size={14}/> Save All Settings</>}
            </Btn>
          </div>
        </>
      )}
    </div>
  )
}
