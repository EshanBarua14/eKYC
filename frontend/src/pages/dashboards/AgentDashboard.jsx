import { useEffect, useState } from "react"
import { Fingerprint, Clock, CheckCircle, XCircle, Plus, ArrowRight } from "lucide-react"
import StatCard from "../../components/ui/StatCard"
import Card from "../../components/ui/Card"
import Button from "../../components/ui/Button"
import Badge from "../../components/ui/Badge"
import { api } from "../../hooks/useApi"

export default function AgentDashboard() {
  const [sessions, setSessions] = useState([])

  useEffect(() => {
    api.get("/api/v1/kyc/profiles?limit=5").then(r => setSessions(r.data?.profiles||[])).catch(()=>{})
  }, [])

  const statusBadge = (s) => {
    const map = { MATCHED:"green", FAILED:"red", REVIEW:"yellow", PENDING:"gray" }
    return <Badge color={map[s]||"gray"}>{s}</Badge>
  }

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="page-title">Field Agent Dashboard</h2>
          <p className="text-sm text-gray-400 mt-1">Conduct eKYC verifications</p>
        </div>
        <Button onClick={() => (()=>{})("/kyc/new")} icon={<Plus size={14}/>}>
          New eKYC
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Today's Sessions" value={sessions.length} icon={<Fingerprint size={18}/>} color="blue"/>
        <StatCard title="Matched"  value={sessions.filter(s=>s.verdict==="MATCHED").length}  icon={<CheckCircle size={18}/>} color="green"/>
        <StatCard title="Review"   value={sessions.filter(s=>s.verdict==="REVIEW").length}   icon={<Clock size={18}/>}       color="amber"/>
        <StatCard title="Failed"   value={sessions.filter(s=>s.verdict==="FAILED").length}   icon={<XCircle size={18}/>}     color="red"/>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="section-title mb-0">Recent Sessions</h3>
          <Button variant="ghost" size="sm" onClick={() => (()=>{})("/kyc/sessions")} iconRight={<ArrowRight size={12}/>}>
            View all
          </Button>
        </div>
        {sessions.length === 0 ? (
          <div className="text-center py-8">
            <Fingerprint size={32} className="text-gray-300 mx-auto mb-2"/>
            <p className="text-sm text-gray-400">No sessions yet — start your first eKYC</p>
            <Button className="mt-3" size="sm" onClick={() => (()=>{})("/kyc/new")} icon={<Plus size={12}/>}>
              Start eKYC
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {sessions.map(s => (
              <div key={s.id||s.session_id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                <div>
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{s.session_id||s.id}</p>
                  <p className="text-xs text-gray-400">{s.created_at ? new Date(s.created_at).toLocaleString("en-BD") : "—"}</p>
                </div>
                <div className="flex items-center gap-2">
                  {statusBadge(s.verdict||s.status)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
