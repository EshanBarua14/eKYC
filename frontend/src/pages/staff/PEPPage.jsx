/**
 * PEP List Management — BFIU §4.2
 * Full CRUD for PEP/IP entries
 */
import { useState, useEffect } from "react"
import { toast } from "react-hot-toast"
import { API, getToken } from "../../config"
import { Shield, Plus, Search, RefreshCw, X } from "lucide-react"

const token = () => getToken() || localStorage.getItem("ekyc_admin_token") || ""
const apiFetch = (path, opts={}) => fetch(`${API}${path}`, {
  ...opts,
  headers: { "Content-Type":"application/json", Authorization:`Bearer ${token()}`, ...(opts.headers||{}) }
}).then(r => r.json())

export default function PEPManagementPage() {
  const [entries, setEntries]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [search, setSearch]     = useState("")
  const [showAdd, setShowAdd]   = useState(false)
  const [form, setForm]         = useState({
    full_name_en:"", full_name_bn:"", category:"PEP",
    position:"", ministry_or_org:"", nationality:"BD",
    risk_level:"HIGH", notes:""
  })

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const d = await apiFetch("/api/v1/pep/entries?limit=200")
      setEntries(d.entries || d.pep_entries || d || [])
    } catch { setEntries([]) }
    finally { setLoading(false) }
  }

  const addEntry = async () => {
    if (!form.full_name_en) { toast.error("Name required"); return }
    try {
      await apiFetch("/api/v1/pep/entries", { method:"POST", body: JSON.stringify(form) })
      toast.success("PEP entry added ✓ (BFIU §4.2)")
      setShowAdd(false)
      setForm({ full_name_en:"", full_name_bn:"", category:"PEP", position:"", ministry_or_org:"", nationality:"BD", risk_level:"HIGH", notes:"" })
      load()
    } catch(e) { toast.error("Failed to add PEP entry") }
  }

  const deactivate = async (id) => {
    try {
      await apiFetch(`/api/v1/pep/entries/${id}/deactivate`, { method:"PATCH" })
      toast.success("PEP entry deactivated")
      load()
    } catch { toast.error("Deactivation failed") }
  }

  const f = k => e => setForm(p => ({...p, [k]: e.target.value}))

  const filtered = entries.filter(e =>
    !search ||
    e.full_name_en?.toLowerCase().includes(search.toLowerCase()) ||
    e.full_name_bn?.includes(search) ||
    e.category?.toLowerCase().includes(search.toLowerCase()) ||
    e.position?.toLowerCase().includes(search.toLowerCase())
  )

  const riskColor = { HIGH:"badge-red", MEDIUM:"badge-yellow", LOW:"badge-green" }
  const catColor  = { PEP:"badge-red", IP:"badge-yellow", PEP_FAMILY:"badge-blue", PEP_ASSOCIATE:"badge-accent" }

  return (
    <div>
      <div className="page-header" style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between" }}>
        <div>
          <div className="page-title">PEP List Management</div>
          <div className="page-subtitle">Politically Exposed Persons · BFIU §4.2 · {entries.filter(e=>e.status==="ACTIVE").length} active entries</div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(!showAdd)}>
          <Plus size={13}/> Add PEP Entry
        </button>
      </div>

      <div className="alert alert-warning" style={{ marginBottom:16 }}>
        <Shield size={14} style={{ flexShrink:0 }}/>
        <span>BFIU §4.2: PEP/IP customers require EDD. Any match triggers Enhanced Due Diligence workflow automatically.</span>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="data-card" style={{ marginBottom:16 }}>
          <div className="data-card-header">
            <span className="data-card-title"><Plus size={14}/> New PEP Entry</span>
            <button className="btn btn-outline btn-sm" onClick={() => setShowAdd(false)}><X size={12}/></button>
          </div>
          <div className="data-card-body">
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
              {[["Full Name (EN) *","full_name_en"],["Full Name (BN)","full_name_bn"],
                ["Position","position"],["Ministry / Org","ministry_or_org"],
                ["Nationality (ISO)","nationality"],["Notes","notes"]].map(([l,k]) => (
                <div key={k}>
                  <label className="input-label">{l}</label>
                  <input className="glass-input" value={form[k]} onChange={f(k)} placeholder={l.replace(" *","")}/>
                </div>
              ))}
              <div>
                <label className="input-label">Category</label>
                <select className="glass-input" value={form.category} onChange={f("category")}>
                  {["PEP","IP","PEP_FAMILY","PEP_ASSOCIATE"].map(c=><option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="input-label">Risk Level</label>
                <select className="glass-input" value={form.risk_level} onChange={f("risk_level")}>
                  {["HIGH","MEDIUM","LOW"].map(r=><option key={r}>{r}</option>)}
                </select>
              </div>
            </div>
            <div style={{ display:"flex", gap:10, marginTop:14 }}>
              <button className="btn btn-primary btn-md" onClick={addEntry}><Plus size={13}/> Add Entry</button>
              <button className="btn btn-outline btn-md" onClick={() => setShowAdd(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Search */}
      <div style={{ display:"flex", gap:10, marginBottom:14, alignItems:"center" }}>
        <div style={{ position:"relative", flex:1, maxWidth:340 }}>
          <Search size={14} style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)", color:"var(--text3)" }}/>
          <input className="glass-input" value={search} onChange={e=>setSearch(e.target.value)}
            placeholder="Search by name, category, position…" style={{ paddingLeft:32 }}/>
        </div>
        <button className="btn btn-outline btn-sm" onClick={load}><RefreshCw size={12}/> Refresh</button>
        <span className="badge badge-gray">{filtered.length} results</span>
      </div>

      {/* Table */}
      <div className="data-card" style={{ padding:0, overflow:"hidden" }}>
        {loading ? (
          <div style={{ padding:40, textAlign:"center", color:"var(--text3)" }}>Loading PEP entries…</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🛡️</div>
            <div className="empty-title">No PEP entries found</div>
            <div className="empty-desc">Load seed data or add entries manually</div>
            <button className="btn btn-primary btn-sm" style={{ marginTop:12 }} onClick={() => setShowAdd(true)}>
              <Plus size={12}/> Add First Entry
            </button>
          </div>
        ) : (
          <table className="glass-table">
            <thead><tr>
              <th>Name (EN)</th><th>Name (BN)</th><th>Category</th>
              <th>Position</th><th>Risk</th><th>Status</th><th>Source</th><th>Action</th>
            </tr></thead>
            <tbody>
              {filtered.map((e,i) => (
                <tr key={i}>
                  <td style={{ fontWeight:600, color:"var(--text)" }}>{e.full_name_en}</td>
                  <td style={{ fontFamily:"serif", fontSize:13 }}>{e.full_name_bn||"—"}</td>
                  <td><span className={`badge ${catColor[e.category]||"badge-gray"}`}>{e.category}</span></td>
                  <td style={{ fontSize:11, color:"var(--text2)", maxWidth:180, overflow:"hidden", textOverflow:"ellipsis" }}>{e.position||"—"}</td>
                  <td><span className={`badge ${riskColor[e.risk_level]||"badge-gray"}`}>{e.risk_level}</span></td>
                  <td><span className={`badge ${e.status==="ACTIVE"?"badge-green":"badge-gray"}`}>{e.status||"ACTIVE"}</span></td>
                  <td><span className="badge badge-blue">{e.source||"MANUAL"}</span></td>
                  <td>
                    {(e.status==="ACTIVE"||!e.status) && (
                      <button className="btn btn-danger btn-sm" onClick={() => deactivate(e.id)}>
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
