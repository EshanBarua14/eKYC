import { useNavigate } from "react-router-dom"
import { Upload, Clock, CheckCircle, Plus } from "lucide-react"
import StatCard from "../../components/ui/StatCard"
import Card from "../../components/ui/Card"
import Button from "../../components/ui/Button"

export default function MakerDashboard() {
  const navigate = useNavigate()
  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="page-title">Maker Dashboard</h2>
          <p className="text-sm text-gray-400 mt-1">Submit KYC profiles for review</p>
        </div>
        <Button onClick={() => navigate("/kyc/new")} icon={<Plus size={14}/>}>New Submission</Button>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <StatCard title="Pending Review" value="—" icon={<Clock size={18}/>}       color="amber"/>
        <StatCard title="Approved"       value="—" icon={<CheckCircle size={18}/>} color="green"/>
        <StatCard title="Submitted"      value="—" icon={<Upload size={18}/>}      color="blue"/>
      </div>
      <Card>
        <p className="text-sm text-gray-400 text-center py-8">
          Create a new KYC submission to get started.
        </p>
        <div className="flex justify-center">
          <Button onClick={() => navigate("/kyc/new")} icon={<Plus size={14}/>}>Start New eKYC</Button>
        </div>
      </Card>
    </div>
  )
}
