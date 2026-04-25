/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f0f7ff",
          100: "#e0effe",
          200: "#bae0fd",
          300: "#7cc8fb",
          400: "#36aaf5",
          500: "#0c8ee0",
          600: "#006fbe",
          700: "#00589a",
          800: "#044b80",
          900: "#0a3f6a",
          950: "#07284a",
        },
        xpert: {
          blue:   "#0066CC",
          navy:   "#003366",
          gold:   "#FFB300",
          green:  "#00A86B",
          red:    "#DC2626",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        "glow-blue": "0 0 20px rgba(0,102,204,0.3)",
        "glow-green": "0 0 20px rgba(0,168,107,0.3)",
        "card": "0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.12), 0 8px 32px rgba(0,0,0,0.08)",
      },
      animation: {
        "fade-up":    "fadeUp 0.3s cubic-bezier(0.34,1.56,0.64,1) both",
        "fade-in":    "fadeIn 0.2s ease both",
        "slide-in":   "slideIn 0.3s cubic-bezier(0.34,1.56,0.64,1) both",
        "pulse-dot":  "pulseDot 2s infinite",
        "spin-slow":  "spin 3s linear infinite",
      },
      keyframes: {
        fadeUp:    { from: { opacity:0, transform:"translateY(12px)" }, to: { opacity:1, transform:"translateY(0)" } },
        fadeIn:    { from: { opacity:0 }, to: { opacity:1 } },
        slideIn:   { from: { opacity:0, transform:"translateX(-12px)" }, to: { opacity:1, transform:"translateX(0)" } },
        pulseDot:  { "0%,100%": { opacity:1 }, "50%": { opacity:0.4 } },
      },
      backgroundImage: {
        "gradient-brand": "linear-gradient(135deg, #003366 0%, #0066CC 50%, #00A86B 100%)",
        "gradient-dark":  "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
        "mesh": "radial-gradient(at 40% 20%, #0066CC22 0px, transparent 50%), radial-gradient(at 80% 80%, #00A86B22 0px, transparent 50%)",
      },
    },
  },
  plugins: [],
}
