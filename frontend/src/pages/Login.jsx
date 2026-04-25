import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { Fingerprint, Eye, EyeOff, Lock, Mail, Shield, Sun, Moon, ChevronRight } from "lucide-react"
import { useAuthStore } from "../store/authStore"
import { api } from "../hooks/useApi"
import { notify } from "../components/ui/Toast"
import Button from "../components/ui/Button"
import Input from "../components/ui/Input"
import { Toaster } from "react-hot-toast"

const ROLES = [
  { key:"ADMIN",              label:"Admin",              color:"bg-red-500",    desc:"Full system access" },
  { key:"MAKER",              label:"Maker",              color:"bg-blue-500",   desc:"Submit KYC" },
  { key:"CHECKER",            label:"Checker",            color:"bg-amber-500",  desc:"Review & approve" },
  { key:"AGENT",              label:"Field Agent",        color:"bg-emerald-500",desc:"Face verification" },
  { key:"AUDITOR",            label:"Auditor",            color:"bg-purple-500", desc:"Read-only access" },
  { key:"COMPLIANCE_OFFICER", label:"Compliance Officer", color:"bg-rose-500",   desc:"EDD & PEP" },
]

const DEMO = {
  ADMIN:              { email:"admin-bypass@demo.ekyc",      password:"AdminDemo@2026" },
  MAKER:              { email:"maker-bypass@demo.ekyc",      password:"DemoMaker@2026" },
  CHECKER:            { email:"checker-bypass@demo.ekyc",    password:"DemoChecker@2026" },
  AGENT:              { email:"agent-bypass@demo.ekyc",      password:"DemoAgent@2026" },
  AUDITOR:            { email:"auditor-bypass@demo.ekyc",    password:"DemoAudit@2026" },
  COMPLIANCE_OFFICER: { email:"co-bypass@demo.ekyc",         password:"DemoCO@2026" },
}

export default function Login() {
  const navigate = useNavigate()
  const { login, theme, toggleTheme } = useAuthStore()
  const [selectedRole, setSelectedRole] = useState(null)
  const [email, setEmail]       = useState("")
  const [password, setPassword] = useState("")
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState("")

  const fillDemo = (role) => {
    setSelectedRole(role)
    setEmail(DEMO[role]?.email || "")
    setPassword(DEMO[role]?.password || "")
    setError("")
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError("")
    try {
      // Register (ignore 409)
      try { await api.post("/api/v1/auth/register", {
        email, password, phone:"01700000001",
        full_name: selectedRole || "Demo User",
        role: (selectedRole||"AGENT").toLowerCase(),
        institution_id: "inst-demo-001"
      }) } catch(_) {}

      // Login
      const res = await api.post("/api/v1/auth/token", { email, password })
      const token = res.data?.access_token || res.data?.token || ""
      if (!token) throw new Error("No token returned")

      login(token)
      notify.success(`Welcome back — ${selectedRole || "User"}`)
      navigate("/dashboard")
    } catch(err) {
      const msg = err.response?.data?.detail || "Login failed — check credentials"
      setError(msg)
      notify.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-950 via-brand-900 to-gray-950 flex flex-col">
      <Toaster position="top-right"/>

      {/* Header */}
      <div className="flex items-center justify-between p-4 md:p-6">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-white/10 rounded-xl flex items-center justify-center backdrop-blur">
            <Fingerprint size={18} className="text-white"/>
          </div>
          <div>
            <p className="text-sm font-bold text-white">Xpert eKYC</p>
            <p className="text-[10px] text-white/50">BFIU Circular No. 29</p>
          </div>
        </div>
        <button onClick={toggleTheme} className="p-2 hover:bg-white/10 rounded-xl transition-colors">
          {theme === "light" ? <Moon size={16} className="text-white/70"/> : <Sun size={16} className="text-amber-400"/>}
        </button>
      </div>

      {/* Main */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-4xl grid lg:grid-cols-2 gap-6 items-center">

          {/* Left — branding */}
          <motion.div
            initial={{ opacity:0, x:-20 }}
            animate={{ opacity:1, x:0 }}
            transition={{ duration:0.4 }}
            className="hidden lg:block text-white space-y-6"
          >
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 rounded-full text-xs font-medium mb-4">
                <Shield size={11}/> Bangladesh Financial Intelligence Unit
              </div>
              <h1 className="text-4xl font-bold leading-tight">
                Digital eKYC<br/>
                <span className="text-brand-300">Onboarding Platform</span>
              </h1>
              <p className="text-white/60 mt-3 text-sm leading-relaxed">
                Fully compliant with BFIU Circular No. 29. Secure NID verification,
                face matching, risk grading, and EDD workflow for Bangladesh financial institutions.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label:"BFIU §3.2", desc:"Face verification" },
                { label:"BFIU §4.2", desc:"PEP/EDD workflow" },
                { label:"BFIU §5.2", desc:"Data isolation" },
                { label:"Annexure-2", desc:"Composite score" },
              ].map(f => (
                <div key={f.label} className="bg-white/5 rounded-xl p-3 border border-white/10">
                  <p className="text-xs font-semibold text-brand-300">{f.label}</p>
                  <p className="text-[11px] text-white/50 mt-0.5">{f.desc}</p>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-white/30">
              Design &amp; Developed by Xpert Fintech Ltd.
            </p>
          </motion.div>

          {/* Right — login form */}
          <motion.div
            initial={{ opacity:0, y:20 }}
            animate={{ opacity:1, y:0 }}
            transition={{ duration:0.4, delay:0.1 }}
            className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-6 space-y-5"
          >
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Staff Login</h2>
              <p className="text-xs text-gray-400 mt-0.5">Select your role and sign in</p>
            </div>

            {/* Role picker */}
            <div>
              <label className="label">Select Role</label>
              <div className="grid grid-cols-3 gap-1.5">
                {ROLES.map(r => (
                  <button key={r.key} type="button"
                    onClick={() => fillDemo(r.key)}
                    className={`p-2.5 rounded-xl border text-left transition-all duration-150 ${
                      selectedRole === r.key
                        ? "border-brand-500 bg-brand-50 dark:bg-brand-950/30"
                        : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                    }`}
                  >
                    <div className={`w-4 h-4 ${r.color} rounded-full mb-1`}/>
                    <p className="text-[11px] font-semibold text-gray-800 dark:text-gray-200 leading-tight">{r.label}</p>
                    <p className="text-[10px] text-gray-400 leading-tight">{r.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <Input label="Email" type="email" value={email}
                onChange={e=>setEmail(e.target.value)} required
                icon={<Mail size={14}/>} placeholder="email@institution.com"/>
              <Input label="Password" type={showPass?"text":"password"}
                value={password} onChange={e=>setPassword(e.target.value)} required
                icon={<Lock size={14}/>}
                iconRight={
                  <button type="button" onClick={()=>setShowPass(!showPass)}>
                    {showPass ? <EyeOff size={14}/> : <Eye size={14}/>}
                  </button>
                }
                placeholder="••••••••"/>

              {error && (
                <p className="text-xs text-red-500 bg-red-50 dark:bg-red-950/20 rounded-lg px-3 py-2">{error}</p>
              )}

              <Button type="submit" className="w-full" loading={loading}
                icon={<Shield size={14}/>} iconRight={<ChevronRight size={14}/>}>
                Sign In Securely
              </Button>
            </form>

            <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
              <p className="text-[10px] text-center text-gray-400">
                BFIU Circular No. 29 · AES-256 Encrypted · BST Timestamps
              </p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 text-center">
        <p className="text-[11px] text-white/30">
          Design &amp; Developed by <span className="text-white/50 font-medium">Xpert Fintech Ltd.</span>
          {" "}· BFIU Circular No. 29 Compliant · © {new Date().getFullYear()}
        </p>
      </div>
    </div>
  )
}
