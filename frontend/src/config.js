const host = window.location.hostname
export const API = host === "localhost" || host === "127.0.0.1"
  ? "http://localhost:8000"
  : `http://${host}:8000`
