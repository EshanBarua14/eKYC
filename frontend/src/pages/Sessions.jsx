import { useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import Badge from "../components/ui/Badge"
import Table from "../components/ui/Table"
import { api } from "../hooks/useApi"
import { notify } from "../components/ui/Toast"

export default function Sessions() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading]   = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get("/api/v1/kyc/sessions?limit=100")
      setSessions(res.data?.sessions || res.data?.profiles || [])
    } catch { notify.error("Failed to load sessions") }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const cols = [
    { header:"Session ID", key:"session_id", render: v => <span className="font-mono text-xs">{v}</span> },
    { header:"Name",       key:"full_name"  },
    { header:"KYC Type",   key:"kyc_type",   render: v => <Badge color="blue">{v||"—"}</Badge> },
    { header:"Verdict",    key:"verdict",    render: v => <Badge color={v==="MATCHED"?"green":v==="FAILED"?"red":"yellow"}>{v||"—"}</Badge> },
    { header:"Status",     key:"status",     render: v => <Badge color={v==="APPROVED"?"green":v==="REJECTED"?"red":"gray"}>{v||"—"}</Badge> },
    { header:"Risk",       key:"risk_grade", render: v => <Badge color={v==="HIGH"?"red":v==="MEDIUM"?"yellow":"green"}>{v||"—"}</Badge> },
    { header:"Created",    key:"created_at", render: v => v ? new Date(v).toLocaleString("en-BD") : "—" },
  ]

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">KYC Sessions</h2>
          <p className="text-sm text-gray-400 mt-1">{sessions.length} total sessions</p>
        </div>
        <Button variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Refresh</Button>
      </div>
      <Card className="p-0 overflow-hidden">
        <Table columns={cols} data={sessions} loading={loading} emptyTitle="No sessions found"/>
      </Card>
    </div>
  )
}
