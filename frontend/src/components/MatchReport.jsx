import axios from "axios"
import { useState, useEffect } from "react"
import { Card, ScoreBar, CheckItem, Badge, Btn, Spinner, SectionTitle, StatGrid, Divider } from "./ui"
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Eye } from "lucide-react"

import { API } from "../config.js"

export default function MatchReport({ nidB64, liveB64, livenessResults, onReset, onContinue }) {
  const [result,  setResult]  = useState(null)
  const [aiData,  setAiData]  = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => { runVerification() }, [])

  const runVerification = async () => {
    setLoading(true); setError(null)
    try {
      const [vr, ar] = await Promise.all([
        axios.post(`${API}/api/v1/face/verify`, { nid_image_b64:nidB64, live_image_b64:liveB64, session_id:`s_${Date.now()}` }),
        axios.post(`${API}/api/v1/ai/analyze`,  { image_b64:liveB64, session_id:`a_${Date.now()}` }),
      ])
      setResult(vr.data); setAiData(ar.data)
    } catch(e) {
      setError(e?.response?.data?.detail || "Verification failed. Is the backend running?")
    } finally { setLoading(false) }
  }

  if (loading) return (
    <Card style={{ textAlign:"center", padding:"60px 40px" }}>
      <Spinner size={44} />
      <div style={{ fontSize:17, fontWeight:800, color:"var(--text)", marginTop:20, marginBottom:6, letterSpacing:"-0.02em" }}>Running AI Verification</div>
      <div style={{ color:"var(--text2)", fontSize:13, marginBottom:28 }}>Face detection · Liveness · Biometric matching · AI analysis</div>
      <div style={{ display:"flex", justifyContent:"center", gap:24, flexWrap:"wrap" }}>
        {["Face Detection","Liveness Check","Biometric Match","AI Analysis"].map((t,i) => (
          <div key={t} style={{ fontSize:11, color:"var(--text3)", display:"flex", alignItems:"center", gap:5 }}>
            <div style={{ width:5, height:5, borderRadius:"50%", background:"var(--accent)", animation:`pulse 1.5s ease ${i*0.3}s infinite` }} />{t}
          </div>
        ))}
      </div>
    </Card>
  )

  if (error) return (
    <Card style={{ textAlign:"center", padding:"48px 40px" }}>
      <div style={{ width:56, height:56, borderRadius:16, background:"var(--red-bg)", border:"1px solid var(--red-border)", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 16px" }}>
        <XCircle size={24} color="var(--red)" strokeWidth={2}/>
      </div>
      <div style={{ fontSize:15, fontWeight:700, color:"var(--text)", marginBottom:6 }}>Verification Error</div>
      <div style={{ fontSize:13, color:"var(--text2)", marginBottom:22, maxWidth:360, margin:"0 auto 22px" }}>{error}</div>
      <Btn onClick={runVerification}>Retry</Btn>
    </Card>
  )

  if (!result) return null

  const v   = result.verdict
  const ms  = result.match_scores
  const cfg = {
    MATCHED: { color:"var(--green)",  bg:"var(--green-bg)",  border:"var(--green-border)",  Icon:CheckCircle,   label:"Verified"       },
    REVIEW:  { color:"var(--yellow)", bg:"var(--yellow-bg)", border:"var(--yellow-border)", Icon:AlertTriangle, label:"Manual Review"  },
    FAILED:  { color:"var(--red)",    bg:"var(--red-bg)",    border:"var(--red-border)",    Icon:XCircle,       label:"Failed"         },
  }[v] || {}
  const { Icon } = cfg

  return (
    <div style={{ animation:"fadeUp 0.3s ease both" }}>

      {/* Verdict */}
      <div style={{ padding:"20px 24px", borderRadius:"var(--radius)", background:cfg.bg, border:`1px solid ${cfg.border}`, display:"flex", alignItems:"center", gap:16, marginBottom:16, boxShadow:"var(--shadow-sm)" }}>
        <div style={{ width:48, height:48, borderRadius:14, background:"var(--bg2)", border:`1px solid ${cfg.border}`, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
          <Icon size={22} color={cfg.color} strokeWidth={2}/>
        </div>
        <div style={{ flex:1 }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
            <span style={{ fontSize:20, fontWeight:800, color:cfg.color, letterSpacing:"-0.02em" }}>{cfg.label}</span>
            {v === "MATCHED" && <Badge color="green">BFIU §3.3</Badge>}
            {v === "REVIEW"  && <Badge color="yellow">Needs Review</Badge>}
            {v === "FAILED"  && <Badge color="red">Not Verified</Badge>}
          </div>
          <div style={{ fontSize:13, color:"var(--text2)" }}>{result.verdict_reason}</div>
        </div>
        <div style={{ textAlign:"right", flexShrink:0 }}>
          <div style={{ fontSize:38, fontWeight:800, color:cfg.color, lineHeight:1, letterSpacing:"-0.03em", fontFamily:"var(--font-mono)" }}>{result.confidence}%</div>
          <div style={{ fontSize:10, color:"var(--text3)", marginTop:2, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.06em" }}>Confidence</div>
        </div>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>

        {/* Face previews + scores */}
        <Card style={{ animation:"none" }}>
          <SectionTitle sub="Extracted & compared">Detected Faces</SectionTitle>
          <div style={{ display:"flex", justifyContent:"space-around", alignItems:"center", marginBottom:18 }}>
            {[
              { src:result.faces.nid_face_preview,  label:"NID Photo",  found:result.faces.nid_face_detected,  coords:result.faces.nid_face_coords  },
              { src:result.faces.live_face_preview, label:"Live Selfie", found:result.faces.live_face_detected, coords:result.faces.live_face_coords },
            ].map((f,i) => (
              <div key={i} style={{ textAlign:"center" }}>
                <div style={{
                  width:88, height:88, borderRadius:12, overflow:"hidden",
                  border:`2px solid ${f.found ? "var(--accent)" : "var(--border)"}`,
                  background:"var(--bg3)", display:"flex", alignItems:"center", justifyContent:"center",
                  margin:"0 auto 8px",
                  boxShadow: f.found ? "0 0 0 3px var(--accent-bg)" : "none",
                }}>
                  {f.src ? <img src={f.src} style={{ width:"100%", height:"100%", objectFit:"cover" }} alt={f.label}/> : <Eye size={20} color="var(--text3)" strokeWidth={1.5}/>}
                </div>
                <div style={{ fontSize:11, fontWeight:700, color:"var(--text)", marginBottom:2 }}>{f.label}</div>
                {f.coords && <div style={{ fontSize:10, color:"var(--text3)", fontFamily:"var(--font-mono)" }}>{f.coords.w}×{f.coords.h}</div>}
                <div style={{ fontSize:10, color: f.found ? "var(--green)" : "var(--red)", marginTop:2, fontWeight:600 }}>
                  {f.found ? "✓ Detected" : "✗ Not found"}
                </div>
              </div>
            ))}
            <div style={{ fontSize:16, color:"var(--text4)", userSelect:"none" }}>↔</div>
          </div>

          <Divider label="Match Scores" />

          {ms ? (
            <>
              <ScoreBar label="Overall Confidence"    value={ms.confidence}      />
              <ScoreBar label="SSIM Structural"       value={ms.ssim_score      ?? 0} color="var(--green)"  />
              <ScoreBar label="ORB Feature Points"    value={ms.feature_score   ?? 0} color="var(--accent)" />
              <ScoreBar label="Pixel Similarity"      value={ms.pixel_score     ?? 0} color="var(--blue)"   />
              <ScoreBar label="Histogram Correlation" value={ms.histogram_score ?? 0} color="var(--yellow)" />
              <div style={{ fontSize:10, color:"var(--text3)", marginTop:8, padding:"6px 10px", background:"var(--bg3)", borderRadius:"var(--radius-xs)", border:"1px solid var(--border)", fontFamily:"var(--font-mono)" }}>
                SSIM 35% · Histogram 30% · ORB 25% · Pixel 10%
              </div>
            </>
          ) : (
            <div style={{ color:"var(--text3)", fontSize:12, textAlign:"center", padding:"16px 0" }}>Scores unavailable</div>
          )}
        </Card>

        {/* AI Analysis */}
        <Card style={{ animation:"none" }}>
          <SectionTitle sub="MediaPipe · 478 landmarks">AI Face Analysis</SectionTitle>
          {aiData?.face_detected ? (
            <>
              <StatGrid items={[
                ["Age",       aiData.attributes?.age_estimate    ?? "—"],
                ["Profile",   aiData.attributes?.gender_estimate ?? "—"],
                ["Skin",      aiData.attributes?.skin_tone       ?? "—"],
                ["Direction", aiData.head_pose?.direction        ?? "—"],
                ["Smile",     `${aiData.expression?.smile_score ?? 0}%`],
                ["Landmarks", `${aiData.landmark_count}`],
              ]} />
              <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginTop:12 }}>
                {aiData.blink?.detected        && <Badge color="blue">Blink ✓</Badge>}
                {aiData.expression?.is_smiling && <Badge color="green">Smiling</Badge>}
                {aiData.face_detected          && <Badge color="accent">{aiData.landmark_count} pts</Badge>}
              </div>
            </>
          ) : (
            <div style={{ color:"var(--text3)", fontSize:12, textAlign:"center", padding:"20px 0" }}>AI data unavailable</div>
          )}

          <Divider label="Liveness — BFIU Annexure-2" />

          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10 }}>
            <span style={{ fontSize:12, color:"var(--text2)", fontWeight:500 }}>Checks passed</span>
            <Badge color={result.liveness.overall_pass ? "green" : "red"}>
              {result.liveness.score}/{result.liveness.max_score}
            </Badge>
          </div>
          {Object.entries(result.liveness)
            .filter(([k]) => !["overall_pass","score","max_score"].includes(k))
            .map(([,val]) => (
              <CheckItem key={val.label} label={val.label} pass={val.pass} value={String(val.value)} />
            ))}
        </Card>
      </div>

      {/* Session meta */}
      <Card style={{ animation:"none", marginBottom:20 }}>
        <SectionTitle sub="Audit trail">Session Details</SectionTitle>
        <StatGrid items={[
          ["Session ID",  result.session_id],
          ["Timestamp",   result.timestamp],
          ["Processing",  `${result.processing_ms} ms`],
          ["Guideline",   result.bfiu_ref?.guideline ?? "—"],
        ]} />
      </Card>

      <div style={{ display:"flex", gap:8 }}>
        <Btn onClick={onReset} variant="ghost"><RefreshCw size={13} strokeWidth={2.5}/> New Verification</Btn>
        <Btn onClick={runVerification} variant="ghost">↻ Re-run Analysis</Btn>
      </div>
    </div>
  )
}
