import { useEffect, useState } from "react"
import { CheckCircle, XCircle, AlertTriangle, Eye } from "lucide-react"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import Badge from "../components/ui/Badge"
import Table from "../components/ui/Table"
import Modal from "../components/ui/Modal"
import { api } from "../hooks/useApi"
import { notify } from "../components/ui/Toast"

export default function ReviewQueue() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading]   = useState(true)
  const [selected, setSelected] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get("/api/v1/kyc/profiles?limit=50")
      setProfiles(res.data?.profiles || [])
    } catch { notify.error("Failed to load review queue") }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const approve = async (id) => {
    try {
      await api.patch(`/api/v1/kyc/profile/${id}/approve`)
      notify.success("Profile approved ✓")
      load()
    } catch(e) { notify.error(e.response?.data?.detail || "Approval failed") }
  }

  const reject = async (id) => {
    try {
      await api.patch(`/api/v1/kyc/profile/${id}/reject`)
      notify.warning("Profile rejected")
      load()
    } catch { notify.error("Rejection failed") }
  }

  const cols = [
    { header:"Session ID", key:"session_id" },
    { header:"Name",       key:"full_name"  },
    { header:"KYC Type",   key:"kyc_type",  render: v => <Badge color="blue">{v}</Badge> },
    { header:"Risk",       key:"risk_grade", render: v => <Badge color={v==="HIGH"?"red":v==="MEDIUM"?"yellow":"green"}>{v}</Badge> },
    { header:"Status",     key:"status",    render: v => <Badge color={v==="APPROVED"?"green":v==="REJECTED"?"red":v==="EDD_REQUIRED"?"purple":"yellow"}>{v}</Badge> },
    { header:"EDD",        key:"edd_required", render: v => v ? <Badge color="red">EDD</Badge> : <Badge color="gray">No</Badge> },
    { header:"Actions",    key:"session_id", render: (v, row) => (
      <div className="flex gap-1.5">
        <Button size="xs" variant="ghost" icon={<Eye size={11}/>} onClick={()=>setSelected(row)}>View</Button>
        {row.status==="PENDING"||row.status==="EDD_REQUIRED" ? <>
          <Button size="xs" variant="success" icon={<CheckCircle size={11}/>} onClick={()=>approve(v)}>Approve</Button>
          <Button size="xs" variant="danger"  icon={<XCircle size={11}/>}    onClick={()=>reject(v)}>Reject</Button>
        </> : null}
      </div>
    )},
  ]

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">Review Queue</h2>
          <p className="text-sm text-gray-400 mt-1">{profiles.filter(p=>p.status==="PENDING").length} pending reviews</p>
        </div>
        <Button variant="secondary" onClick={load}>Refresh</Button>
      </div>
      <Card className="p-0 overflow-hidden">
        <Table columns={cols} data={profiles} loading={loading} emptyTitle="No profiles in queue"/>
      </Card>

      <Modal open={!!selected} onClose={()=>setSelected(null)} title="KYC Profile Detail" size="lg">
        {selected && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(selected).map(([k,v]) => (
                <div key={k} className="space-y-0.5">
                  <p className="text-xs text-gray-400 uppercase tracking-wide">{k.replace(/_/g," ")}</p>
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{String(v??"—")}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
