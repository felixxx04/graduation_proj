import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  prefix: '',
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        border: 'rgba(255,255,255,0.08)',
        input: 'rgba(255,255,255,0.10)',
        ring: 'rgba(14,165,233,0.40)',
        background: '#060f1e',
        foreground: '#f8fafc',
        primary: {
          DEFAULT: '#0ea5e9',
          foreground: '#ffffff',
          hover: '#38bdf8',
        },
        secondary: {
          DEFAULT: 'rgba(255,255,255,0.06)',
          foreground: '#cbd5e1',
        },
        destructive: {
          DEFAULT: '#ef4444',
          foreground: '#ffffff',
        },
        warning: {
          DEFAULT: '#f59e0b',
          foreground: '#0a1628',
        },
        success: {
          DEFAULT: '#22c55e',
          foreground: '#ffffff',
        },
        info: {
          DEFAULT: '#3b82f6',
          foreground: '#ffffff',
        },
        muted: {
          DEFAULT: '#0a1628',
          foreground: '#94a3b8',
        },
        accent: {
          DEFAULT: '#14b8a6',
          foreground: '#ffffff',
        },
        popover: {
          DEFAULT: '#0f2744',
          foreground: '#f8fafc',
        },
        card: {
          DEFAULT: '#0f2744',
          foreground: '#f8fafc',
        },
        surface: {
          base: '#060f1e',
          DEFAULT: '#0a1628',
          elevated: '#0f2744',
          overlay: '#132f4c',
        },
        brand: {
          sky: '#0ea5e9',
          teal: '#14b8a6',
          mint: '#5eead4',
          navy: '#0f2b4c',
        },
      },
      borderRadius: {
        none: '0px',
        xs: '4px',
        sm: '8px',
        DEFAULT: '10px',
        md: '10px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        full: '9999px',
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        xs: '0 1px 3px rgba(0,0,0,0.30)',
        sm: '0 4px 12px rgba(0,0,0,0.40)',
        md: '0 8px 24px rgba(0,0,0,0.50)',
        lg: '0 16px 40px rgba(0,0,0,0.60)',
        xl: '0 24px 56px rgba(0,0,0,0.70)',
        'glow-primary': '0 0 20px rgba(14,165,233,0.15)',
        'glow-teal': '0 0 20px rgba(20,184,166,0.12)',
        'glow-sm': '0 0 0 3px rgba(14,165,233,0.15)',
        'btn-primary': '0 2px 8px rgba(14,165,233,0.30)',
        'btn-primary-hover': '0 4px 16px rgba(14,165,233,0.45)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { transform: 'translateY(8px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'brand-pulse': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.25s ease-out forwards',
        'slide-up': 'slide-up 0.3s ease-out forwards',
        'brand-pulse': 'brand-pulse 2s ease-in-out infinite',
        shimmer: 'shimmer 1.5s infinite',
      },
      transitionDuration: {
        DEFAULT: '200ms',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
