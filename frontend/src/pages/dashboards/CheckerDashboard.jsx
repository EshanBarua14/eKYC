import { useEffect, useState } from "react"
import { CheckSquare, Clock, XCircle, AlertTriangle, ArrowRight } from "lucide-react"
import StatCard from "../../components/ui/StatCard"
import Card from "../../components/ui/Card"
import Button from "../../components/ui/Button"
import Badge from "../../components/ui/Badge"
import { api } from "../../hooks/useApi"

export default function CheckerDashboard() {
  const [queue, setQueue] = useState([])

  useEffect(() => {
    api.get("/api/v1/kyc/profiles?limit=10").then(r => setQueue(r.data?.profiles||[])).catch(()=>{})
  }, [])

  const pending = queue.filter(p => p.status === "PENDING" || p.verdict === "REVIEW")

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="page-title">Checker Dashboard</h2>
          <p className="text-sm text-gray-400 mt-1">Review and approve KYC submissions</p>
        </div>
        <Button onClick={() => {}} icon={<CheckSquare size={14}/>}>
          Open Review Queue
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Pending Review" value={pending.length}                                  icon={<Clock size={18}/>}        color="amber"/>
        <StatCard title="Approved Today" value={queue.filter(p=>p.status==="APPROVED").length}  icon={<CheckSquare size={18}/>}  color="green"/>
        <StatCard title="Rejected"       value={queue.filter(p=>p.status==="REJECTED").length}  icon={<XCircle size={18}/>}      color="red"/>
        <StatCard title="EDD Required"   value={queue.filter(p=>p.edd_required).length}         icon={<AlertTriangle size={18}/>} color="purple"/>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="section-title mb-0">Review Queue</h3>
          <Button variant="ghost" size="sm" onClick={() => {}} iconRight={<ArrowRight size={12}/>}>
            View all
          </Button>
        </div>
        {pending.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No pending reviews</p>
        ) : pending.slice(0,5).map((p,i) => (
          <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl mb-2">
            <div>
              <p className="text-sm font-medium">{p.full_name || p.session_id}</p>
              <p className="text-xs text-gray-400">{p.kyc_type} · Risk: {p.risk_grade}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge color={p.edd_required?"yellow":"blue"}>{p.status}</Badge>
              <Button size="xs" onClick={() => {}}>Review</Button>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}
