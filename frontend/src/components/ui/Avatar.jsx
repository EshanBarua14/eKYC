const COLORS = [
  "bg-blue-500","bg-emerald-500","bg-purple-500","bg-amber-500",
  "bg-red-500","bg-pink-500","bg-indigo-500","bg-teal-500"
]
export default function Avatar({ name = "", size = "md", src, className = "" }) {
  const sizes = { xs:"w-6 h-6 text-xs", sm:"w-8 h-8 text-xs", md:"w-10 h-10 text-sm", lg:"w-12 h-12 text-base", xl:"w-16 h-16 text-xl" }
  const color = COLORS[(name.charCodeAt(0) || 0) % COLORS.length]
  const initials = name.split(" ").map(w=>w[0]).join("").toUpperCase().slice(0,2)
  return src
    ? <img src={src} alt={name} className={`${sizes[size]} rounded-full object-cover ${className}`} />
    : <div className={`${sizes[size]} ${color} rounded-full flex items-center justify-center text-white font-semibold ${className}`}>{initials}</div>
}
