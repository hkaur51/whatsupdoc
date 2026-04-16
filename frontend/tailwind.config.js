/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        plum: {
          50: "#F5F0EB",
          100: "#E8DDF0",
          300: "#c4b5d0",
          500: "#7a6389",
          700: "#4a3a55",
          900: "#3D1D5C",
        },
        ink: "#1a1a1a",
        wa: "#25D366",
      },
      fontFamily: {
        serif: ['Newsreader', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
