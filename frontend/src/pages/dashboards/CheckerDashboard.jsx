import { useEffect, useState } from "react"
import { CheckSquare, Clock, XCircle, AlertTriangle, ArrowRight } from "lucide-react"
import StatCard from "../../components/ui/StatCard"
import Card from "../../components/ui/Card"
import Button from "../../components/ui/Button"
import Badge from "../../components/ui/Badge"
import { api } from "../../hooks/useApi"
import { toast } from "react-hot-toast"

export default function CheckerDashboard() {
  const [queue, setQueue] = useState([])
  const [acting, setActing] = useState(null)

  const load = () => {
    api.get("/api/v1/kyc/profiles?limit=10").then(r => setQueue(r.data?.profiles||[])).catch(()=>{})
  }

  useEffect(() => { load() }, [])

  const pending = queue.filter(p => p.status === "PENDING" || p.verdict === "REVIEW")

  // BFIU §4.3 Maker-Checker: Checker must explicitly approve/reject with confirmation
  const handleDecide = async (profile, action) => {
    const verb = action === "approve" ? "APPROVE" : "REJECT"
    const confirmed = window.confirm(
      \`BFIU §4.3 Maker-Checker Confirmation\n\nAre you sure you want to \${verb} this KYC profile?\n\nCustomer: \${profile.full_name || profile.session_id}\nKYC Type: \${profile.kyc_type}\nRisk Grade: \${profile.risk_grade}\n\nThis action is logged in the immutable audit trail.\`
    )
    if (!confirmed) return
    setActing(profile.session_id)
    try {
      const endpoint = \`/api/v1/kyc/profile/\${profile.session_id}/\${action}\`
      await api.patch(endpoint, { checker_note: \`\${verb} by Checker — BFIU §4.3\` })
      toast.success(\`\${verb}D — audit log updated (BFIU §4.3)\`)
      load()
    } catch(e) {
      toast.error(e?.response?.data?.detail || \`\${verb} failed\`)
    } finally { setActing(null) }
  }

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
              <p className="text-xs text-gray-400">{p.kyc_type} Â· Risk: {p.risk_grade}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge color={p.edd_required?"yellow":"blue"}>{p.status}</Badge>
              <div style={{display:"flex",gap:4}}>
                <Button size="xs" variant="success"
                  disabled={acting===p.session_id}
                  onClick={() => handleDecide(p, "approve")}>
                  Approve
                </Button>
                <Button size="xs" variant="danger"
                  disabled={acting===p.session_id}
                  onClick={() => handleDecide(p, "reject")}>
                  Reject
                </Button>
              </div>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}
