import { useState, useRef, useCallback, useEffect } from "react"
import Webcam from "react-webcam"
import axios from "axios"
import { Card, Btn, Spinner, Badge, SectionTitle } from "./ui"
import { Camera, RotateCcw, CheckCircle } from "lucide-react"

import { API } from "../config.js"

const CHALLENGES = [
  { id:"center", label:"Look straight",      hint:"Face the camera directly",     emoji:"👁",  color:"#6358ff" },
  { id:"blink",  label:"Blink slowly",        hint:"Close and open both eyes",     emoji:"😑",  color:"#2d7ef0" },
  { id:"left",   label:"Turn head left",      hint:"Slowly turn to your left",     emoji:"👈",  color:"#00b87a" },
  { id:"right",  label:"Turn head right",     hint:"Slowly turn to your right",    emoji:"👉",  color:"#f0a500" },
  { id:"smile",  label:"Smile naturally",     hint:"Give a genuine smile",         emoji:"😊",  color:"#f03d5f" },
]

export default function LivenessCapture({ onLivenessPassed }) {
  const [step,       setStep]       = useState(0)
  const [results,    setResults]    = useState([])
  const [checking,   setChecking]   = useState(false)
  const [feedback,   setFeedback]   = useState("")
  const [feedbackOk, setFeedbackOk] = useState(null)
  const [camReady,   setCamReady]   = useState(false)
  const [running,    setRunning]    = useState(false)
  const [analysis,   setAnalysis]   = useState(null)
  const webcamRef  = useRef(null)
  const intervalRef = useRef(null)

  const challenge  = CHALLENGES[step]
  const passed     = results.filter(r => r.passed).length
  const progress   = (passed / CHALLENGES.length) * 100

  useEffect(() => {
    if (!running || !camReady || checking) return
    intervalRef.current = setInterval(captureAndCheck, 1500)
    return () => clearInterval(intervalRef.current)
  }, [running, camReady, checking, step])

  const captureAndCheck = useCallback(async () => {
    const img = webcamRef.current?.getScreenshot()
    if (!img || checking) return
    setChecking(true)
    try {
      const { data } = await axios.post(`${API}/api/v1/ai/challenge`, {
        image_b64: img, challenge: CHALLENGES[step]?.id, session_id: `lv_step${step}`
      })
      setAnalysis(data)
      setFeedback(data.reason)
      setFeedbackOk(data.passed)

      if (data.passed) {
        clearInterval(intervalRef.current)
        setRunning(false)
        const newResults = [...results, { challenge: CHALLENGES[step].id, passed: true, snap: img }]
        setResults(newResults)

        if (step + 1 >= CHALLENGES.length) {
          setTimeout(() => onLivenessPassed(img, newResults), 600)
        } else {
          setTimeout(async () => {
            try {
              await axios.post(`${API}/api/v1/ai/reset-session`, {
                image_b64: "x", session_id: `lv_step${step}`
              })
            } catch(e) {}
            setStep(s => s + 1)
            setRunning(true)
            setFeedback("")
            setFeedbackOk(null)
            setAnalysis(null)
          }, 500)
        }
      }
    } catch(e) {
      setFeedback("Analysis error — retrying...")
      setFeedbackOk(false)
    } finally { setChecking(false) }
  }, [step, results, checking])

  const start = () => { setRunning(true); setFeedback("Analyzing..."); setFeedbackOk(null) }
  const pause = () => { setRunning(false); clearInterval(intervalRef.current); setFeedback("") }
  const reset = () => {
    pause(); setStep(0); setResults([]); setFeedback("")
    setFeedbackOk(null); setAnalysis(null)
  }

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>

      {/* Camera */}
      <Card style={{ padding:0, overflow:"hidden" }}>
        <div style={{ position:"relative", background:"#0a0a14", minHeight:320 }}>
          <Webcam ref={webcamRef} audio={false} screenshotFormat="image/jpeg"
            videoConstraints={{ width:480, height:360, facingMode:"user" }}
            onUserMedia={() => setCamReady(true)}
            style={{ width:"100%", display:"block", opacity: camReady ? 1 : 0, transition:"opacity 0.5s" }}
          />

          {!camReady && (
            <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column", gap:12 }}>
              <Spinner size={28} color="rgba(255,255,255,0.4)" />
              <span style={{ fontSize:12, color:"rgba(255,255,255,0.5)" }}>Starting camera...</span>
            </div>
          )}

          {/* Oval face guide */}
          {camReady && (
            <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", pointerEvents:"none" }}>
              <div style={{
                width:150, height:195, borderRadius:"50%",
                border:`2.5px solid ${challenge?.color || "rgba(255,255,255,0.4)"}`,
                boxShadow:`0 0 0 9999px rgba(0,0,0,0.42), 0 0 32px ${challenge?.color}44`,
                transition:"all 0.4s ease",
              }} />
            </div>
          )}

          {/* Scan line */}
          {running && camReady && (
            <div style={{ position:"absolute", left:0, right:0, height:2, background:`linear-gradient(90deg,transparent,${challenge?.color},transparent)`, animation:"scanline 1.8s linear infinite", pointerEvents:"none", opacity:0.7 }} />
          )}

          {/* Checking badge */}
          {checking && (
            <div style={{ position:"absolute", top:12, right:12, display:"flex", alignItems:"center", gap:6, background:"rgba(0,0,0,0.72)", backdropFilter:"blur(8px)", borderRadius:99, padding:"5px 10px" }}>
              <Spinner size={11} color="#fff" />
              <span style={{ fontSize:11, color:"#fff", fontWeight:500 }}>Analyzing</span>
            </div>
          )}

          {/* Current challenge overlay */}
          <div style={{ position:"absolute", bottom:0, left:0, right:0, background:"linear-gradient(transparent,rgba(0,0,0,0.78))", padding:"20px 16px 14px" }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <div style={{ width:34, height:34, borderRadius:99, background:`${challenge?.color}22`, border:`1.5px solid ${challenge?.color}66`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, flexShrink:0 }}>
                {challenge?.emoji}
              </div>
              <div>
                <div style={{ fontSize:10, color:"rgba(255,255,255,0.5)", marginBottom:1 }}>Step {step+1} of {CHALLENGES.length}</div>
                <div style={{ fontSize:13, color:"#fff", fontWeight:700 }}>{challenge?.label}</div>
                {feedback && (
                  <div style={{ fontSize:11, color: feedbackOk ? "#00d68f" : "rgba(255,255,255,0.6)", marginTop:2 }}>{feedback}</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div style={{ padding:"12px 14px", background:"var(--bg2)", borderTop:"1px solid var(--border)", display:"flex", gap:8 }}>
          {!running
            ? <Btn onClick={start} disabled={!camReady} style={{ flex:1, justifyContent:"center" }} size="sm">
                <Camera size={13} strokeWidth={2.5}/> {camReady ? "Start Verification" : "Waiting for camera..."}
              </Btn>
            : <Btn onClick={pause} variant="danger" style={{ flex:1, justifyContent:"center" }} size="sm">
                ⏸ Pause
              </Btn>
          }
          <Btn variant="ghost" onClick={reset} size="sm" style={{ padding:"7px 11px" }}>
            <RotateCcw size={13} strokeWidth={2.5}/>
          </Btn>
        </div>
      </Card>

      {/* Status panel */}
      <Card>
        <div style={{ marginBottom:20 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
            <SectionTitle sub="BFIU Annexure-2 compliant">Liveness Verification</SectionTitle>
            <span style={{ fontSize:11, fontWeight:700, fontFamily:"var(--font-mono)", color:"var(--text3)" }}>{Math.round(progress)}%</span>
          </div>
          <div style={{ background:"var(--bg4)", borderRadius:99, height:5, overflow:"hidden" }}>
            <div style={{ width:`${progress}%`, height:"100%", borderRadius:99, background:"linear-gradient(90deg,var(--accent),var(--green))", transition:"width 0.5s ease" }} />
          </div>
        </div>

        {/* Challenge list */}
        <div style={{ marginBottom:16 }}>
          {CHALLENGES.map((c, i) => {
            const done    = results.find(r => r.challenge === c.id)?.passed
            const current = i === step
            const pending = i > step
            return (
              <div key={c.id} style={{
                display:"flex", alignItems:"center", gap:11,
                padding:"10px 12px", borderRadius:"var(--radius-xs)", marginBottom:6,
                background: done ? "var(--green-bg)" : current ? `${c.color}10` : "var(--bg3)",
                border:`1px solid ${done ? "var(--green-border)" : current ? `${c.color}30` : "var(--border)"}`,
                transition:"all 0.3s",
                animation: current && running ? "slideIn 0.3s ease both" : "none",
              }}>
                <div style={{
                  width:30, height:30, borderRadius:"50%", flexShrink:0,
                  display:"flex", alignItems:"center", justifyContent:"center",
                  background: done ? "var(--green)" : current ? c.color : "var(--bg4)",
                  border:`1.5px solid ${done ? "var(--green)" : current ? c.color : "var(--border)"}`,
                  fontSize:13, transition:"all 0.3s",
                }}>
                  {done ? <CheckCircle size={14} color="#fff" strokeWidth={2.5}/> : current && running ? <Spinner size={13} color="#fff"/> : c.emoji}
                </div>
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:12, fontWeight:700, color: done ? "var(--green)" : current ? "var(--text)" : "var(--text3)" }}>
                    {c.label}
                  </div>
                  <div style={{ fontSize:11, color:"var(--text3)", marginTop:1 }}>
                    {done ? "Completed" : current && feedback ? feedback : c.hint}
                  </div>
                </div>
                {done    && <Badge color="green">✓</Badge>}
                {pending && <span style={{ fontSize:10, color:"var(--text4)", fontWeight:600 }}>Soon</span>}
              </div>
            )
          })}
        </div>

        {/* Live AI readings */}
        {analysis && (
          <div style={{ padding:"12px 14px", background:"var(--bg3)", borderRadius:"var(--radius-xs)", border:"1px solid var(--border)" }}>
            <div style={{ fontSize:10, fontWeight:700, color:"var(--text3)", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:10 }}>Live AI Readings</div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
              {[
                ["Direction",  analysis.head_direction || "—"],
                ["Blink",      analysis.blink_detected ? "Detected ✓" : "Not yet"],
                ["Smile",      `${analysis.smile_score || 0}%`],
                ["Face",       analysis.face_detected ? "Tracked ✓" : "Lost"],
              ].map(([k,v]) => (
                <div key={k} style={{ padding:"7px 9px", background:"var(--bg2)", borderRadius:"var(--radius-xs)", border:"1px solid var(--border)" }}>
                  <div style={{ fontSize:9, color:"var(--text3)", fontWeight:600, textTransform:"uppercase", letterSpacing:"0.05em", marginBottom:3 }}>{k}</div>
                  <div style={{ fontSize:12, fontWeight:700, color:"var(--text)", fontFamily:"var(--font-mono)" }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
