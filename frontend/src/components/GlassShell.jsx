import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Building2,
  CheckSquare,
  ChevronRight,
  ClipboardList,
  Download,
  Eye,
  FileText,
  Fingerprint,
  Home,
  Lock,
  LogOut,
  Menu,
  Moon,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Shield,
  Sun,
  UserCheck,
  Users,
  X,
  Zap
} from "lucide-react"
/**
 * GlassShell — unified glassmorphism layout for all staff roles
 * Wraps: AdminConsole, ComplianceDashboard, AgentDashboard, MakerDashboard
 * BFIU Circular No. 29 — consistent UI for all roles
 */
import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"

// ── Nav config per role ──────────────────────────────────────────────────────
const ROLE_NAV = {
  ADMIN: {
    color: "#e8304f",
    label: "Administrator",
    emoji: "🔴",
    sections: [
      { label: "Overview", items: [
        { id:"dashboard",    icon: Home,          label: "Dashboard"       },
        { id:"health",       icon: Activity,      label: "System Health"   },
      ]},
      { label: "Management", items: [
        { id:"institutions", icon: Building2,     label: "Institutions"    },
        { id:"users",        icon: Users,         label: "Users"           },
        { id:"thresholds",   icon: Settings,      label: "Thresholds"      },
        { id:"webhooks",     icon: Zap,           label: "Webhooks"        },
      ]},
      { label: "Compliance", items: [
        { id:"pep",          icon: Shield,        label: "PEP List"        },
        { id:"auditlogs",    icon: FileText,      label: "Audit Logs"      },
        { id:"lifecycle",    icon: RefreshCw,     label: "KYC Lifecycle"   },
        { id:"screening_manual", icon: Search,    label: "Screening"       },
        { id:"notifications",icon: Bell,          label: "Notifications"   },
        { id:"settings",     icon: Settings,      label: "Settings"        },
      ]},
    ]
  },
  AGENT: {
    color: "#00b87a",
    label: "Field Agent",
    emoji: "🟢",
    sections: [
      { label: "eKYC", items: [
        { id:"dashboard",    icon: Home,          label: "Dashboard"       },
        { id:"new",          icon: Plus,          label: "New Session",   accent: true },
        { id:"sessions",     icon: ClipboardList, label: "My Sessions"    },
        { id:"search",       icon: Search,        label: "NID Search"     },
      ]},
      { label: "Tools", items: [
        { id:"screening",    icon: Search,        label: "Screening Check" },
        { id:"fallback",     icon: FileText,      label: "Fallback KYC"   },
        { id:"risk",         icon: BarChart3,     label: "Risk Calculator" },
      ]},
      { label: "Reports", items: [
        { id:"reports",      icon: FileText,      label: "My Reports"     },
        { id:"profile",      icon: UserCheck,     label: "My Profile"     },
      ]},
    ]
  },
  MAKER: {
    color: "#1a6edc",
    label: "Maker",
    emoji: "🔵",
    sections: [
      { label: "Submissions", items: [
        { id:"dashboard",    icon: Home,          label: "Dashboard"       },
        { id:"submit",       icon: Plus,          label: "New Submission", accent: true },
        { id:"queue",        icon: ClipboardList, label: "My Queue"        },
        { id:"approved",     icon: CheckSquare,   label: "Approved"        },
        { id:"rejected",     icon: X,             label: "Rejected"        },
      ]},
    ]
  },
  CHECKER: {
    color: "#e09500",
    label: "Checker",
    emoji: "🟡",
    sections: [
      { label: "Review", items: [
        { id:"posture",      icon: Home,          label: "Dashboard"       },
        { id:"queues",       icon: CheckSquare,   label: "Review Queue",   badge: "!" },
        { id:"edd",          icon: AlertTriangle, label: "EDD Cases"       },
        { id:"screening",    icon: Eye,           label: "Screening Hits"  },
      ]},
      { label: "Reports", items: [
        { id:"failed",       icon: X,             label: "Failed KYC"      },
        { id:"export",       icon: Download,      label: "BFIU Export"     },
      ]},
    ]
  },
  AUDITOR: {
    color: "#5b4fff",
    label: "Auditor",
    emoji: "🟣",
    sections: [
      { label: "Audit", items: [
        { id:"posture",      icon: Home,          label: "Dashboard"       },
        { id:"queues",       icon: ClipboardList, label: "KYC Queues"      },
        { id:"screening",    icon: Eye,           label: "Screening Hits"  },
        { id:"export",       icon: Download,      label: "BFIU Export"     },
      ]},
    ]
  },
  COMPLIANCE_OFFICER: {
    color: "#e8304f",
    label: "Compliance Officer",
    emoji: "🔴",
    sections: [
      { label: "Compliance", items: [
        { id:"posture",      icon: Home,          label: "Dashboard"       },
        { id:"edd",          icon: AlertTriangle, label: "EDD Cases",      badge: "!" },
        { id:"screening",    icon: Shield,        label: "Screening Hits"  },
        { id:"queues",       icon: ClipboardList, label: "KYC Queues"      },
      ]},
      { label: "Tools", items: [
        { id:"screening_manual", icon: Search,    label: "Manual Screening"},
        { id:"beneficial_owner", icon: Users,     label: "Beneficial Owner"},
        { id:"lifecycle",    icon: RefreshCw,     label: "KYC Lifecycle"   },
        { id:"notifications",icon: Bell,          label: "Notifications"   },
      ]},
      { label: "Reports", items: [
        { id:"export",       icon: Download,      label: "BFIU Export"     },
      ]},
    ]
  },
}

const PAGE_TITLES = {
  dashboard:"Dashboard", health:"System Health", institutions:"Institutions",
  users:"User Management", thresholds:"Risk Thresholds", webhooks:"Webhooks",
  pep:"PEP List Management", auditlogs:"Audit Logs", settings:"Settings",
  new:"New eKYC Session", sessions:"My Sessions", search:"NID Search",
  reports:"Reports", profile:"My Profile", submit:"New KYC Submission",
  queue:"My Queue", approved:"Approved", rejected:"Rejected",
  posture:"Compliance Posture", queues:"KYC Review Queue", edd:"EDD Cases",
  screening:"Screening Hits", failed:"Failed Onboarding", export:"BFIU Export",
}

const NOTIFICATIONS = [
  { msg:"UNSCR feed updated — 0 new hits",      time:"2 min ago",  type:"green"  },
  { msg:"EDD case pending review",               time:"15 min ago", type:"yellow" },
  { msg:"Monthly BFIU report ready",             time:"1 hour ago", type:"blue"   },
  { msg:"PEP list refreshed — 22 entries",       time:"2 hours ago",type:"accent" },
]

export default function GlassShell({ role, theme, toggleTheme, onExit, children, activeTab, setActiveTab }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notifOpen,   setNotifOpen]   = useState(false)
  const notifRef = useRef(null)
  const config = ROLE_NAV[role] || ROLE_NAV.AGENT

  // Close notif on outside click
  useEffect(() => {
    const handler = (e) => { if (notifRef.current && !notifRef.current.contains(e.target)) setNotifOpen(false) }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  const avatarColor = { ADMIN:"#e8304f", AGENT:"#00b87a", MAKER:"#1a6edc", CHECKER:"#e09500", AUDITOR:"#5b4fff", COMPLIANCE_OFFICER:"#e8304f" }[role] || "#5b4fff"
  const initials = role?.slice(0,2) || "U"

  const SidebarContent = () => (
    <>
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Fingerprint size={17} color="#fff" strokeWidth={2.5}/>
        </div>
        <div style={{ minWidth:0 }}>
          <div style={{ fontSize:13, fontWeight:800, color:"var(--text)", lineHeight:1.2 }}>Xpert eKYC</div>
          <div style={{ fontSize:9, color:"var(--text3)", fontWeight:600, letterSpacing:"0.05em" }}>BFIU CIRCULAR NO. 29</div>
        </div>
      </div>

      {/* Role badge */}
      <div style={{ padding:"10px 14px 6px" }}>
        <span className={`role-badge role-${role}`} style={{ width:"100%", justifyContent:"center" }}>
          {config.emoji} {config.label}
        </span>
      </div>

      {/* Nav */}
      <div className="sidebar-nav">
        {config.sections.map((section, si) => (
          <div key={si}>
            <div className="sidebar-section-label">{section.label}</div>
            {section.items.map(item => {
              const Icon = item.icon
              const isActive = activeTab === item.id
              return (
                <div
                  key={item.id}
                  onClick={() => { setActiveTab(item.id); setSidebarOpen(false) }}
                  className={`sidebar-item ${isActive ? "active" : ""} ${item.accent ? "accent-item" : ""}`}
                  style={ item.accent && !isActive ? {
                    background:"var(--accent-bg)",
                    color:"var(--accent)",
                    border:"1px solid var(--accent-bg2)",
                    fontWeight:700,
                  } : {}}
                >
                  <Icon size={14} strokeWidth={isActive ? 2.5 : 2}/>
                  <span className="truncate">{item.label}</span>
                  {item.badge && <span className="sidebar-badge">{item.badge}</span>}
                  {item.accent && !isActive && <Zap size={10} style={{ marginLeft:"auto", color:"var(--accent)" }}/>}
                </div>
              )
            })}
          </div>
        ))}
      </div>

      {/* User + logout */}
      <div className="sidebar-user">
        <div className="sidebar-user-card">
          <div className="sidebar-avatar" style={{ background: avatarColor }}>
            {initials}
          </div>
          <div style={{ minWidth:0, flex:1 }}>
            <div style={{ fontSize:11.5, fontWeight:700, color:"var(--text)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
              Demo {config.label}
            </div>
            <div style={{ fontSize:10, color:"var(--text3)" }}>inst-demo-001</div>
          </div>
          <Lock size={11} color="var(--text4)"/>
        </div>
        <div
          className="sidebar-item danger"
          onClick={onExit}
          style={{ width:"100%", justifyContent:"center", gap:6 }}
        >
          <LogOut size={13}/> Sign Out
        </div>
      </div>
    </>
  )

  return (
    <div className="staff-shell" data-theme={theme}>
      {/* Mobile overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
            style={{ position:"fixed", inset:0, zIndex:300, background:"rgba(7,9,15,0.5)", backdropFilter:"blur(4px)" }}
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Desktop sidebar */}
      <aside className="staff-sidebar" style={{ display:"flex" }}>
        <SidebarContent/>
      </aside>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ x:"-100%" }} animate={{ x:0 }} exit={{ x:"-100%" }}
            transition={{ type:"spring", damping:30, stiffness:300 }}
            className="staff-sidebar"
            style={{ position:"fixed", zIndex:400, display:"flex" }}
          >
            <button
              onClick={() => setSidebarOpen(false)}
              style={{ position:"absolute", top:14, right:14, background:"var(--bg4)", border:"none", borderRadius:8, width:28, height:28, display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer" }}
            >
              <X size={14} color="var(--text2)"/>
            </button>
            <SidebarContent/>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main */}
      <div className="staff-main">
        {/* Topbar */}
        <div className="staff-topbar">
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <button
              onClick={() => setSidebarOpen(true)}
              style={{ display:"none", background:"var(--bg3)", border:"1px solid var(--border)", borderRadius:8, width:34, height:34, alignItems:"center", justifyContent:"center", cursor:"pointer" }}
              className="mobile-menu-btn"
            >
              <Menu size={16} color="var(--text2)"/>
            </button>
            <div>
              <div style={{ fontSize:14, fontWeight:800, color:"var(--text)" }}>
                {PAGE_TITLES[activeTab] || "Dashboard"}
              </div>
              <div style={{ fontSize:10, color:"var(--text3)", fontWeight:600 }}>
                BFIU Circular No. 29 · {config.label}
              </div>
            </div>
          </div>

          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            {/* Live */}
            <div className="api-live">
              <div className="api-live-dot"/>
              <span className="api-live-text">Live</span>
            </div>

            {/* Notifications */}
            <div style={{ position:"relative" }} ref={notifRef}>
              <button
                onClick={() => setNotifOpen(!notifOpen)}
                style={{ width:34, height:34, borderRadius:9, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", position:"relative" }}
              >
                <Bell size={15} color="var(--text2)"/>
                <span style={{ position:"absolute", top:7, right:7, width:6, height:6, borderRadius:"50%", background:"var(--red)", border:"2px solid var(--bg3)" }}/>
              </button>
              <AnimatePresence>
                {notifOpen && (
                  <motion.div
                    initial={{ opacity:0, y:-8, scale:0.95 }}
                    animate={{ opacity:1, y:0, scale:1 }}
                    exit={{ opacity:0, y:-8, scale:0.95 }}
                    className="notif-dropdown"
                  >
                    <div style={{ padding:"12px 14px", borderBottom:"1px solid var(--border)", fontSize:12, fontWeight:800, color:"var(--text)", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                      Notifications
                      <span className="badge badge-red" style={{ fontSize:10 }}>4 new</span>
                    </div>
                    {NOTIFICATIONS.map((n,i) => (
                      <div key={i} className="notif-item">
                        <div className="notif-dot" style={{ background:`var(--${n.type === "accent" ? "accent" : n.type})` }}/>
                        <div>
                          <div style={{ fontSize:11.5, color:"var(--text)", fontWeight:500 }}>{n.msg}</div>
                          <div style={{ fontSize:10, color:"var(--text3)", marginTop:2 }}>{n.time}</div>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Theme */}
            <button
              onClick={toggleTheme}
              style={{ width:34, height:34, borderRadius:9, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer" }}
            >
              {theme === "light"
                ? <Moon size={15} color="var(--text2)"/>
                : <Sun  size={15} color="#ffb800"/>}
            </button>

            {/* Role pill */}
            <span className={`role-badge role-${role}`}>{config.emoji} {role?.replace("_"," ")}</span>
          </div>
        </div>

        {/* Content */}
        <div className="staff-content">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity:0, y:8 }}
              animate={{ opacity:1, y:0 }}
              exit={{ opacity:0, y:-8 }}
              transition={{ duration:0.18 }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer */}
        <footer className="app-footer">
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <div style={{ width:18, height:18, borderRadius:5, background:"linear-gradient(135deg,var(--accent),var(--blue))", display:"flex", alignItems:"center", justifyContent:"center" }}>
              <Fingerprint size={10} color="#fff" strokeWidth={2.5}/>
            </div>
            <span>Design &amp; Developed by <span className="footer-brand">Xpert Fintech Ltd.</span></span>
          </div>
          <span>BFIU Circular No. 29 Compliant · AES-256 · BST</span>
          <span>© {new Date().getFullYear()} All rights reserved</span>
        </footer>
      </div>

      <style>{`
        @media (max-width: 768px) {
          .staff-sidebar { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
      `}</style>
    </div>
  )
}
