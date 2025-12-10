/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'grok': {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#b9e6fe',
          300: '#7cd4fd',
          400: '#36bffa',
          500: '#0ca5eb',
          600: '#0086c9',
          700: '#016aa3',
          800: '#065986',
          900: '#0b4a6f',
          950: '#072f4a',
        },
        'x': {
          black: '#000000',
          white: '#ffffff',
          gray: {
            100: '#e7e9ea',
            200: '#cfd9de',
            300: '#b9c4cb',
            400: '#8899a6',
            500: '#71767b',
            600: '#536471',
            700: '#38444d',
            800: '#202327',
            900: '#16181c',
            950: '#0f1114',
          }
        }
      },
      fontFamily: {
        'display': ['Cal Sans', 'Inter', 'system-ui', 'sans-serif'],
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient': 'gradient 8s ease infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      },
      backgroundSize: {
        '300%': '300%',
      }
    },
  },
  plugins: [],
}

