
import { useState, useRef } from "react"
import axios from "axios"
import { Card, Btn, CheckItem, Badge, SectionTitle, Divider } from "./ui"
import { Upload, Camera, RotateCcw, CheckCircle, Loader, AlertCircle, ArrowRight } from "lucide-react"
import Webcam from "react-webcam"
import ConsentGate from "./ConsentGate"
import { API } from "../config.js"

function UploadZone({ label, preview, onFile, onCamera, hint }) {
  const [dragOver, setDragOver] = useState(false)
  const [camMode, setCamMode]   = useState(false)
  const [camReady, setCamReady] = useState(false)
  const webcamRef = useRef(null)

  const loadFile = (file) => {
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => onFile(ev.target.result)
    reader.readAsDataURL(file)
  }

  const capture = () => {
    const img = webcamRef.current?.getScreenshot()
    if (img) { onFile(img); setCamMode(false) }
  }

  return (
    <div>
      <div style={{ fontSize:12, fontWeight:700, color:"var(--text2)",
        marginBottom:8, display:"flex", alignItems:"center", gap:6 }}>
        {label}
        {hint && <span style={{ fontSize:10, color:"var(--text3)", fontWeight:400 }}>— {hint}</span>}
      </div>
      {camMode ? (
        <div style={{ borderRadius:"var(--radius-sm)", overflow:"hidden", background:"#000",
          border:"1px solid var(--border)" }}>
          <div style={{ position:"relative" }}>
            <Webcam ref={webcamRef} audio={false} screenshotFormat="image/jpeg"
              videoConstraints={{ width:640, height:400, facingMode:{ideal:"environment"} }}
              onUserMedia={() => setCamReady(true)}
              style={{ width:"100%", display:"block" }}/>
            {camReady && <div style={{ position:"absolute", left:0, right:0, height:2,
              background:"linear-gradient(90deg,transparent,var(--accent),transparent)",
              animation:"scanline 2s linear infinite", pointerEvents:"none" }}/>}
          </div>
          <div style={{ padding:"8px", background:"var(--bg3)", display:"flex", gap:8 }}>
            <Btn onClick={capture} disabled={!camReady} style={{ flex:1, justifyContent:"center" }} size="sm">
              <Camera size={12}/> {camReady ? "Capture" : "Starting..."}
            </Btn>
            <Btn variant="ghost" size="sm" onClick={() => { setCamMode(false); setCamReady(false) }}>Cancel</Btn>
          </div>
        </div>
      ) : (
        <label
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); loadFile(e.dataTransfer.files[0]) }}
          style={{ display:"block", cursor:"pointer" }}>
          <input type="file" accept="image/*" onChange={e => loadFile(e.target.files[0])} style={{ display:"none" }}/>
          <div style={{
            border:`2px dashed ${dragOver ? "var(--accent)" : preview ? "var(--green)" : "var(--border-h)"}`,
            borderRadius:"var(--radius-sm)", minHeight:140,
            display:"flex", alignItems:"center", justifyContent:"center",
            background: preview ? "var(--bg3)" : dragOver ? "var(--accent-bg)" : "var(--bg3)",
            overflow:"hidden", transition:"all 0.2s", position:"relative",
          }}>
            {preview ? (
              <>
                <img src={preview} alt={label}
                  style={{ width:"100%", maxHeight:160, objectFit:"contain", display:"block" }}/>
                <div style={{ position:"absolute", top:6, right:6 }}>
                  <Badge color="green">✓ Loaded</Badge>
                </div>
              </>
            ) : (
              <div style={{ textAlign:"center", padding:"20px 16px" }}>
                <Upload size={22} color="var(--text3)" strokeWidth={1.5} style={{ margin:"0 auto 10px" }}/>
                <div style={{ fontSize:12, fontWeight:700, color:"var(--text)", marginBottom:3 }}>
                  {dragOver ? "Drop here" : `Drop ${label}`}
                </div>
                <div style={{ fontSize:11, color:"var(--text3)" }}>or click to browse</div>
              </div>
            )}
          </div>
        </label>
      )}
      <div style={{ display:"flex", gap:6, marginTop:6 }}>
        {preview && (
          <Btn size="sm" variant="ghost" onClick={() => onFile(null)} style={{ flex:1, justifyContent:"center" }}>
            <RotateCcw size={11}/> Retake
          </Btn>
        )}
        <Btn size="sm" variant="ghost" onClick={() => setCamMode(true)} style={{ flex:1, justifyContent:"center" }}>
          <Camera size={11}/> Camera
        </Btn>
      </div>
    </div>
  )
}

export default function NIDScanner({ onNIDCaptured, nidEntry, onBack }) {
  const [frontB64,   setFrontB64]   = useState(null)
  const [backB64,    setBackB64]    = useState(null)
  const [scanning,   setScanning]   = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [showConsent,setShowConsent]= useState(false)
  const [consentRecord,setConsentRecord] = useState(null)

  const canAnalyze = !!frontB64

  const analyzeNID = async () => {
    if (!frontB64) return
    setScanning(true)
    try {
      const { data } = await axios.post(`${API}/api/v1/ai/scan-nid`, {
        image_b64:  frontB64,
        session_id: `nid_${Date.now()}`
      })
      setScanResult(data)
    } catch(e) {
      setScanResult({ error: e?.response?.data?.detail || e?.message || JSON.stringify(e) })
    } finally { setScanning(false) }
  }

  const reset = () => {
    setFrontB64(null); setBackB64(null); setScanResult(null)
  }

  const confirm = () => {
    if (frontB64 && scanResult?.is_valid_nid) setShowConsent(true)
  }

  const onConsented = (consent) => {
    setShowConsent(false)
    setConsentRecord(consent)
    // Pass both front and back, plus scan result with fields
    onNIDCaptured(frontB64, {
      ...scanResult,
      back_b64: backB64,
    })
  }

  const qColor = { Excellent:"green", Good:"green", Fair:"yellow", Poor:"red", Invalid:"red" }[scanResult?.quality_label] || "red"

  return (
    <>
      {showConsent && (
        <ConsentGate
          sessionId={`nid_${Date.now()}`}
          nidHash={scanResult?.nid_hash || "N/A"}
          onConsented={onConsented}
          onDeclined={() => setShowConsent(false)}
        />
      )}

      {nidEntry && (
        <div style={{ marginBottom:16, padding:"11px 16px", borderRadius:"var(--radius-sm)",
          background:"var(--accent-bg)", border:"1px solid rgba(91,79,255,0.2)",
          display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div style={{ fontSize:12, color:"var(--accent)", fontWeight:600 }}>
            NID: <span style={{ fontFamily:"var(--font-mono)" }}>{nidEntry.nidNumber}</span>
            {" · "} DOB: <span style={{ fontFamily:"var(--font-mono)" }}>{nidEntry.dob}</span>
          </div>
          <button onClick={onBack} style={{ fontSize:11, color:"var(--accent)", background:"none",
            border:"none", cursor:"pointer", fontFamily:"var(--font)", fontWeight:600 }}>
            ← Change
          </button>
        </div>
      )}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        {/* Left — Upload */}
        <Card>
          <SectionTitle sub="BFIU §3.3 Step 1 — Front side first, then back page">
            Upload NID Card
          </SectionTitle>

          <div style={{ display:"grid", gap:16 }}>
            <UploadZone
              label="Front Side"
              preview={frontB64}
              onFile={setFrontB64}
              hint="Required — contains photo and NID number"
            />
            <UploadZone
              label="Back Side"
              preview={backB64}
              onFile={setBackB64}
              hint="Recommended — contains permanent address"
            />
          </div>

          {frontB64 && (
            <div style={{ marginTop:14, display:"flex", gap:8 }}>
              <Btn onClick={analyzeNID} loading={scanning} style={{ flex:1, justifyContent:"center" }}>
                {scanning ? "Analyzing..." : "Check NID Quality"}
              </Btn>
              <Btn variant="ghost" onClick={reset} style={{ padding:"10px 12px" }}>
                <RotateCcw size={13} strokeWidth={2.5}/>
              </Btn>
            </div>
          )}

          {!frontB64 && (
            <>
              <Divider label="BFIU Requirements"/>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
                {[
                  ["Annex-2a","High-res, sharp photo"],
                  ["Annex-2b","White lighting"],
                  ["Annex-2d","No glare on card"],
                  ["Annex-2e","Face fully visible"],
                ].map(([ref, text]) => (
                  <div key={ref} style={{ display:"flex", gap:7, alignItems:"flex-start",
                    padding:"8px 10px", background:"var(--bg3)",
                    borderRadius:"var(--radius-xs)", border:"1px solid var(--border)" }}>
                    <span style={{ fontSize:9, fontWeight:700, color:"var(--accent)",
                      background:"var(--accent-bg)", padding:"2px 6px",
                      borderRadius:4, whiteSpace:"nowrap", marginTop:1 }}>{ref}</span>
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
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center",
              justifyContent:"center", padding:"48px 20px", textAlign:"center" }}>
              <div style={{ width:56, height:56, borderRadius:16, background:"var(--bg3)",
                border:"1px solid var(--border)", display:"flex", alignItems:"center",
                justifyContent:"center", marginBottom:14 }}>
                <span style={{ fontSize:24 }}>🪪</span>
              </div>
              <div style={{ fontSize:13, fontWeight:600, color:"var(--text2)", marginBottom:4 }}>
                No NID analyzed yet
              </div>
              <div style={{ fontSize:12, color:"var(--text3)" }}>
                Upload the front side of your NID card to begin
              </div>
              {!backB64 && frontB64 && (
                <div style={{ marginTop:12, padding:"9px 14px", background:"var(--yellow-bg)",
                  border:"1px solid var(--yellow-border)", borderRadius:"var(--radius-sm)",
                  fontSize:11, color:"var(--yellow)" }}>
                  💡 Also upload the back side for complete address extraction
                </div>
              )}
            </div>
          )}

          {scanning && (
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center",
              justifyContent:"center", padding:"48px 20px", textAlign:"center", gap:12 }}>
              <Loader size={32} color="var(--accent)" style={{ animation:"spin 1s linear infinite" }}/>
              <div style={{ fontSize:13, fontWeight:600, color:"var(--text2)" }}>Analyzing NID card...</div>
              <div style={{ fontSize:12, color:"var(--text3)" }}>Checking quality, glare, face detection</div>
            </div>
          )}

          {scanResult && !scanResult.error && (
            <>
              <div style={{ display:"flex", alignItems:"center", gap:14,
                padding:"14px 16px", background:"var(--bg3)",
                borderRadius:"var(--radius-sm)", border:"1px solid var(--border)", marginBottom:16 }}>
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:10, fontWeight:600, color:"var(--text3)",
                    textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:4 }}>
                    Scan Quality
                  </div>
                  <div style={{ fontSize:28, fontWeight:800,
                    color:`var(--${qColor})`, lineHeight:1, letterSpacing:"-0.02em" }}>
                    {scanResult.quality_score}
                    <span style={{ fontSize:14, color:"var(--text3)", fontWeight:500 }}>/5</span>
                  </div>
                </div>
                <Badge color={qColor}>{scanResult.quality_label}</Badge>
              </div>

              {/* OCR extracted fields */}
              {scanResult.fields && (
                <div style={{ marginBottom:12, padding:"10px 14px", background:"var(--accent-bg)",
                  border:"1px solid rgba(91,79,255,0.2)", borderRadius:"var(--radius-sm)" }}>
                  <div style={{ fontSize:11, fontWeight:700, color:"var(--accent)",
                    marginBottom:8, textTransform:"uppercase", letterSpacing:"0.05em" }}>
                    Extracted OCR Fields
                  </div>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:4 }}>
                    {[
                      ["Name",    scanResult.fields.full_name_en],
                      ["DOB",     scanResult.fields.date_of_birth],
                      ["NID No.", scanResult.fields.nid_number],
                      ["Father",  scanResult.fields.fathers_name_en],
                    ].filter(([,v]) => v).map(([label, val]) => (
                      <div key={label} style={{ fontSize:11, color:"var(--text2)" }}>
                        <span style={{ color:"var(--text3)", fontWeight:600 }}>{label}:</span>{" "}
                        <span style={{ fontFamily:"var(--font-mono)", fontSize:10 }}>{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.entries(scanResult.checks).map(([k,v]) => (
                <CheckItem key={k} label={v.label} pass={v.pass} value={String(v.value)}/>
              ))}

              {!scanResult.is_valid_nid && scanResult.nid_issues?.length > 0 && (
                <div style={{ padding:"14px 16px", background:"var(--red-bg)",
                  border:"1px solid var(--red-border)", borderRadius:"var(--radius-sm)", marginBottom:12 }}>
                  <div style={{ fontSize:13, fontWeight:700, color:"var(--red)", marginBottom:8 }}>
                    Invalid NID Card
                  </div>
                  {scanResult.nid_issues.map((issue, i) => (
                    <div key={i} style={{ fontSize:12, color:"var(--text2)", marginBottom:4,
                      display:"flex", gap:6 }}>
                      <span style={{ color:"var(--red)" }}>•</span>{issue}
                    </div>
                  ))}
                </div>
              )}

              {scanResult.quality_score < 3 && (
                <div style={{ display:"flex", gap:8, padding:"10px 12px", background:"var(--yellow-bg)",
                  border:"1px solid var(--yellow-border)", borderRadius:"var(--radius-xs)",
                  marginTop:10, marginBottom:10 }}>
                  <AlertCircle size={14} color="var(--yellow)" strokeWidth={2.5} style={{ flexShrink:0, marginTop:1 }}/>
                  <span style={{ fontSize:12, color:"var(--yellow)", fontWeight:500 }}>
                    Low quality may reduce matching accuracy. Retake with better lighting.
                  </span>
                </div>
              )}

              {!backB64 && (
                <div style={{ display:"flex", gap:8, padding:"10px 12px", background:"var(--blue-bg)",
                  border:"1px solid var(--blue-border)", borderRadius:"var(--radius-xs)", marginBottom:12 }}>
                  <AlertCircle size={14} color="var(--blue)" strokeWidth={2.5} style={{ flexShrink:0, marginTop:1 }}/>
                  <span style={{ fontSize:12, color:"var(--blue)", fontWeight:500 }}>
                    Back side not uploaded — permanent address will not be extracted.
                  </span>
                </div>
              )}

              <Divider/>

              <Btn
                onClick={confirm}
                variant={scanResult.is_valid_nid
                  ? (scanResult.quality_score >= 3 ? "success" : "ghost")
                  : "danger"}
                disabled={!scanResult.is_valid_nid}
                size="lg"
                style={{ width:"100%", justifyContent:"center" }}
              >
                <CheckCircle size={14} strokeWidth={2.5}/>
                {scanResult.is_valid_nid
                  ? (scanResult.quality_score >= 3
                    ? "Confirm & Continue →"
                    : "Continue Anyway (Low Quality)")
                  : "Fix issues above to continue"}
              </Btn>
            </>
          )}

          {scanResult?.error && (
            <div style={{ display:"flex", gap:10, padding:"14px 16px", background:"var(--red-bg)",
              border:"1px solid var(--red-border)", borderRadius:"var(--radius-sm)", marginTop:8 }}>
              <AlertCircle size={15} color="var(--red)" strokeWidth={2.5} style={{ flexShrink:0, marginTop:1 }}/>
              <div>
                <div style={{ fontSize:13, fontWeight:600, color:"var(--red)", marginBottom:2 }}>
                  Analysis failed
                </div>
                <div style={{ fontSize:12, color:"var(--text2)" }}>{scanResult.error}</div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
