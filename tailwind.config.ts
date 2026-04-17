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
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
          hover: 'hsl(var(--primary-hover))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          foreground: 'hsl(var(--warning-foreground))',
        },
        info: {
          DEFAULT: 'hsl(var(--info))',
          foreground: 'hsl(var(--info-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        /* Clinical IA Data Colors */
        'ia-accent': 'hsl(var(--primary))',
        'ia-data-red': 'hsl(var(--destructive))',
        'ia-data-green': 'hsl(var(--success))',
        'ia-data-amber': 'hsl(var(--warning))',
        'ia-data-1': 'hsl(var(--ia-data-1))',
        'ia-data-2': 'hsl(var(--ia-data-2))',
        'ia-data-3': 'hsl(var(--ia-data-3))',
        'ia-data-4': 'hsl(var(--ia-data-4))',
        'ia-data-5': 'hsl(var(--ia-data-5))',
        'ia-border': 'hsl(var(--border))',
        'ia-muted': 'hsl(var(--muted))',
        'ia-black': 'hsl(175 60% 6%)',
      },
      borderRadius: {
        none: '0px',
        micro: '2px',
        standard: '3px',
        comfortable: '4px',
        large: '6px',
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 1px)',
        sm: '2px',
      },
      fontFamily: {
        display: ['Playfair Display', 'Noto Serif SC', 'serif'],
        heading: ['DM Sans', 'Noto Sans SC', 'sans-serif'],
        body: ['Inter', 'Noto Sans SC', 'sans-serif'],
        mono: ['Inter', 'monospace'],
      },
      boxShadow: {
        sm: 'none',
        md: 'none',
        lg: 'none',
        xl: 'none',
        glow: 'none',
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
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.2s ease-out',
        'slide-up': 'slide-up 0.25s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
