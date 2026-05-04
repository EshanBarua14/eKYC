import { useEffect, useState } from "react"
import { Plus, Search, RefreshCw, Clock, Shield } from "lucide-react"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import Badge from "../components/ui/Badge"
import Input from "../components/ui/Input"
import Modal from "../components/ui/Modal"
import { api } from "../hooks/useApi"
import { notify } from "../components/ui/Toast"
import { useAuthStore } from "../store/authStore"

function toBDTime(ts) {
  if (!ts) return "—"
  try {
    return new Date(ts).toLocaleString("en-BD", {
      timeZone:"Asia/Dhaka", year:"numeric", month:"short", day:"2-digit",
      hour:"2-digit", minute:"2-digit", hour12:false
    })
  } catch { return ts }
}

const CAT_COLOR = {
  DOMESTIC_PEP:"purple", FOREIGN_PEP:"violet", INTERNATIONAL_ORG:"indigo",
  FAMILY_MEMBER:"pink", CLOSE_ASSOCIATE:"orange", PEP:"purple", IP:"red",
  PEP_FAMILY:"pink", PEP_ASSOCIATE:"orange"
}

const LIMIT = 20

export default function PEPManagement() {
  const { role } = useAuthStore()
  const [peps, setPeps]       = useState([])
  const [total, setTotal]     = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage]       = useState(1)
  const [search, setSearch]   = useState("")
  const [lastSync, setLastSync] = useState(null)
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm]       = useState({
    full_name_en:"", full_name_bn:"", category:"DOMESTIC_PEP",
    position:"", ministry_or_org:"", risk_level:"HIGH", source:"MANUAL"
  })

  const load = async (p = page) => {
    setLoading(true)
    try {
      const offset = (p-1)*LIMIT
      const res = await api.get(`/api/v1/pep/entries?limit=${LIMIT}&offset=${offset}&status=ACTIVE`)
      const d = res.data
      const entries = d?.entries || d?.items || (Array.isArray(d) ? d : [])
      setPeps(entries)
      setTotal(d?.total ?? entries.length)
    } catch { notify.error("Failed to load PEP list") }
    finally { setLoading(false) }
  }

  const loadMeta = async () => {
    try {
      const res = await api.get("/api/v1/pep/meta")
      setLastSync(res.data?.last_updated || res.data?.last_sync || null)
    } catch {}
  }

  useEffect(() => { load(1); loadMeta() }, [])

  const filtered = peps.filter(p =>
    !search ||
    p.full_name_en?.toLowerCase().includes(search.toLowerCase()) ||
    p.full_name_bn?.includes(search) ||
    p.category?.toLowerCase().includes(search.toLowerCase()) ||
    p.position?.toLowerCase().includes(search.toLowerCase())
  )

  const addPEP = async () => {
    if (!form.full_name_en) return notify.error("Full name (EN) required")
    try {
      await api.post("/api/v1/pep/entries", form)
      notify.success("PEP entry added (BFIU §4.2)")
      setAddOpen(false)
      setForm({ full_name_en:"", full_name_bn:"", category:"DOMESTIC_PEP", position:"", ministry_or_org:"", risk_level:"HIGH", source:"MANUAL" })
      load(1); loadMeta()
    } catch(e) { notify.error(e.response?.data?.detail || "Failed to add PEP") }
  }

  const deactivate = async (id) => {
    if (!confirm("Deactivate this PEP entry?")) return
    try {
      await api.patch(`/api/v1/pep/entries/${id}/deactivate`)
      notify.warning("PEP entry deactivated")
      load(page); loadMeta()
    } catch { notify.error("Deactivation failed") }
  }

  const pages = Math.ceil(total / LIMIT)

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">PEP List Management</h2>
          <p className="text-sm text-gray-400 mt-1">
            Politically Exposed Persons · BFIU §4.2 ·{" "}
            <span className="font-semibold text-gray-600 dark:text-gray-300">{total} total entries</span>
          </p>
        </div>
        {role === "ADMIN" && (
          <div className="flex gap-2">
            <Button variant="secondary" icon={<RefreshCw size={14}/>} onClick={()=>{load(1);loadMeta()}}>Refresh</Button>
            <Button icon={<Plus size={14}/>} onClick={()=>setAddOpen(true)}>Add PEP Entry</Button>
          </div>
        )}
      </div>

      <div className="p-3 bg-amber-50 dark:bg-amber-950/20 rounded-xl border border-amber-200 dark:border-amber-800 flex items-center justify-between">
        <p className="text-xs text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
          <Shield size={12}/> BFIU §4.2: PEP/IP customers require EDD. Any match triggers Enhanced Due Diligence automatically.
        </p>
        {lastSync && (
          <p className="text-xs text-gray-400 flex items-center gap-1 flex-shrink-0 ml-4">
            <Clock size={11}/> Last sync: {toBDTime(lastSync)} BST
          </p>
        )}
      </div>

      <div className="flex gap-3 items-center justify-between">
        <Input placeholder="Search by name, category, position..."
          value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}}
          icon={<Search size={14}/>} className="max-w-sm"/>
        <div className="flex gap-3 text-xs text-gray-400">
          <span>{filtered.length} shown</span>
          {pages > 1 && <span>Page {page}/{pages}</span>}
        </div>
      </div>

      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
                {["Name","Bangla Name","Category","Position / Org","Country","Risk","Source","Status","Action"].map(h=>(
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
              {loading ? (
                <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Loading PEP registry...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                  <p className="font-medium">No PEP entries found</p>
                  <p className="text-xs mt-1">Add entries manually or sync from BFIU source</p>
                </td></tr>
              ) : filtered.map(p => (
                <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200 max-w-[150px] truncate">{p.full_name_en}</td>
                  <td className="px-4 py-3 font-sans text-gray-600 dark:text-gray-400 max-w-[120px] truncate">{p.full_name_bn||"—"}</td>
                  <td className="px-4 py-3 whitespace-nowrap"><Badge color={CAT_COLOR[p.category]||"gray"}>{p.category}</Badge></td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[180px] truncate">{[p.position,p.ministry_or_org].filter(Boolean).join(" · ")||"—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">{p.country||"Bangladesh"}</td>
                  <td className="px-4 py-3 whitespace-nowrap"><Badge color={p.risk_level==="HIGH"?"red":p.risk_level==="MEDIUM"?"amber":"green"}>{p.risk_level||"HIGH"}</Badge></td>
                  <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{p.source||"—"}</td>
                  <td className="px-4 py-3 whitespace-nowrap"><Badge color={p.status==="ACTIVE"?"green":"gray"}>{p.status||"ACTIVE"}</Badge></td>
                  <td className="px-4 py-3">
                    {role==="ADMIN" && p.status==="ACTIVE" ? (
                      <button onClick={()=>deactivate(p.id)}
                        className="px-2 py-1 text-xs font-medium text-red-600 bg-red-50 dark:bg-red-950/20 border border-red-200 rounded-lg hover:bg-red-100 transition-colors">
                        Deactivate
                      </button>
                    ) : <span className="text-xs text-gray-300">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{total} total · Showing {Math.min((page-1)*LIMIT+1,total)}–{Math.min(page*LIMIT,total)}</span>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={page<=1} onClick={()=>{setPage(p=>p-1);load(page-1)}}>← Prev</Button>
            <span className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs font-medium">{page}/{pages}</span>
            <Button variant="secondary" size="sm" disabled={page>=pages} onClick={()=>{setPage(p=>p+1);load(page+1)}}>Next →</Button>
          </div>
        </div>
      )}

      <Modal open={addOpen} onClose={()=>setAddOpen(false)} title="Add PEP Entry">
        <div className="space-y-3">
          <Input label="Full Name (English) *" value={form.full_name_en} onChange={e=>setForm(p=>({...p,full_name_en:e.target.value}))} placeholder="As per official records"/>
          <Input label="Full Name (Bangla)" value={form.full_name_bn} onChange={e=>setForm(p=>({...p,full_name_bn:e.target.value}))} placeholder="বাংলা নাম (optional)"/>
          <div>
            <label className="label">Category *</label>
            <select className="input" value={form.category} onChange={e=>setForm(p=>({...p,category:e.target.value}))}>
              {["DOMESTIC_PEP","FOREIGN_PEP","INTERNATIONAL_ORG","FAMILY_MEMBER","CLOSE_ASSOCIATE","IP"].map(c=><option key={c}>{c}</option>)}
            </select>
          </div>
          <Input label="Position / Title" value={form.position} onChange={e=>setForm(p=>({...p,position:e.target.value}))} placeholder="e.g. Minister, Secretary"/>
          <Input label="Ministry / Organisation" value={form.ministry_or_org} onChange={e=>setForm(p=>({...p,ministry_or_org:e.target.value}))} placeholder="e.g. Ministry of Finance"/>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Risk Level</label>
              <select className="input" value={form.risk_level} onChange={e=>setForm(p=>({...p,risk_level:e.target.value}))}>
                {["HIGH","MEDIUM","LOW"].map(r=><option key={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Source</label>
              <select className="input" value={form.source} onChange={e=>setForm(p=>({...p,source:e.target.value}))}>
                {["MANUAL","BFIU","UN_SANCTIONS","OPENSANCTIONS"].map(s=><option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={()=>setAddOpen(false)}>Cancel</Button>
            <Button className="flex-1" onClick={addPEP}>Add to Registry</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
