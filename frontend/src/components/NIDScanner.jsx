import { useState, useRef } from "react"
import axios from "axios"
import { Card, Btn, CheckItem, Badge, SectionTitle, Divider } from "./ui"
import { Upload, Camera, RotateCcw, CheckCircle, Loader, AlertCircle } from "lucide-react"
import Webcam from "react-webcam"

import { API } from "../config.js"

export default function NIDScanner({ onNIDCaptured }) {
  const [nidB64,     setNidB64]     = useState(null)
  const [preview,    setPreview]    = useState(null)
  const [scanning,   setScanning]   = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [camMode,    setCamMode]    = useState(false)
  const [camReady,   setCamReady]   = useState(false)
  const [dragOver,   setDragOver]   = useState(false)
  const webcamRef = useRef(null)

  const loadFile = (file) => {
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => { setNidB64(ev.target.result); setPreview(ev.target.result); setScanResult(null) }
    reader.readAsDataURL(file)
  }

  const captureFromCam = () => {
    const img = webcamRef.current?.getScreenshot()
    if (img) { setNidB64(img); setPreview(img); setScanResult(null); setCamMode(false) }
  }

  const analyzeNID = async () => {
    if (!nidB64) return
    setScanning(true)
    try {
      const { data } = await axios.post(`${API}/api/v1/ai/scan-nid`, { image_b64: nidB64, session_id: `nid_${Date.now()}` })
      setScanResult(data)
    } catch (e) {
      setScanResult({ error: e?.response?.data?.detail || e?.message || JSON.stringify(e) }); console.error("NID scan error:", e)
    } finally { setScanning(false) }
  }

  const reset = () => { setNidB64(null); setPreview(null); setScanResult(null); setCamMode(false); setCamReady(false) }
  const confirm = () => { if (nidB64) onNIDCaptured(nidB64, scanResult) }

  const qColor = { Excellent:"green", Good:"green", Fair:"yellow", Poor:"red" }[scanResult?.quality_label] || "red"

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>

      {/* Left */}
      <Card>
        <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:20 }}>
          <SectionTitle sub="Front side · Clear photo · No glare">Upload NID Card</SectionTitle>
          {!camMode && !preview && (
            <button onClick={() => setCamMode(true)} style={{
              display:"flex", alignItems:"center", gap:5, padding:"6px 11px",
              borderRadius:"var(--radius-xs)", background:"var(--bg3)",
              border:"1px solid var(--border)", cursor:"pointer",
              fontSize:11, fontWeight:600, color:"var(--text2)", fontFamily:"var(--font)",
              transition:"all 0.15s",
            }}>
              <Camera size={11} strokeWidth={2.5}/> Camera
            </button>
          )}
        </div>

        {/* Camera mode */}
        {camMode && (
          <div style={{ borderRadius:"var(--radius-sm)", overflow:"hidden", background:"#000", marginBottom:12, border:"1px solid var(--border)" }}>
            <div style={{ position:"relative" }}>
              <Webcam ref={webcamRef} audio={false} screenshotFormat="image/jpeg"
                videoConstraints={{ width:640, height:400, facingMode:{ideal:"environment"} }}
                onUserMedia={() => setCamReady(true)}
                style={{ width:"100%", display:"block" }}
              />
              <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", pointerEvents:"none" }}>
                <div style={{ width:"88%", height:"76%", border:`2px solid ${camReady ? "var(--accent)" : "rgba(255,255,255,0.3)"}`, borderRadius:10, boxShadow:"0 0 0 9999px rgba(0,0,0,0.45)", transition:"border-color 0.3s" }}>
                  <div style={{ position:"absolute", top:-22, left:0, right:0, textAlign:"center" }}>
                    <span style={{ fontSize:10, color:"rgba(255,255,255,0.85)", background:"rgba(0,0,0,0.55)", padding:"3px 10px", borderRadius:99 }}>Align NID card within frame</span>
                  </div>
                </div>
              </div>
              {camReady && <div style={{ position:"absolute", left:0, right:0, height:2, background:"linear-gradient(90deg,transparent,var(--accent),transparent)", animation:"scanline 2s linear infinite", pointerEvents:"none" }} />}
            </div>
            <div style={{ padding:"10px 12px", background:"var(--bg3)", display:"flex", gap:8 }}>
              <Btn onClick={captureFromCam} disabled={!camReady} style={{ flex:1, justifyContent:"center" }} size="sm">
                <Camera size={12}/> {camReady ? "Capture NID" : "Starting camera..."}
              </Btn>
              <Btn variant="ghost" size="sm" onClick={() => { setCamMode(false); setCamReady(false) }}>Cancel</Btn>
            </div>
          </div>
        )}

        {/* Upload dropzone */}
        {!camMode && (
          <label
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); loadFile(e.dataTransfer.files[0]) }}
            style={{ display:"block", cursor:"pointer" }}
          >
            <input type="file" accept="image/*" onChange={e => loadFile(e.target.files[0])} style={{ display:"none" }} />
            <div style={{
              border:`2px dashed ${dragOver ? "var(--accent)" : preview ? "var(--accent)" : "var(--border-h)"}`,
              borderRadius:"var(--radius-sm)", minHeight:220,
              display:"flex", alignItems:"center", justifyContent:"center",
              background: dragOver ? "var(--accent-bg)" : preview ? "var(--bg3)" : "var(--bg3)",
              overflow:"hidden", transition:"all 0.2s", position:"relative",
            }}>
              {preview ? (
                <>
                  <img src={preview} alt="NID" style={{ width:"100%", maxHeight:240, objectFit:"contain", display:"block" }} />
                  <div style={{ position:"absolute", top:8, right:8 }}>
                    <Badge color="accent">Loaded ✓</Badge>
                  </div>
                </>
              ) : (
                <div style={{ textAlign:"center", padding:"32px 24px" }}>
                  <div style={{ width:52, height:52, borderRadius:14, background:"var(--bg4)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 16px", transition:"all 0.2s" }}>
                    <Upload size={20} color="var(--text3)" strokeWidth={1.5} />
                  </div>
                  <div style={{ fontSize:13, fontWeight:700, color:"var(--text)", marginBottom:4 }}>
                    {dragOver ? "Drop it here" : "Drop NID photo here"}
                  </div>
                  <div style={{ fontSize:12, color:"var(--text3)", marginBottom:12 }}>or click to browse your files</div>
                  <div style={{ display:"inline-flex", alignItems:"center", gap:5, padding:"5px 12px", background:"var(--bg4)", borderRadius:99, border:"1px solid var(--border)" }}>
                    <span style={{ fontSize:11, color:"var(--text3)" }}>JPG · PNG · WEBP</span>
                  </div>
                </div>
              )}
            </div>
          </label>
        )}

        {/* Action row */}
        {preview && (
          <div style={{ display:"flex", gap:8, marginTop:14 }}>
            <Btn onClick={analyzeNID} loading={scanning} style={{ flex:1, justifyContent:"center" }}>
              {scanning ? "Analyzing..." : "Check NID Quality"}
            </Btn>
            <Btn variant="ghost" onClick={reset} style={{ padding:"10px 12px" }}>
              <RotateCcw size={13} strokeWidth={2.5}/>
            </Btn>
          </div>
        )}

        {/* BFIU tips */}
        {!preview && !camMode && (
          <>
            <Divider label="BFIU Requirements" />
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
              {[
                ["Annex-2a", "High-res, sharp photo"],
                ["Annex-2b", "White lighting"],
                ["Annex-2d", "No glare on card"],
                ["Annex-2e", "Face fully visible"],
              ].map(([ref, text]) => (
                <div key={ref} style={{ display:"flex", gap:7, alignItems:"flex-start", padding:"8px 10px", background:"var(--bg3)", borderRadius:"var(--radius-xs)", border:"1px solid var(--border)" }}>
                  <span style={{ fontSize:9, fontWeight:700, color:"var(--accent)", background:"var(--accent-bg)", padding:"2px 6px", borderRadius:4, whiteSpace:"nowrap", marginTop:1 }}>{ref}</span>
                  <span style={{ fontSize:11, color:"var(--text2)", lineHeight:1.4 }}>{text}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>

      {/* Right — Analysis */}
      <Card>
        <SectionTitle sub="BFIU §3.3 · Annexure-2d">NID Scan Analysis</SectionTitle>

        {!scanResult && !scanning && (
          <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:"48px 20px", textAlign:"center" }}>
            <div style={{ width:56, height:56, borderRadius:16, background:"var(--bg3)", border:"1px solid var(--border)", display:"flex", alignItems:"center", justifyContent:"center", marginBottom:14 }}>
              <span style={{ fontSize:24 }}>🪪</span>
            </div>
            <div style={{ fontSize:13, fontWeight:600, color:"var(--text2)", marginBottom:4 }}>No NID analyzed yet</div>
            <div style={{ fontSize:12, color:"var(--text3)" }}>Upload your NID card to see quality checks</div>
          </div>
        )}

        {scanning && (
          <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:"48px 20px", textAlign:"center", gap:12 }}>
            <div style={{ position:"relative" }}>
              <Loader size={32} color="var(--accent)" style={{ animation:"spin 1s linear infinite" }} />
            </div>
            <div style={{ fontSize:13, fontWeight:600, color:"var(--text2)" }}>Analyzing NID card...</div>
            <div style={{ fontSize:12, color:"var(--text3)" }}>Checking quality, glare, face detection</div>
          </div>
        )}

        {scanResult && !scanResult.error && (
          <>
            {/* Quality score */}
            <div style={{ display:"flex", alignItems:"center", gap:14, padding:"14px 16px", background:"var(--bg3)", borderRadius:"var(--radius-sm)", border:"1px solid var(--border)", marginBottom:16 }}>
              <div style={{ flex:1 }}>
                <div style={{ fontSize:10, fontWeight:600, color:"var(--text3)", textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:4 }}>Scan Quality</div>
                <div style={{ fontSize:28, fontWeight:800, color:`var(--${qColor})`, lineHeight:1, letterSpacing:"-0.02em" }}>
                  {scanResult.quality_score}<span style={{ fontSize:14, color:"var(--text3)", fontWeight:500 }}>/5</span>
                </div>
              </div>
              <Badge color={qColor}>{scanResult.quality_label}</Badge>
            </div>

            {Object.entries(scanResult.checks).map(([k,v]) => (
              <CheckItem key={k} label={v.label} pass={v.pass} value={String(v.value)} />
            ))}

            {scanResult.quality_score < 3 && (
              <div style={{ display:"flex", gap:8, padding:"10px 12px", background:"var(--yellow-bg)", border:"1px solid var(--yellow-border)", borderRadius:"var(--radius-xs)", marginTop:10, marginBottom:10 }}>
                <AlertCircle size={14} color="var(--yellow)" strokeWidth={2.5} style={{ flexShrink:0, marginTop:1 }} />
                <span style={{ fontSize:12, color:"var(--yellow)", fontWeight:500 }}>Low quality may reduce matching accuracy. Retake with better lighting.</span>
              </div>
            )}

            <Divider />

            <Btn
              onClick={confirm}
              variant={scanResult.quality_score >= 3 ? "success" : "ghost"}
              size="lg"
              style={{ width:"100%", justifyContent:"center" }}
            >
              <CheckCircle size={14} strokeWidth={2.5}/>
              {scanResult.quality_score >= 3 ? "Confirm & Continue" : "Continue Anyway"}
            </Btn>
          </>
        )}

        {scanResult?.error && (
          <div style={{ display:"flex", gap:10, padding:"14px 16px", background:"var(--red-bg)", border:"1px solid var(--red-border)", borderRadius:"var(--radius-sm)", marginTop:8 }}>
            <AlertCircle size={15} color="var(--red)" strokeWidth={2.5} style={{ flexShrink:0, marginTop:1 }} />
            <div>
              <div style={{ fontSize:13, fontWeight:600, color:"var(--red)", marginBottom:2 }}>Analysis failed</div>
              <div style={{ fontSize:12, color:"var(--text2)" }}>{scanResult.error}</div>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
