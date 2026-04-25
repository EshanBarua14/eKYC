import { useEffect, useState } from "react"
import { Plus, Search } from "lucide-react"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import Badge from "../components/ui/Badge"
import Table from "../components/ui/Table"
import Input from "../components/ui/Input"
import Modal from "../components/ui/Modal"
import { api } from "../hooks/useApi"
import { notify } from "../components/ui/Toast"
import { useAuthStore } from "../store/authStore"

export default function PEPManagement() {
  const { role } = useAuthStore()
  const [peps, setPeps]     = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm]     = useState({ full_name_en:"", category:"PEP", position:"", ministry_or_org:"", risk_level:"HIGH" })

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get("/api/v1/pep/entries?limit=100")
      setPeps(res.data?.entries || res.data || [])
    } catch { notify.error("Failed to load PEP list") }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const filtered = peps.filter(p =>
    p.full_name_en?.toLowerCase().includes(search.toLowerCase()) ||
    p.category?.toLowerCase().includes(search.toLowerCase())
  )

  const addPEP = async () => {
    try {
      await api.post("/api/v1/pep/entries", form)
      notify.success("PEP entry added ✓")
      setAddOpen(false)
      load()
    } catch(e) { notify.error(e.response?.data?.detail || "Failed to add PEP") }
  }

  const deactivate = async (id) => {
    try {
      await api.patch(`/api/v1/pep/entries/${id}/deactivate`)
      notify.warning("PEP entry deactivated")
      load()
    } catch { notify.error("Deactivation failed") }
  }

  const cols = [
    { header:"Name (EN)",   key:"full_name_en" },
    { header:"Name (BN)",   key:"full_name_bn", render: v => <span className="font-sans">{v||"—"}</span> },
    { header:"Category",    key:"category",    render: v => <Badge color="purple">{v}</Badge> },
    { header:"Position",    key:"position",    render: v => <span className="text-xs">{v||"—"}</span> },
    { header:"Risk",        key:"risk_level",  render: v => <Badge color={v==="HIGH"?"red":v==="MEDIUM"?"yellow":"green"}>{v}</Badge> },
    { header:"Status",      key:"status",      render: v => <Badge color={v==="ACTIVE"?"green":"gray"}>{v}</Badge> },
    { header:"Source",      key:"source",      render: v => <Badge color="blue">{v}</Badge> },
    ...(role==="ADMIN"? [{ header:"Action", key:"id", render: (v) => (
      <Button size="xs" variant="danger" onClick={()=>deactivate(v)}>Deactivate</Button>
    )}] : []),
  ]

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">PEP List Management</h2>
          <p className="text-sm text-gray-400 mt-1">Politically Exposed Persons · BFIU §4.2</p>
        </div>
        {role === "ADMIN" && (
          <Button icon={<Plus size={14}/>} onClick={() => setAddOpen(true)}>Add PEP Entry</Button>
        )}
      </div>

      <div className="max-w-xs">
        <Input placeholder="Search by name or category…" value={search}
          onChange={e=>setSearch(e.target.value)} icon={<Search size={14}/>}/>
      </div>

      <Card className="p-0 overflow-hidden">
        <Table columns={cols} data={filtered} loading={loading}
          emptyTitle="No PEP entries" emptyDesc="Load seed data or add entries manually"/>
      </Card>

      <Modal open={addOpen} onClose={()=>setAddOpen(false)} title="Add PEP Entry">
        <div className="space-y-3">
          <Input label="Full Name (EN) *" value={form.full_name_en} onChange={e=>setForm(p=>({...p,full_name_en:e.target.value}))}/>
          <div>
            <label className="label">Category</label>
            <select className="input" value={form.category} onChange={e=>setForm(p=>({...p,category:e.target.value}))}>
              {["PEP","IP","PEP_FAMILY","PEP_ASSOCIATE"].map(c=><option key={c}>{c}</option>)}
            </select>
          </div>
          <Input label="Position" value={form.position} onChange={e=>setForm(p=>({...p,position:e.target.value}))}/>
          <Input label="Ministry / Organisation" value={form.ministry_or_org} onChange={e=>setForm(p=>({...p,ministry_or_org:e.target.value}))}/>
          <div>
            <label className="label">Risk Level</label>
            <select className="input" value={form.risk_level} onChange={e=>setForm(p=>({...p,risk_level:e.target.value}))}>
              {["HIGH","MEDIUM","LOW"].map(r=><option key={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={()=>setAddOpen(false)}>Cancel</Button>
            <Button className="flex-1" onClick={addPEP}>Add Entry</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
