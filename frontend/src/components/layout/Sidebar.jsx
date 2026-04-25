import { NavLink } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import {
  LayoutDashboard, Users, Shield, FileText, Settings,
  LogOut, ChevronRight, Fingerprint, Bell, BarChart3,
  AlertTriangle, UserCheck, Building2, Key, Activity,
  ClipboardList, Search, Upload, CheckSquare, X
} from "lucide-react"
import { useAuthStore } from "../../store/authStore"
import Avatar from "../ui/Avatar"

const NAV_BY_ROLE = {
  ADMIN: [
    { to:"/dashboard",    icon:<LayoutDashboard size={16}/>, label:"Dashboard" },
    { to:"/institutions", icon:<Building2 size={16}/>,       label:"Institutions" },
    { to:"/users",        icon:<Users size={16}/>,           label:"Users" },
    { to:"/pep",          icon:<Shield size={16}/>,          label:"PEP List" },
    { to:"/audit",        icon:<FileText size={16}/>,        label:"Audit Log" },
    { to:"/system",       icon:<Activity size={16}/>,        label:"System Health" },
    { to:"/settings",     icon:<Settings size={16}/>,        label:"Settings" },
  ],
  AGENT: [
    { to:"/dashboard",    icon:<LayoutDashboard size={16}/>, label:"Dashboard" },
    { to:"/kyc/new",      icon:<Fingerprint size={16}/>,     label:"New eKYC" },
    { to:"/kyc/sessions", icon:<ClipboardList size={16}/>,   label:"My Sessions" },
  ],
  MAKER: [
    { to:"/dashboard",    icon:<LayoutDashboard size={16}/>, label:"Dashboard" },
    { to:"/kyc/new",      icon:<Upload size={16}/>,          label:"New Submission" },
    { to:"/kyc/queue",    icon:<ClipboardList size={16}/>,   label:"My Queue" },
  ],
  CHECKER: [
    { to:"/dashboard",    icon:<LayoutDashboard size={16}/>, label:"Dashboard" },
    { to:"/review",       icon:<CheckSquare size={16}/>,     label:"Review Queue" },
    { to:"/audit",        icon:<FileText size={16}/>,        label:"Audit Log" },
  ],
  COMPLIANCE_OFFICER: [
    { to:"/dashboard",    icon:<LayoutDashboard size={16}/>, label:"Dashboard" },
    { to:"/edd",          icon:<AlertTriangle size={16}/>,   label:"EDD Queue" },
    { to:"/screening",    icon:<Search size={16}/>,          label:"Screening" },
    { to:"/pep",          icon:<Shield size={16}/>,          label:"PEP Hits" },
    { to:"/audit",        icon:<FileText size={16}/>,        label:"Audit Log" },
  ],
  AUDITOR: [
    { to:"/dashboard",    icon:<LayoutDashboard size={16}/>, label:"Dashboard" },
    { to:"/audit",        icon:<FileText size={16}/>,        label:"Audit Log" },
    { to:"/reports",      icon:<BarChart3 size={16}/>,       label:"Reports" },
    { to:"/risk",         icon:<AlertTriangle size={16}/>,   label:"Risk Dashboard" },
  ],
}

export default function Sidebar({ open, onClose }) {
  const { user, role, logout } = useAuthStore()
  const navItems = NAV_BY_ROLE[role] || NAV_BY_ROLE.AGENT

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
            className="fixed inset-0 z-20 bg-black/40 lg:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ x: open ? 0 : "-100%" }}
        transition={{ type:"spring", damping:30, stiffness:300 }}
        className="fixed top-0 left-0 z-30 h-full w-64 bg-white dark:bg-gray-950
                   border-r border-gray-100 dark:border-gray-800 flex flex-col
                   lg:translate-x-0 lg:static lg:z-auto"
      >
        {/* Logo */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-brand-600 to-brand-800 rounded-xl flex items-center justify-center">
              <Fingerprint size={16} className="text-white"/>
            </div>
            <div>
              <p className="text-sm font-bold text-gray-900 dark:text-white leading-tight">Xpert eKYC</p>
              <p className="text-[10px] text-gray-400 leading-tight">BFIU Circular No. 29</p>
            </div>
          </div>
          <button onClick={onClose} className="lg:hidden p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            <X size={16} className="text-gray-500"/>
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-0.5">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest px-3 py-2">
            {role?.replace("_"," ")}
          </p>
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} onClick={onClose}
              className={({ isActive }) => isActive ? "sidebar-item-active block" : "sidebar-item block"}
            >
              <span className="flex items-center gap-3">
                {item.icon}
                <span>{item.label}</span>
                {item.badge && (
                  <span className="ml-auto badge-red text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-600">
                    {item.badge}
                  </span>
                )}
              </span>
            </NavLink>
          ))}
        </nav>

        {/* User + logout */}
        <div className="p-3 border-t border-gray-100 dark:border-gray-800 space-y-1">
          <div className="flex items-center gap-3 px-3 py-2">
            <Avatar name={user?.id || role || "U"} size="sm"/>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-gray-800 dark:text-gray-200 truncate">
                {user?.id || "Demo User"}
              </p>
              <p className="text-[10px] text-gray-400">{role}</p>
            </div>
          </div>
          <button onClick={logout}
            className="sidebar-item w-full text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 hover:text-red-600">
            <LogOut size={15}/> Sign Out
          </button>
        </div>
      </motion.aside>
    </>
  )
}
