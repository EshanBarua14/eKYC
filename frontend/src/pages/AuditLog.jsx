import { useEffect, useState } from "react"
import { Download, RefreshCw } from "lucide-react"
import Card from "../components/ui/Card"
import Button from "../components/ui/Button"
import Badge from "../components/ui/Badge"
import Table from "../components/ui/Table"
import { api } from "../hooks/useApi"
import { notify } from "../components/ui/Toast"

export default function AuditLog() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get("/api/v1/audit/logs?limit=100")
      setLogs(res.data?.logs || res.data || [])
    } catch { notify.error("Failed to load audit logs") }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const exportPDF = async () => {
    try {
      notify.info("Generating audit PDF…")
      await api.post("/api/v1/audit/export-pdf", {})
      notify.success("Audit PDF exported")
    } catch { notify.error("Export failed") }
  }

  const cols = [
    { header:"Event",       key:"event_type", render: v => <span className="font-mono text-xs">{v}</span> },
    { header:"Actor",       key:"actor_role",  render: v => <Badge color="blue">{v||"SYSTEM"}</Badge> },
    { header:"Session",     key:"session_id",  render: v => <span className="font-mono text-xs text-gray-400">{v||"—"}</span> },
    { header:"IP",          key:"ip_address",  render: v => <span className="text-xs text-gray-400">{v||"—"}</span> },
    { header:"Time (BST)",  key:"created_at",  render: v => v ? new Date(v).toLocaleString("en-BD") : "—" },
  ]

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="page-title">Audit Log</h2>
          <p className="text-sm text-gray-400 mt-1">Immutable audit trail · BFIU §5.1</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" icon={<RefreshCw size={14}/>} onClick={load}>Refresh</Button>
          <Button variant="outline"   icon={<Download size={14}/>}  onClick={exportPDF}>Export PDF</Button>
        </div>
      </div>
      <Card className="p-0 overflow-hidden">
        <Table columns={cols} data={logs} loading={loading}
          emptyTitle="No audit events" emptyDesc="Audit events will appear here"/>
      </Card>
    </div>
  )
}
