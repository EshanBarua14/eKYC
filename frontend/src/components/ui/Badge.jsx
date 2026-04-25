const colors = {
  green:  "badge-green",
  red:    "badge-red",
  yellow: "badge-yellow",
  blue:   "badge-blue",
  gray:   "badge-gray",
  purple: "badge bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  orange: "badge bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
}

export default function Badge({ children, color = "gray", icon, className = "" }) {
  return (
    <span className={`${colors[color] || colors.gray} ${className}`}>
      {icon && <span className="mr-0.5">{icon}</span>}
      {children}
    </span>
  )
}
