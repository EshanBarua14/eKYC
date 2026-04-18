
/* Ultra-modern UI components — M23 Design Refresh */

export function Card({ children, style = {}, glow = false, glass = false, hover = false }) {
  return (
    <div
      style={{
        background: glass ? "var(--bg-glass)" : "var(--bg2)",
        backdropFilter: glass ? "blur(20px) saturate(180%)" : undefined,
        WebkitBackdropFilter: glass ? "blur(20px) saturate(180%)" : undefined,
        border: `1px solid ${glass ? "var(--border-glass)" : "var(--border)"}`,
        borderRadius: "var(--radius)",
        padding: "22px 24px",
        boxShadow: glow
          ? "var(--shadow), var(--shadow-accent)"
          : "var(--shadow-sm)",
        animation: "fadeUp 0.25s cubic-bezier(0.34,1.56,0.64,1) both",
        transition: "box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease",
        position: "relative",
        overflow: "hidden",
        ...style,
      }}
      onMouseEnter={hover ? e => {
        e.currentTarget.style.boxShadow = "var(--shadow), 0 0 0 1px var(--border-h)"
        e.currentTarget.style.transform = "translateY(-1px)"
      } : undefined}
      onMouseLeave={hover ? e => {
        e.currentTarget.style.boxShadow = "var(--shadow-sm)"
        e.currentTarget.style.transform = ""
      } : undefined}
    >
      {glow && (
        <div style={{
          position:"absolute", top:0, left:0, right:0, height:1,
          background:"linear-gradient(90deg,transparent,var(--accent),transparent)",
          opacity:0.6,
        }}/>
      )}
      {children}
    </div>
  )
}

export function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 13, fontWeight: 800, color: "var(--text)",
        letterSpacing: "-0.015em", lineHeight: 1.3,
      }}>{children}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 3, fontWeight: 500 }}>{sub}</div>}
    </div>
  )
}

export function Btn({ children, onClick, variant = "primary", disabled, loading, style = {}, size = "md" }) {
  const sizes = {
    sm: { padding: "7px 13px", fontSize: 12, gap: 5, radius: "var(--radius-sm)" },
    md: { padding: "10px 20px", fontSize: 13, gap: 7, radius: "var(--radius-sm)" },
    lg: { padding: "13px 28px", fontSize: 14, gap: 8, radius: "var(--radius-sm)" },
  }
  const s = sizes[size] || sizes.md

  const variants = {
    primary: {
      background: "linear-gradient(135deg, var(--accent) 0%, var(--blue) 100%)",
      color: "#fff",
      border: "1px solid transparent",
      boxShadow: "var(--shadow-accent), inset 0 1px 0 rgba(255,255,255,0.15)",
    },
    ghost: {
      background: "var(--bg3)",
      color: "var(--text2)",
      border: "1px solid var(--border)",
      boxShadow: "var(--shadow-xs)",
    },
    success: {
      background: "linear-gradient(135deg, var(--green) 0%, var(--blue) 100%)",
      color: "#fff",
      border: "1px solid transparent",
      boxShadow: "var(--shadow-green), inset 0 1px 0 rgba(255,255,255,0.15)",
    },
    danger: {
      background: "var(--red-bg)",
      color: "var(--red)",
      border: "1px solid var(--red-border)",
    },
    outline: {
      background: "transparent",
      color: "var(--accent)",
      border: "1px solid var(--accent)",
    },
    glass: {
      background: "var(--bg-glass)",
      backdropFilter: "blur(12px)",
      color: "var(--text)",
      border: "1px solid var(--border-glass)",
    },
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: s.gap,
        padding: s.padding,
        borderRadius: s.radius,
        fontSize: s.fontSize,
        fontWeight: 700,
        fontFamily: "var(--font)",
        cursor: disabled || loading ? "not-allowed" : "pointer",
        transition: "all 0.15s cubic-bezier(0.4,0,0.2,1)",
        opacity: disabled || loading ? 0.5 : 1,
        lineHeight: 1,
        position: "relative",
        overflow: "hidden",
        letterSpacing: "-0.01em",
        ...variants[variant],
        ...style,
      }}
      onMouseEnter={e => {
        if (!disabled && !loading) {
          e.currentTarget.style.filter = "brightness(1.1)"
          e.currentTarget.style.transform = "translateY(-1px)"
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.filter = ""
        e.currentTarget.style.transform = ""
      }}
      onMouseDown={e => {
        if (!disabled && !loading) e.currentTarget.style.transform = "scale(0.97)"
      }}
      onMouseUp={e => { e.currentTarget.style.transform = "" }}
    >
      {loading && (
        <span style={{
          width: 12, height: 12,
          border: "2px solid currentColor",
          borderTopColor: "transparent",
          borderRadius: "50%",
          animation: "spin 0.7s linear infinite",
          display: "inline-block",
          flexShrink: 0,
        }}/>
      )}
      {children}
    </button>
  )
}

export function Badge({ children, color = "accent" }) {
  const map = {
    accent:  { bg:"var(--accent-bg2)", color:"var(--accent)",  border:"rgba(91,79,255,0.3)",   glow:"rgba(91,79,255,0.15)"  },
    green:   { bg:"var(--green-bg)",   color:"var(--green)",   border:"var(--green-border)",    glow:"rgba(0,184,122,0.1)"   },
    red:     { bg:"var(--red-bg)",     color:"var(--red)",     border:"var(--red-border)",      glow:"rgba(232,48,79,0.1)"   },
    yellow:  { bg:"var(--yellow-bg)",  color:"var(--yellow)",  border:"var(--yellow-border)",   glow:"rgba(224,149,0,0.1)"   },
    blue:    { bg:"var(--blue-bg)",    color:"var(--blue)",    border:"var(--blue-border)",     glow:"rgba(26,110,220,0.1)"  },
    purple:  { bg:"var(--purple-bg)",  color:"var(--purple)",  border:"rgba(147,51,234,0.3)",   glow:"rgba(147,51,234,0.1)"  },
  }
  const c = map[color] || map.accent
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "3px 9px",
      borderRadius: "var(--radius-full)",
      background: c.bg, color: c.color,
      border: `1px solid ${c.border}`,
      letterSpacing: "0.02em",
      display: "inline-flex", alignItems: "center", gap: 4,
      lineHeight: 1.5,
      boxShadow: `0 2px 8px ${c.glow}`,
      transition: "all 0.15s ease",
    }}>{children}</span>
  )
}

export function ScoreBar({ label, value, color }) {
  const v = typeof value === "number" ? value : 0
  const c = color || (v >= 55 ? "var(--green)" : v >= 35 ? "var(--yellow)" : "var(--red)")
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:6 }}>
        <span style={{ fontSize:12, color:"var(--text2)", fontWeight:500 }}>{label}</span>
        <span style={{ fontSize:12, color:c, fontWeight:800, fontFamily:"var(--font-mono)" }}>{v}%</span>
      </div>
      <div style={{
        background:"var(--bg4)", borderRadius:99, height:5, overflow:"hidden",
        boxShadow:"inset 0 1px 3px rgba(0,0,0,0.1)",
      }}>
        <div style={{
          width:`${Math.min(100,v)}%`, height:"100%", borderRadius:99,
          background:c,
          boxShadow:`0 0 8px ${c}88`,
          transition:"width 1.4s cubic-bezier(0.34,1.2,0.64,1)",
        }}/>
      </div>
    </div>
  )
}

export function Spinner({ size = 22, color = "var(--accent)" }) {
  return (
    <div style={{
      width:size, height:size,
      border:`2px solid ${color}22`,
      borderTopColor:color,
      borderRadius:"50%",
      animation:"spin 0.75s linear infinite",
      flexShrink:0,
      boxShadow:`0 0 12px ${color}44`,
    }}/>
  )
}

export function CheckItem({ label, pass, value }) {
  return (
    <div style={{
      display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"9px 13px", borderRadius:"var(--radius-sm)", marginBottom:5,
      background: pass ? "var(--green-bg)" : "var(--red-bg)",
      border:`1px solid ${pass ? "var(--green-border)" : "var(--red-border)"}`,
      transition:"all 0.15s ease",
    }}>
      <div style={{ display:"flex", alignItems:"center", gap:9 }}>
        <div style={{
          width:18, height:18, borderRadius:"50%",
          background: pass
            ? "linear-gradient(135deg, var(--green), var(--green-h))"
            : "linear-gradient(135deg, var(--red), var(--red-h))",
          display:"flex", alignItems:"center", justifyContent:"center",
          flexShrink:0, boxShadow: pass ? "var(--shadow-green)" : "var(--shadow-red)",
        }}>
          <span style={{ fontSize:9, color:"#fff", fontWeight:900 }}>{pass ? "✓" : "✗"}</span>
        </div>
        <span style={{ fontSize:12, fontWeight:600, color:"var(--text)" }}>{label}</span>
      </div>
      <span style={{ fontSize:11, color:"var(--text3)", fontFamily:"var(--font-mono)", fontWeight:500 }}>{value}</span>
    </div>
  )
}

export function Divider({ label }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:12, margin:"18px 0" }}>
      <div style={{ flex:1, height:"1px", background:"var(--border)" }}/>
      {label && (
        <span style={{
          fontSize:10, color:"var(--text3)", fontWeight:700,
          letterSpacing:"0.08em", whiteSpace:"nowrap", textTransform:"uppercase",
          padding:"2px 8px", borderRadius:"var(--radius-full)",
          background:"var(--bg3)", border:"1px solid var(--border)",
        }}>{label}</span>
      )}
      <div style={{ flex:1, height:"1px", background:"var(--border)" }}/>
    </div>
  )
}

export function StatGrid({ items }) {
  return (
    <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(100px,1fr))", gap:8 }}>
      {items.map(([label, value, color]) => (
        <div key={label} style={{
          padding:"11px 13px",
          background:"var(--bg3)",
          borderRadius:"var(--radius-sm)",
          border:"1px solid var(--border)",
          transition:"all 0.15s ease",
          position:"relative",
          overflow:"hidden",
        }}>
          <div style={{
            position:"absolute", top:0, left:0, right:0, height:2,
            background: color || "var(--accent)",
            opacity:0.6,
            borderRadius:"var(--radius-sm) var(--radius-sm) 0 0",
          }}/>
          <div style={{ fontSize:9, color:"var(--text3)", fontWeight:700, marginBottom:5, textTransform:"uppercase", letterSpacing:"0.07em" }}>{label}</div>
          <div style={{ fontSize:15, fontWeight:800, color: color || "var(--text)", fontFamily:"var(--font-mono)", letterSpacing:"-0.02em" }}>{value}</div>
        </div>
      ))}
    </div>
  )
}
