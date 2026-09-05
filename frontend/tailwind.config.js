/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Seashell = Main background (page bg, large sections, cards)
        seashell: {
          DEFAULT: "#FFF4EB",
          muted: "#F7EAD9",
        },
        // Wheat = Secondary background / highlight (feature cards, badges)
        wheat: {
          DEFAULT: "#F6E0B6",
          dark: "#E4CA97",
        },
        // Powder Blue = Muted UI / secondary elements (inputs, inactive states, subtle panels)
        powderBlue: {
          DEFAULT: "#A6BCC9",
          dark: "#849EAF",
        },
        // French Blue = Primary accent / action (buttons, links, active states, icons)
        frenchBlue: {
          DEFAULT: "#3E4B8E",
          hover: "#4E5DAA",
          dark: "#2F396E",
        },
        // Midnight Violet = Primary dark / text (headings, navbar, footer, strong text)
        midnight: {
          DEFAULT: "#3D1534",
          light: "#5A2050",
          dark: "#2A0E24",
          card: "#4A1A40",
        },
      },
      borderRadius: {
        xl: "12px",
        "2xl": "16px",
        "3xl": "24px",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
