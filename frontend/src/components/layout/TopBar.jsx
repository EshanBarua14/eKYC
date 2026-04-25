import { Menu, Sun, Moon, Bell, RefreshCw } from "lucide-react"
import { useAuthStore } from "../../store/authStore"
import Avatar from "../ui/Avatar"
import { useState } from "react"

export default function TopBar({ onMenuClick, title = "" }) {
  const { theme, toggleTheme, role, user } = useAuthStore()
  const [notifOpen, setNotifOpen] = useState(false)

  return (
    <header className="h-14 bg-white dark:bg-gray-950 border-b border-gray-100 dark:border-gray-800
                       flex items-center justify-between px-4 gap-4 sticky top-0 z-10">
      <div className="flex items-center gap-3">
        <button onClick={onMenuClick}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl lg:hidden transition-colors">
          <Menu size={18} className="text-gray-600 dark:text-gray-400"/>
        </button>
        <div>
          <h1 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{title}</h1>
          <p className="text-[10px] text-gray-400 hidden sm:block">BFIU Circular No. 29 Compliant</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Live indicator */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 dark:bg-emerald-950/30
                        rounded-full border border-emerald-100 dark:border-emerald-900">
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse-dot"/>
          <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">Live</span>
        </div>

        {/* Theme toggle */}
        <button onClick={toggleTheme}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
          {theme === "light"
            ? <Moon size={16} className="text-gray-500"/>
            : <Sun  size={16} className="text-amber-400"/>}
        </button>

        {/* Notifications */}
        <button onClick={() => setNotifOpen(!notifOpen)}
          className="relative p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
          <Bell size={16} className="text-gray-500"/>
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full"/>
        </button>

        <Avatar name={user?.id || role || "U"} size="sm"/>
      </div>
    </header>
  )
}
