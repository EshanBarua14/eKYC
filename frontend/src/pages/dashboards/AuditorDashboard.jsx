import { useEffect, useState } from "react"
import { FileText, BarChart3, Shield, Download, ArrowRight } from "lucide-react"
import StatCard from "../../components/ui/StatCard"
import Card from "../../components/ui/Card"
import Button from "../../components/ui/Button"
import Badge from "../../components/ui/Badge"
import { api } from "../../hooks/useApi"
import { notify } from "../../components/ui/Toast"

export default function AuditorDashboard() {
  const [logs, setLogs] = useState([])

  useEffect(() => {
    api.get("/api/v1/audit/log?limit=5").then(r => setLogs(r.data?.logs||[])).catch(()=>{})
  }, [])

  const exportReport = async () => {
    try {
      notify.info("Generating BFIU report…")
      const res = await api.post("/api/v1/bfiu-report/current-month", {})
      notify.success("Report generated successfully")
    } catch {
      notify.error("Report generation failed")
    }
  }

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="page-title">Auditor Dashboard</h2>
          <p className="text-sm text-gray-400 mt-1">Audit logs, reports, risk analysis</p>
        </div>
        <Button onClick={exportReport} icon={<Download size={14}/>} variant="outline">
          Export BFIU Report
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Audit Events"  value={logs.length} icon={<FileText size={18}/>}  color="blue"/>
        <StatCard title="Reports"       value="—"           icon={<BarChart3 size={18}/>} color="green"/>
        <StatCard title="Risk Alerts"   value="—"           icon={<Shield size={18}/>}    color="amber"/>
        <StatCard title="Compliance"    value="100%"        icon={<Shield size={18}/>}    color="purple"/>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="section-title mb-0">Recent Audit Events</h3>
          <Button variant="ghost" size="sm" onClick={() => {}} iconRight={<ArrowRight size={12}/>}>View all</Button>
        </div>
        {logs.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No audit events</p>
        ) : logs.map((l,i) => (
          <div key={i} className="flex items-center justify-between p-3 border-b border-gray-50 dark:border-gray-800 last:border-0">
            <div>
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{l.event_type||l.action}</p>
              <p className="text-xs text-gray-400">{l.created_at ? new Date(l.created_at).toLocaleString("en-BD") : "—"}</p>
            </div>
            <Badge color="blue">{l.actor_role||"SYSTEM"}</Badge>
          </div>
        ))}
      </Card>
    </div>
  )
}
