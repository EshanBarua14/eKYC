import { forwardRef } from "react"

const Input = forwardRef(function Input({
  label, error, hint, icon, iconRight,
  className = "", containerClass = "", ...props
}, ref) {
  return (
    <div className={`space-y-1.5 ${containerClass}`}>
      {label && <label className="label">{label}</label>}
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          className={`input ${icon ? "pl-10" : ""} ${iconRight ? "pr-10" : ""} ${error ? "border-red-400 focus:ring-red-400" : ""} ${className}`}
          {...props}
        />
        {iconRight && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
            {iconRight}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {hint && !error && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  )
})
export default Input
