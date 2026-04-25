import toast from "react-hot-toast"
import { CheckCircle, XCircle, AlertTriangle, Info } from "lucide-react"

export const notify = {
  success: (msg, opts={}) => toast.custom(
    <div className="flex items-center gap-3 bg-white dark:bg-gray-900 border border-emerald-200 dark:border-emerald-800 rounded-xl px-4 py-3 shadow-lg">
      <CheckCircle size={18} className="text-emerald-500 shrink-0"/>
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{msg}</p>
    </div>, { duration: 3000, ...opts }
  ),
  error: (msg, opts={}) => toast.custom(
    <div className="flex items-center gap-3 bg-white dark:bg-gray-900 border border-red-200 dark:border-red-800 rounded-xl px-4 py-3 shadow-lg">
      <XCircle size={18} className="text-red-500 shrink-0"/>
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{msg}</p>
    </div>, { duration: 4000, ...opts }
  ),
  warning: (msg, opts={}) => toast.custom(
    <div className="flex items-center gap-3 bg-white dark:bg-gray-900 border border-amber-200 dark:border-amber-800 rounded-xl px-4 py-3 shadow-lg">
      <AlertTriangle size={18} className="text-amber-500 shrink-0"/>
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{msg}</p>
    </div>, { duration: 4000, ...opts }
  ),
  info: (msg, opts={}) => toast.custom(
    <div className="flex items-center gap-3 bg-white dark:bg-gray-900 border border-blue-200 dark:border-blue-800 rounded-xl px-4 py-3 shadow-lg">
      <Info size={18} className="text-blue-500 shrink-0"/>
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{msg}</p>
    </div>, { duration: 3000, ...opts }
  ),
  bfiu: (msg) => toast.custom(
    <div className="flex items-center gap-3 bg-brand-600 rounded-xl px-4 py-3 shadow-lg">
      <CheckCircle size={18} className="text-white shrink-0"/>
      <p className="text-sm font-medium text-white">{msg}</p>
    </div>, { duration: 4000 }
  ),
}
export default notify
