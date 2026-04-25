import { motion } from "framer-motion"

export default function Card({ children, className = "", hover = false, glow = false, onClick, ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      whileHover={hover ? { y: -2, boxShadow: "0 8px 30px rgba(0,0,0,0.12)" } : undefined}
      onClick={onClick}
      className={`card ${hover ? "cursor-pointer" : ""} ${glow ? "shadow-glow-blue" : ""} ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  )
}
