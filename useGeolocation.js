/**
 * useGeolocation — M67
 * BFIU §4.5: Captures GPS, validates BD bounds, attaches headers to all API calls.
 * Usage: const { geo, geoStatus, requestGeo } = useGeolocation()
 */
import { useState, useEffect, useCallback } from "react"
import axios from "axios"

// Bangladesh bounding box
const BD_BOUNDS = { latMin: 20.5, latMax: 26.7, lonMin: 88.0, lonMax: 92.7 }

function isWithinBD(lat, lon) {
  return lat >= BD_BOUNDS.latMin && lat <= BD_BOUNDS.latMax &&
         lon >= BD_BOUNDS.lonMin && lon <= BD_BOUNDS.lonMax
}

export function useGeolocation() {
  const [geo, setGeo] = useState(null)          // { lat, lon, accuracy, withinBD }
  const [geoStatus, setGeoStatus] = useState("idle") // idle|requesting|ok|denied|error|outside_bd

  const applyGeoHeaders = useCallback((lat, lon, accuracy) => {
    axios.defaults.headers.common["X-Geo-Lat"]      = String(lat)
    axios.defaults.headers.common["X-Geo-Lng"]      = String(lon)
    axios.defaults.headers.common["X-Geo-Accuracy"] = String(accuracy || "")
  }, [])

  const requestGeo = useCallback(() => {
    if (!navigator.geolocation) {
      setGeoStatus("error")
      return
    }
    setGeoStatus("requesting")
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lon, accuracy } = pos.coords
        const withinBD = isWithinBD(lat, lon)
        setGeo({ lat, lon, accuracy, withinBD })
        setGeoStatus(withinBD ? "ok" : "outside_bd")
        applyGeoHeaders(lat, lon, accuracy)
        // Persist for session
        sessionStorage.setItem("ekyc_geo", JSON.stringify({ lat, lon, accuracy, withinBD }))
      },
      (err) => {
        setGeoStatus(err.code === 1 ? "denied" : "error")
        // Still try cached
        const cached = sessionStorage.getItem("ekyc_geo")
        if (cached) {
          const g = JSON.parse(cached)
          setGeo(g)
          applyGeoHeaders(g.lat, g.lon, g.accuracy)
          setGeoStatus(g.withinBD ? "ok" : "outside_bd")
        }
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 300000 }
    )
  }, [applyGeoHeaders])

  // Auto-request on mount
  useEffect(() => {
    // Check cache first
    const cached = sessionStorage.getItem("ekyc_geo")
    if (cached) {
      const g = JSON.parse(cached)
      setGeo(g)
      applyGeoHeaders(g.lat, g.lon, g.accuracy)
      setGeoStatus(g.withinBD ? "ok" : "outside_bd")
    } else {
      requestGeo()
    }
  }, [])

  return { geo, geoStatus, requestGeo }
}

/**
 * GeoBanner component — shows geo status in UI
 */
export function GeoBanner({ geoStatus, geo, onRequest }) {
  if (geoStatus === "idle" || geoStatus === "requesting") {
    return (
      <div className="geo-banner geo-banner-warn" style={{ marginBottom: 10 }}>
        <span style={{ fontSize: 14 }}>📍</span>
        <span>{geoStatus === "requesting" ? "Detecting location…" : "Location required for BFIU §4.5 compliance"}</span>
        {geoStatus === "idle" && (
          <button onClick={onRequest} style={{ marginLeft: "auto", padding: "2px 10px", borderRadius: 20, background: "var(--yellow-bg)", border: "1px solid var(--yellow-border)", color: "var(--yellow)", fontSize: 10, fontWeight: 700, fontFamily: "var(--font)", cursor: "pointer" }}>
            Enable
          </button>
        )}
      </div>
    )
  }
  if (geoStatus === "denied" || geoStatus === "error") {
    return (
      <div className="geo-banner geo-banner-warn">
        <span style={{ fontSize: 14 }}>⚠️</span>
        <span>Location access denied — geo data unavailable. Enable in browser settings.</span>
      </div>
    )
  }
  if (geoStatus === "outside_bd") {
    return (
      <div className="geo-banner geo-banner-err">
        <span style={{ fontSize: 14 }}>🚫</span>
        <span>Location outside Bangladesh — eKYC restricted per BFIU §4.5</span>
      </div>
    )
  }
  if (geoStatus === "ok" && geo) {
    return (
      <div className="geo-banner" style={{ marginBottom: 10 }}>
        <span style={{ fontSize: 14 }}>📍</span>
        <span>Bangladesh ✓ — {geo.lat.toFixed(4)}°N {geo.lon.toFixed(4)}°E (±{Math.round(geo.accuracy || 0)}m)</span>
        <span className="pill pill-green" style={{ marginLeft: "auto" }}>BFIU §4.5</span>
      </div>
    )
  }
  return null
}
