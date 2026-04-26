import { useEffect, useState } from "react"
import { AlertTriangle, Shield, Search, FileText, ExternalLink } from "lucide-react"
import StatCard from "../../components/ui/StatCard"
import Card from "../../components/ui/Card"
import Button from "../../components/ui/Button"
import Badge from "../../components/ui/Badge"
import { api } from "../../hooks/useApi"
import { notify } from "../../components/ui/Toast"

export default function ComplianceDashboard() {
  const [edd, setEdd]       = useState([])
  const [screening, setScreening] = useState({ pep_hits:0, unscr_hits:0, adverse_hits:0 })

  useEffect(() => {
    api.get("/api/v1/compliance/edd-cases?limit=5").then(r => setEdd(r.data?.queue||[])).catch(()=>{})
    api.get("/api/v1/compliance/metrics").then(r => setScreening(r.data||{})).catch(()=>{})
  }, [])

  const escalate = async (id) => {
    try {
      await api.post(`/api/v1/edd/${id}/escalate-bfiu`, {})
      notify.bfiu("Case escalated to BFIU successfully")
    } catch { notify.error("Escalation failed") }
  }

  return (
    <div className="space-y-6 animate-fade-up">
      <div>
        <h2 className="page-title">Compliance Officer Dashboard</h2>
        <p className="text-sm text-gray-400 mt-1">EDD, PEP, UNSCR, adverse media monitoring</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="EDD Open"      value={edd.length}              icon={<AlertTriangle size={18}/>} color="red"/>
        <StatCard title="PEP Hits"      value={screening.pep_hits||0}   icon={<Shield size={18}/>}       color="amber"/>
        <StatCard title="UNSCR Hits"    value={screening.unscr_hits||0} icon={<Search size={18}/>}       color="purple"/>
        <StatCard title="Adverse Media" value={screening.adverse_hits||0} icon={<FileText size={18}/>}   color="blue"/>
      </div>

      <Card>
        <h3 className="section-title flex items-center gap-2">
          <AlertTriangle size={15} className="text-red-500"/> EDD Queue
        </h3>
        {edd.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No open EDD cases</p>
        ) : edd.map((item, i) => (
          <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl mb-2">
            <div>
              <p className="text-sm font-medium">{item.customer_name || item.session_id}</p>
              <p className="text-xs text-gray-400">Risk: {item.risk_level} · {item.trigger_reason}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge color="red">EDD</Badge>
              <Button size="xs" variant="danger"
                onClick={() => escalate(item.id)}
                icon={<ExternalLink size={11}/>}>
                Escalate to BFIU
              </Button>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}
