/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bcad: {
          50:  '#f3f6fa',
          100: '#e2eaf3',
          500: '#3a6fa5',
          700: '#1a3a5c',  // primary brand
          900: '#0f2238',
        },
        money: '#0a7c2a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
