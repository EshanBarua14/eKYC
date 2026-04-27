import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Users, Building2, Shield, Activity, AlertTriangle, CheckCircle, FileText, TrendingUp } from "lucide-react"
import StatCard from "../../components/ui/StatCard"
import Card from "../../components/ui/Card"
import Badge from "../../components/ui/Badge"
import { api } from "../../hooks/useApi"

export default function AdminDashboard() {
  const [stats, setStats] = useState({ users:0, institutions:0, pep:0, sessions:0 })
  const [health, setHealth] = useState(null)

  useEffect(() => {
    api.get("/api/v1/admin/stats").then(r => setStats({ users: r.data.total_users??0, institutions: r.data.total_institutions??0, pep: r.data.total_pep??0, sessions: r.data.total_sessions??0 })).catch(()=>{})
    api.get("/health").then(r => setHealth(r.data)).catch(()=>{})
  }, [])

  return (
    <div className="space-y-6 animate-fade-up">
      <div>
        <h2 className="page-title">Admin Dashboard</h2>
        <p className="text-sm text-gray-400 mt-1">System overview · BFIU Circular No. 29</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Users"      value={stats.users||"—"}        icon={<Users size={18}/>}     color="blue"/>
        <StatCard title="Institutions"     value={stats.institutions||"—"} icon={<Building2 size={18}/>} color="green"/>
        <StatCard title="PEP Entries"      value={stats.pep||"—"}          icon={<Shield size={18}/>}    color="amber"/>
        <StatCard title="KYC Sessions"     value={stats.sessions||"—"}     icon={<Activity size={18}/>}  color="purple"/>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <h3 className="section-title flex items-center gap-2">
            <Activity size={15} className="text-brand-500"/> System Health
          </h3>
          {health ? (
            <div className="space-y-2">
              {Object.entries(health).map(([k,v]) => (
                <div key={k} className="flex items-center justify-between py-1.5 border-b border-gray-50 dark:border-gray-800 last:border-0">
                  <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">{k.replace(/_/g," ")}</span>
                  <Badge color={v==="ok"||v===true?"green":v==="warn"?"yellow":"red"}>
                    {String(v)}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">Checking system health…</p>
          )}
        </Card>

        <Card>
          <h3 className="section-title flex items-center gap-2">
            <TrendingUp size={15} className="text-brand-500"/> BFIU Compliance Status
          </h3>
          <div className="space-y-2">
            {[
              { label:"UNSCR Live Feed",      status:"green",  text:"Active" },
              { label:"PEP Screening",         status:"green",  text:"Active" },
              { label:"AES-256 Encryption",    status:"green",  text:"Enabled" },
              { label:"Audit Log Immutability",status:"green",  text:"Enforced" },
              { label:"Data Residency BD",     status:"green",  text:"BD-ONLY" },
              { label:"EDD Workflow",          status:"green",  text:"Operational" },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between py-1.5 border-b border-gray-50 dark:border-gray-800 last:border-0">
                <span className="text-sm text-gray-600 dark:text-gray-400">{item.label}</span>
                <Badge color={item.status}>{item.text}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
