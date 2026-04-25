import { Check } from "lucide-react"
export default function StepBar({ steps, current }) {
  return (
    <div className="flex items-start gap-0 w-full">
      {steps.map((s, i) => {
        const done = current > i + 1
        const active = current === i + 1
        return (
          <div key={i} className="flex items-start" style={{ flex: i < steps.length - 1 ? 1 : "none" }}>
            <div className="flex flex-col items-center gap-1.5 min-w-[60px]">
              <div className={`step-dot ${done ? "step-dot-done" : active ? "step-dot-active" : "step-dot-pending"}`}>
                {done ? <Check size={12} strokeWidth={3}/> : <span className="text-xs">{i+1}</span>}
              </div>
              <span className={`text-center text-[10px] font-medium leading-tight ${active ? "text-brand-600 dark:text-brand-400" : done ? "text-emerald-600" : "text-gray-400"}`}>
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="flex-1 mt-4 mx-1">
                <div className={`h-0.5 w-full transition-all duration-500 ${done ? "bg-emerald-400" : active ? "bg-brand-300" : "bg-gray-200 dark:bg-gray-700"}`}/>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
