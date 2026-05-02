/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00A3FF',
          container: '#00A3FF',
          dark: '#00629d',
        },
        neutral: {
          DEFAULT: '#09090B',
          rich: '#09090B',
        },
        surface: {
          DEFAULT: '#F8FAFC',
          container: '#eaeef6',
          bright: '#f7f9ff',
          dim: '#d6dae2',
        },
        secondary: '#292d32',
        tertiary: '#904d00',
        error: '#ba1a1a',
        'on-surface': '#171c22',
        'on-surface-variant': '#3f4852',
      },
      borderRadius: {
        'global': '16px',
        'card-lg': '20px',
      },
      fontFamily: {
        inter: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glass': '0 4px 20px rgba(59, 130, 246, 0.1)',
        'ambient': '0 2px 4px rgba(0,0,0,0.05)',
        'key': '0 10px 15px -3px rgba(0,0,0,0.1)',
        'penumbra': '0 4px 6px -2px rgba(0,0,0,0.05)',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      animation: {
        'pulse-skeleton': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
