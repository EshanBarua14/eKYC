import { motion } from "framer-motion"

export default function StatCard({ title, value, icon, color = "blue", trend, subtitle, className="" }) {
  const colors = {
    blue:   "bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400",
    green:  "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400",
    red:    "bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400",
    amber:  "bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400",
    purple: "bg-purple-50 dark:bg-purple-950/30 text-purple-600 dark:text-purple-400",
  }
  return (
    <motion.div
      initial={{ opacity:0, y:8 }}
      animate={{ opacity:1, y:0 }}
      className={`card flex items-start gap-4 ${className}`}
    >
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${colors[color]} shrink-0`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide truncate">{title}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white mt-0.5">{value}</p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        {trend && <p className={`text-xs mt-0.5 font-medium ${trend > 0 ? "text-emerald-500" : "text-red-500"}`}>{trend > 0 ? "↑" : "↓"} {Math.abs(trend)}%</p>}
      </div>
    </motion.div>
  )
}
