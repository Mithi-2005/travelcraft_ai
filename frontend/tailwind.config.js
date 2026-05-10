/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#050505",
        mist: "#f5f7fb",
        glass: "rgba(255,255,255,0.08)",
        glow: "#00FFC6",
        coral: "#FF6B6B",
        solar: "#FFB86A",
        iris: "#8E7CFF",
        aqua: "#84FFF0",
      },
      boxShadow: {
        soft: "0 22px 60px rgba(0,0,0,0.22)",
        glow: "0 0 0 1px rgba(0,255,198,0.22), 0 20px 50px rgba(0,255,198,0.18)",
        coral: "0 0 0 1px rgba(255,107,107,0.22), 0 18px 45px rgba(255,107,107,0.18)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
      backgroundImage: {
        "hero-radial":
          "radial-gradient(circle at top left, rgba(0,255,198,0.16), transparent 35%), radial-gradient(circle at 80% 20%, rgba(255,107,107,0.18), transparent 22%), radial-gradient(circle at bottom right, rgba(142,124,255,0.16), transparent 28%)",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Manrope'", "sans-serif"],
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-12px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulseBorder: {
          "0%, 100%": { opacity: "0.45" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        float: "float 7s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
        pulseBorder: "pulseBorder 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
