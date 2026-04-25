import { useAuthStore } from "../store/authStore"
import AdminDashboard      from "./dashboards/AdminDashboard"
import AgentDashboard      from "./dashboards/AgentDashboard"
import CheckerDashboard    from "./dashboards/CheckerDashboard"
import AuditorDashboard    from "./dashboards/AuditorDashboard"
import ComplianceDashboard from "./dashboards/ComplianceDashboard"
import MakerDashboard      from "./dashboards/MakerDashboard"

export default function Dashboard() {
  const { role } = useAuthStore()
  const map = {
    ADMIN:              <AdminDashboard/>,
    AGENT:              <AgentDashboard/>,
    MAKER:              <MakerDashboard/>,
    CHECKER:            <CheckerDashboard/>,
    AUDITOR:            <AuditorDashboard/>,
    COMPLIANCE_OFFICER: <ComplianceDashboard/>,
  }
  return map[role] || <AgentDashboard/>
}
