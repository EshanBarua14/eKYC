import { useNavigate } from "react-router-dom"
import Button from "../components/ui/Button"
import { Home } from "lucide-react"
export default function NotFound() {
  const navigate = useNavigate()
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <p className="text-6xl font-bold text-gray-200 dark:text-gray-800">404</p>
      <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mt-2">Page not found</h2>
      <p className="text-sm text-gray-400 mt-1">The page you're looking for doesn't exist</p>
      <Button className="mt-4" onClick={() => navigate("/dashboard")} icon={<Home size={14}/>}>Back to Dashboard</Button>
    </div>
  )
}
