import { useState } from "react"
import { Outlet, useLocation } from "react-router-dom"
import Sidebar from "./Sidebar"
import TopBar from "./TopBar"
import Footer from "./Footer"
import { Toaster } from "react-hot-toast"

const PAGE_TITLES = {
  "/dashboard":    "Dashboard",
  "/kyc/new":      "New eKYC Onboarding",
  "/kyc/sessions": "My Sessions",
  "/kyc/queue":    "KYC Queue",
  "/review":       "Review Queue",
  "/edd":          "EDD Queue",
  "/screening":    "Screening",
  "/pep":          "PEP Management",
  "/audit":        "Audit Log",
  "/reports":      "Reports",
  "/risk":         "Risk Dashboard",
  "/institutions": "Institutions",
  "/users":        "User Management",
  "/system":       "System Health",
  "/settings":     "Settings",
}

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] || "eKYC Platform"

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)}/>

      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar onMenuClick={() => setSidebarOpen(true)} title={title}/>

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet/>
        </main>

        <Footer/>
      </div>

      <Toaster position="top-right" containerStyle={{ top: 60 }}/>
    </div>
  )
}
