import { useEffect } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Toaster } from "react-hot-toast"
import { useAuthStore } from "./store/authStore"
import AppLayout   from "./components/layout/AppLayout"
import Login       from "./pages/Login"
import Dashboard   from "./pages/Dashboard"
import KYCWizard   from "./pages/KYCWizard"
import Sessions    from "./pages/Sessions"
import ReviewQueue from "./pages/ReviewQueue"
import AuditLog    from "./pages/AuditLog"
import PEPManagement from "./pages/PEPManagement"
import NotFound    from "./pages/NotFound"

function RequireAuth({ children }) {
  const { token } = useAuthStore()
  return token ? children : <Navigate to="/login" replace/>
}

export default function App() {
  const { theme } = useAuthStore()

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
  }, [theme])

  return (
    <BrowserRouter>
      <Toaster position="top-right" containerStyle={{ top: 60 }}/>
      <Routes>
        <Route path="/login" element={<Login/>}/>
        <Route path="/" element={<Navigate to="/dashboard" replace/>}/>

        <Route path="/" element={<RequireAuth><AppLayout/></RequireAuth>}>
          <Route path="dashboard"    element={<Dashboard/>}/>
          <Route path="kyc/new"      element={<KYCWizard/>}/>
          <Route path="kyc/sessions" element={<Sessions/>}/>
          <Route path="kyc/queue"    element={<Sessions/>}/>
          <Route path="review"       element={<ReviewQueue/>}/>
          <Route path="audit"        element={<AuditLog/>}/>
          <Route path="pep"          element={<PEPManagement/>}/>
          <Route path="edd"          element={<Dashboard/>}/>
          <Route path="screening"    element={<Dashboard/>}/>
          <Route path="reports"      element={<Dashboard/>}/>
          <Route path="risk"         element={<Dashboard/>}/>
          <Route path="institutions" element={<Dashboard/>}/>
          <Route path="users"        element={<Dashboard/>}/>
          <Route path="system"       element={<Dashboard/>}/>
          <Route path="settings"     element={<Dashboard/>}/>
          <Route path="*"            element={<NotFound/>}/>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
