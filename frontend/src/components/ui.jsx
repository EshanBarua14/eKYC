export function Card({ children, style = {}, glow = false }) {
  return (
    <div style={{
      background: "var(--bg2)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius)",
      padding: "22px 24px",
      boxShadow: glow ? "var(--shadow), var(--shadow-accent)" : "var(--shadow)",
      animation: "fadeUp 0.3s ease both",
      ...style,
    }}>{children}</div>
  )
}

export function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", letterSpacing: "-0.01em" }}>{children}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

export function Btn({ children, onClick, variant = "primary", disabled, loading, style = {}, size = "md" }) {
  const sizes = {
    sm: { padding: "7px 14px", fontSize: 12, gap: 5 },
    md: { padding: "10px 20px", fontSize: 13, gap: 7 },
    lg: { padding: "13px 28px", fontSize: 14, gap: 8 },
  }
  const s = sizes[size] || sizes.md
  const variants = {
    primary: {
      background: "var(--accent)", color: "#fff",
      border: "1px solid transparent",
      boxShadow: "0 2px 8px rgba(99,88,255,0.3), inset 0 1px 0 rgba(255,255,255,0.15)",
    },
    ghost: {
      background: "var(--bg3)", color: "var(--text2)",
      border: "1px solid var(--border)",
    },
    success: {
      background: "var(--green)", color: "#fff",
      border: "1px solid transparent",
      boxShadow: "0 2px 8px rgba(0,184,122,0.3)",
    },
    danger: {
      background: "var(--red-bg)", color: "var(--red)",
      border: "1px solid var(--red-border)",
    },
    outline: {
      background: "transparent", color: "var(--accent)",
      border: "1px solid var(--accent)",
    },
  }
  return (
    <button onClick={onClick} disabled={disabled || loading} style={{
      display: "inline-flex", alignItems: "center", gap: s.gap,
      padding: s.padding, borderRadius: "var(--radius-sm)",
      fontSize: s.fontSize, fontWeight: 600, fontFamily: "var(--font)",
      cursor: disabled || loading ? "not-allowed" : "pointer",
      transition: "all 0.15s ease",
      opacity: disabled || loading ? 0.5 : 1,
      lineHeight: 1,
      ...variants[variant], ...style,
    }}
    onMouseEnter={e => { if (!disabled && !loading) e.currentTarget.style.filter = "brightness(1.08)" }}
    onMouseLeave={e => { e.currentTarget.style.filter = "" }}
    onMouseDown={e => { if (!disabled && !loading) e.currentTarget.style.transform = "scale(0.98)" }}
    onMouseUp={e => { e.currentTarget.style.transform = "" }}
    >
      {loading && <span style={{ width:12, height:12, border:"2px solid currentColor", borderTopColor:"transparent", borderRadius:"50%", animation:"spin 0.7s linear infinite", display:"inline-block", flexShrink:0 }} />}
      {children}
    </button>
  )
}

export function Badge({ children, color = "accent" }) {
  const map = {
    accent:  { bg: "var(--accent-bg)",   color: "var(--accent)",  border: "rgba(99,88,255,0.2)"  },
    green:   { bg: "var(--green-bg)",    color: "var(--green)",   border: "var(--green-border)"  },
    red:     { bg: "var(--red-bg)",      color: "var(--red)",     border: "var(--red-border)"    },
    yellow:  { bg: "var(--yellow-bg)",   color: "var(--yellow)",  border: "var(--yellow-border)" },
    blue:    { bg: "var(--blue-bg)",     color: "var(--blue)",    border: "rgba(45,126,240,0.2)" },
  }
  const c = map[color] || map.accent
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "3px 9px",
      borderRadius: 99, background: c.bg, color: c.color,
      border: `1px solid ${c.border}`, letterSpacing: "0.03em",
      display: "inline-flex", alignItems: "center", gap: 4,
      lineHeight: 1.4,
    }}>{children}</span>
  )
}

export function ScoreBar({ label, value, color }) {
  const v = typeof value === "number" ? value : 0
  const c = color || (v >= 55 ? "var(--green)" : v >= 35 ? "var(--yellow)" : "var(--red)")
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:5 }}>
        <span style={{ fontSize:12, color:"var(--text2)", fontWeight:500 }}>{label}</span>
        <span style={{ fontSize:12, color:c, fontWeight:700, fontFamily:"var(--font-mono)" }}>{v}%</span>
      </div>
      <div style={{ background:"var(--bg4)", borderRadius:99, height:4, overflow:"hidden" }}>
        <div style={{
          width:`${Math.min(100,v)}%`, height:"100%", borderRadius:99,
          background:c, transition:"width 1.2s cubic-bezier(.4,0,.2,1)",
          opacity: 0.9,
        }} />
      </div>
    </div>
  )
}

export function Spinner({ size = 22, color = "var(--accent)" }) {
  return (
    <div style={{ width:size, height:size, border:`2px solid ${color}22`, borderTopColor:color, borderRadius:"50%", animation:"spin 0.75s linear infinite", flexShrink:0 }} />
  )
}

export function CheckItem({ label, pass, value }) {
  return (
    <div style={{
      display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"9px 12px", borderRadius:"var(--radius-xs)", marginBottom:6,
      background: pass ? "var(--green-bg)" : "var(--red-bg)",
      border:`1px solid ${pass ? "var(--green-border)" : "var(--red-border)"}`,
    }}>
      <div style={{ display:"flex", alignItems:"center", gap:8 }}>
        <div style={{ width:16, height:16, borderRadius:"50%", background: pass ? "var(--green)" : "var(--red)", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
          <span style={{ fontSize:9, color:"#fff", fontWeight:800 }}>{pass ? "✓" : "✗"}</span>
        </div>
        <span style={{ fontSize:12, fontWeight:500, color:"var(--text)" }}>{label}</span>
      </div>
      <span style={{ fontSize:11, color:"var(--text3)", fontFamily:"var(--font-mono)" }}>{value}</span>
    </div>
  )
}

export function Divider({ label }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:12, margin:"16px 0" }}>
      <div style={{ flex:1, height:"1px", background:"var(--border)" }} />
      {label && <span style={{ fontSize:11, color:"var(--text3)", fontWeight:600, letterSpacing:"0.05em", whiteSpace:"nowrap" }}>{label}</span>}
      <div style={{ flex:1, height:"1px", background:"var(--border)" }} />
    </div>
  )
}

export function StatGrid({ items }) {
  return (
    <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(100px,1fr))", gap:8 }}>
      {items.map(([label, value, color]) => (
        <div key={label} style={{ padding:"10px 12px", background:"var(--bg3)", borderRadius:"var(--radius-xs)", border:"1px solid var(--border)" }}>
          <div style={{ fontSize:10, color:"var(--text3)", fontWeight:600, marginBottom:4, textTransform:"uppercase", letterSpacing:"0.06em" }}>{label}</div>
          <div style={{ fontSize:14, fontWeight:700, color: color || "var(--text)", fontFamily:"var(--font-mono)" }}>{value}</div>
        </div>
      ))}
    </div>
  )
}
