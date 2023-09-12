/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {      
      colors: {
        primary: "#ffffff",
        secondary: "#161b22",
        tertiary: "#3344E0",
      }
    },
  },
  variants: {
    extend: {
      display: ["group-hover"],
    },
  },  
  plugins: [],
}
