import { motion } from "framer-motion"
import { Loader2 } from "lucide-react"

export default function Button({
  children, variant = "primary", size = "md",
  loading = false, disabled = false,
  icon, iconRight, className = "", onClick, type = "button", ...props
}) {
  const base = "inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-all duration-200 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed select-none"
  const variants = {
    primary:   "bg-brand-600 hover:bg-brand-700 text-white shadow-sm hover:shadow-glow-blue",
    secondary: "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-brand-300 text-gray-700 dark:text-gray-200 shadow-sm",
    danger:    "bg-red-600 hover:bg-red-700 text-white",
    success:   "bg-emerald-600 hover:bg-emerald-700 text-white",
    ghost:     "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400",
    outline:   "border border-brand-600 text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-950/30",
    gold:      "bg-amber-500 hover:bg-amber-600 text-white",
  }
  const sizes = {
    xs: "px-2.5 py-1.5 text-xs",
    sm: "px-3 py-2 text-xs",
    md: "px-4 py-2.5 text-sm",
    lg: "px-5 py-3 text-base",
    xl: "px-6 py-3.5 text-base",
  }
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : icon}
      {children}
      {!loading && iconRight}
    </motion.button>
  )
}
