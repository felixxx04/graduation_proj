# MediAI UI/UX Visual Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the frontend from Clinical IA (border-based, no-shadow, light teal) to MediAI dark medical-tech design (navy base, teal accent, glass nav, shadow depth, animated interactions).

**Architecture:** Deep-first design token rewrite (CSS variables + Tailwind config) flows into component layer (button/card/input/skeleton), then layout (glass nav), then page-by-page visual refresh. All pages share one dark theme via `:root` CSS custom properties. No light/dark toggle — dark is the only mode.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS 3.x, framer-motion (already installed)

---

## File Structure Map

| File | Responsibility |
|------|---------------|
| `tailwind.config.ts` | Colors, border-radius scale, shadow scale, font families, keyframes |
| `src/index.css` | CSS custom properties, base layer, component utility classes, animations |
| `src/components/ui/button.tsx` | Button variants: primary gradient, secondary ghost, outline, danger |
| `src/components/ui/card.tsx` | Card with shadow + hover lift + glow border |
| `src/components/ui/input.tsx` | Dark input with focus ring glow |
| `src/components/ui/skeleton.tsx` | Brand-colored pulse skeleton |
| `src/components/Layout.tsx` | Glass navbar with scroll detection, mobile drawer |
| `src/pages/HomePage.tsx` | Asymmetric hero + stats grid + features + CTA |
| `src/pages/DrugRecommendation.tsx` | Dark form + drug cards with rank colors |
| `src/pages/PatientRecords.tsx` | Dark table with zebra stripes + hover |
| `src/pages/LoginPage.tsx` | Dark login card |
| `src/App.tsx` | Page transition animations |

---

### Task 1: Rewrite Tailwind Config — Design Tokens

**Files:**
- Modify: `tailwind.config.ts`

**What:** Replace Clinical IA token system with MediAI dark theme tokens. Remove the serif font display classes, add real shadows, new border-radius scale, navy/teal color palette, new animations.

- [ ] **Step 1: Rewrite tailwind.config.ts**

```typescript
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
        /* Surface tokens */
        surface: {
          base: '#060f1e',
          DEFAULT: '#0a1628',
          elevated: '#0f2744',
          overlay: '#132f4c',
        },
        /* Brand data colors */
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
```

- [ ] **Step 2: Verify config compiles**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1 | head -5`
Expected: No new errors from config change (config is not type-checked by tsc, just validate syntax)

---

### Task 2: Rewrite index.css — CSS Variables & Base Layer

**Files:**
- Modify: `src/index.css`

**What:** Replace ALL existing CSS with new MediAI design system. This is a complete rewrite — remove Clinical IA border hierarchy, Playfair Display, HSL variables; add navy/teal hex colors, Inter font stack, real shadows.

- [ ] **Step 1: Write the new index.css**

```css
/* Import Inter + Noto Sans SC for Chinese support */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============================================
   MediAI Design System — Dark Medical Tech
   Navy Base · Teal Accent · Glass Depth
   ============================================ */

@layer base {
  :root {
    /* Background Hierarchy */
    --bg-base: #060f1e;
    --bg-surface: #0a1628;
    --bg-elevated: #0f2744;
    --bg-overlay: #132f4c;

    /* Brand */
    --brand-primary: #0ea5e9;
    --brand-primary-dark: #0284c7;
    --brand-accent: #14b8a6;
    --brand-accent-light: #5eead4;
    --brand-navy: #0f2b4c;

    /* Semantic */
    --semantic-success: #22c55e;
    --semantic-warning: #f59e0b;
    --semantic-danger: #ef4444;
    --semantic-info: #3b82f6;

    /* Text */
    --text-primary: #f8fafc;
    --text-secondary: #cbd5e1;
    --text-tertiary: #94a3b8;
    --text-disabled: #64748b;

    /* Border */
    --border-subtle: rgba(255,255,255,0.06);
    --border-default: rgba(255,255,255,0.10);
    --border-emphasis: rgba(14,165,233,0.20);
    --border-active: rgba(14,165,233,0.40);

    /* Shadows */
    --shadow-xs: 0 1px 3px rgba(0,0,0,0.30);
    --shadow-sm: 0 4px 12px rgba(0,0,0,0.40);
    --shadow-md: 0 8px 24px rgba(0,0,0,0.50);
    --shadow-lg: 0 16px 40px rgba(0,0,0,0.60);
    --shadow-glow-primary: 0 0 20px rgba(14,165,233,0.15);
    --shadow-glow-teal: 0 0 20px rgba(20,184,166,0.12);

    /* Radius */
    --radius-xs: 4px;
    --radius-sm: 8px;
    --radius-md: 10px;
    --radius-lg: 12px;
    --radius-xl: 16px;
    --radius-2xl: 24px;

    /* Typography Scale */
    --text-hero: clamp(2.25rem, 5vw, 3rem);
    --text-section: 1.375rem;
    --text-card-title: 1rem;
    --text-body: 0.9375rem;
    --text-caption: 0.8125rem;
    --text-micro: 0.6875rem;
  }

  * {
    border-color: var(--border-subtle);
  }

  html {
    scroll-behavior: smooth;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    background: var(--bg-base);
    color: var(--text-secondary);
    font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont,
                 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-feature-settings: "kern" 1, "liga" 1;
    line-height: 1.6;
  }

  /* Typography */
  h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary);
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
  }

  h1 { font-size: var(--text-hero); font-weight: 800; letter-spacing: -0.03em; }
  h2 { font-size: var(--text-section); }
  h3 { font-size: var(--text-card-title); font-weight: 600; }
  h4 { font-size: var(--text-card-title); }

  p {
    line-height: 1.65;
    color: var(--text-secondary);
  }

  a {
    color: var(--brand-primary);
    text-decoration: none;
    transition: color 0.2s ease;
  }

  a:hover {
    color: #38bdf8;
  }
}

/* ============================================
   Scrollbar — Dark Minimal
   ============================================ */

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }

::selection {
  background: rgba(14,165,233,0.25);
  color: var(--text-primary);
}

/* ============================================
   Focus Ring
   ============================================ */

:focus-visible {
  outline: 2px solid var(--brand-primary);
  outline-offset: 2px;
}

/* ============================================
   Container
   ============================================ */

@layer components {
  .container {
    width: 100%;
    margin-left: auto;
    margin-right: auto;
    padding-left: 1rem;
    padding-right: 1rem;
  }

  @media (min-width: 768px) {
    .container { max-width: 768px; padding-left: 1.5rem; padding-right: 1.5rem; }
  }
  @media (min-width: 1024px) {
    .container { max-width: 1024px; padding-left: 2rem; padding-right: 2rem; }
  }
  @media (min-width: 1280px) {
    .container { max-width: 1280px; }
  }
  @media (min-width: 1536px) {
    .container { max-width: 1400px; }
  }
}
```

---

### Task 3: Rewrite index.css — Component Classes & Animations

**Files:**
- Modify: `src/index.css` (append after container block)

**What:** Add component utility classes for cards, badges, data tables, progress bars, skeleton, sections, and all utility classes that pages reference.

- [ ] **Step 1: Append component classes to index.css**

Append to `src/index.css` after the container block (inside `@layer components`):

```css
/* ============================================
   Section Utilities
   ============================================ */

.section-dark {
  background: var(--bg-overlay);
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.section-dark p { color: var(--text-tertiary); }
.section-dark h1, .section-dark h2, .section-dark h3 { color: var(--text-primary); }

.section-light {
  background: var(--bg-surface);
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.section-base {
  background: var(--bg-base);
}

/* ============================================
   Card Base
   ============================================ */

.ia-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  transition: transform 0.2s ease-out, box-shadow 0.2s ease-out, border-color 0.2s ease-out;
}

.ia-card-hover:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-sm);
  border-color: var(--border-emphasis);
}

.ia-card-active {
  border-color: var(--border-active);
  box-shadow: var(--shadow-sm), var(--shadow-glow-teal);
}

.ia-card-dark {
  background: var(--bg-overlay);
  border-color: var(--border-subtle);
  color: var(--text-primary);
}

/* ============================================
   Badge / Tag
   ============================================ */

.ia-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  font-size: var(--text-micro);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid;
  border-radius: var(--radius-xs);
}

.ia-badge-primary {
  color: var(--brand-primary);
  border-color: rgba(14,165,233,0.30);
  background: rgba(14,165,233,0.10);
}

.ia-badge-success {
  color: var(--semantic-success);
  border-color: rgba(34,197,94,0.30);
  background: rgba(34,197,94,0.10);
}

.ia-badge-warning {
  color: var(--semantic-warning);
  border-color: rgba(245,158,11,0.30);
  background: rgba(245,158,11,0.10);
}

.ia-badge-danger {
  color: var(--semantic-danger);
  border-color: rgba(239,68,68,0.30);
  background: rgba(239,68,68,0.10);
}

.ia-badge-info {
  color: var(--semantic-info);
  border-color: rgba(59,130,246,0.30);
  background: rgba(59,130,246,0.10);
}

/* Solid badge variants for dark backgrounds */
.ia-badge-solid-primary {
  color: white;
  border-color: var(--brand-primary);
  background: var(--brand-primary);
}

.ia-badge-solid-teal {
  color: #0a1628;
  border-color: var(--brand-accent-light);
  background: var(--brand-accent-light);
}

/* ============================================
   Data Table
   ============================================ */

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-caption);
}

.data-table thead {
  border-bottom: 2px solid rgba(255,255,255,0.08);
  background: var(--bg-surface);
}

.data-table th {
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  font-size: var(--text-micro);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  color: var(--text-secondary);
}

.data-table tbody tr {
  transition: background-color 0.15s ease;
}

.data-table tbody tr:nth-child(even) {
  background: rgba(14,165,233,0.03);
}

.data-table tbody tr:hover {
  background: rgba(14,165,233,0.08);
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

/* ============================================
   Progress Bar
   ============================================ */

.progress-bar {
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.06);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-primary), var(--brand-accent));
  border-radius: 2px;
  transition: width 0.4s ease;
}

.progress-bar-fill-success { background: linear-gradient(90deg, #22c55e, #16a34a); }
.progress-bar-fill-warning { background: linear-gradient(90deg, #f59e0b, #d97706); }
.progress-bar-fill-danger { background: linear-gradient(90deg, #ef4444, #dc2626); }

/* ============================================
   Skeleton Loading
   ============================================ */

.skeleton {
  position: relative;
  overflow: hidden;
  background: linear-gradient(
    90deg,
    rgba(14,165,233,0.06),
    rgba(20,184,166,0.04),
    rgba(14,165,233,0.06)
  );
  border-radius: var(--radius-sm);
}

.skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent,
    rgba(14,165,233,0.08),
    transparent
  );
  animation: skeletonShimmer 1.5s infinite;
}

/* ============================================
   Glass Nav Panel
   ============================================ */

.glass-nav {
  background: rgba(10, 22, 40, 0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.glass-nav-solid {
  background: rgba(10, 22, 40, 0.96);
  border-bottom-color: rgba(255,255,255,0.10);
}

/* ============================================
   Gradient Text
   ============================================ */

.gradient-text {
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ============================================
   Hero Decorative Circles
   ============================================ */

.hero-circle {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.hero-circle-lg {
  border: 2px solid rgba(14,165,233,0.08);
}

.hero-circle-md {
  border: 1.5px solid rgba(20,184,166,0.06);
}

.hero-dot {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  background: rgba(14,165,233,0.2);
}
```

Add animations at the bottom (outside `@layer components`, in the main CSS):

```css
/* ============================================
   Animations
   ============================================ */

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUpStagger {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes skeletonShimmer {
  100% { transform: translateX(100%); }
}

@keyframes brandPulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

@keyframes countUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in { animation: fadeIn 0.25s ease-out forwards; }
.animate-slide-up { animation: slideUp 0.3s ease-out forwards; }
.animate-slide-up-stagger { animation: slideUpStagger 0.4s ease-out forwards; opacity: 0; }

/* ============================================
   Print Styles — Invert dark for printing
   ============================================ */

@media print {
  .no-print { display: none !important; }
  .print-area { break-inside: avoid; }
  body {
    background: white !important;
    color: #0f172a !important;
  }
  .ia-card, .glass-nav {
    background: white !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: none !important;
  }
  .glass-nav { backdrop-filter: none !important; }
  h1, h2, h3, h4 { color: #0f172a !important; }
  .gradient-text {
    background: none !important;
    -webkit-text-fill-color: #0ea5e9 !important;
  }
}

/* ============================================
   Responsive Utilities
   ============================================ */

@media (max-width: 640px) {
  .mobile-stack { flex-direction: column; }
  .mobile-full { width: 100%; }
  .mobile-hide { display: none; }
}

@media (min-width: 641px) {
  .desktop-hide { display: none; }
}

/* ============================================
   Accessibility
   ============================================ */

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

### Task 4: Update Button Component

**Files:**
- Modify: `src/components/ui/button.tsx`

**What:** Replace border-based flat buttons with gradient primary, ghost secondary, glow shadows, and scale transforms.

- [ ] **Step 1: Rewrite button.tsx**

```typescript
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold tracking-tight transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-sky/40 focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default:
          'bg-gradient-to-br from-brand-sky to-sky-600 text-white shadow-btn-primary hover:shadow-btn-primary-hover hover:scale-[1.02]',
        destructive:
          'bg-red-500/12 border border-red-500/20 text-red-400 hover:bg-red-500/20 hover:border-red-500/30',
        outline:
          'border border-white/10 bg-transparent text-secondary hover:bg-white/[0.06] hover:border-white/20 hover:text-primary',
        secondary:
          'bg-white/[0.06] text-secondary hover:bg-white/[0.10] hover:text-primary',
        ghost:
          'hover:bg-white/[0.06] hover:text-primary text-tertiary',
        link:
          'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-5 py-2',
        sm: 'h-8 rounded-sm px-3 text-xs',
        lg: 'h-12 rounded-lg px-6 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={loading || props.disabled}
        {...props}
      >
        {loading ? (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : children}
      </button>
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
```

Note: `brand-sky` and `sky-600` colors are defined in tailwind.config.ts. But actually, in Tailwind v3, custom colors in the config are available as `bg-{key}`. Since we defined `brand: { sky: '#0ea5e9', ... }`, the class would be `from-brand-sky`. And `sky-600` is a built-in Tailwind color (`#0284c7`). This should work.

But wait — the brand color keys like `sky` and `teal` will generate `brand-sky` and `brand-teal` class names. The Tailwind config has:
```js
brand: {
  sky: '#0ea5e9',
  teal: '#14b8a6',
  mint: '#5eead4',
  navy: '#0f2b4c',
}
```

So `from-brand-sky` and `to-sky-600` (standard Tailwind) will work.

- [ ] **Step 2: Verify build**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1`
Expected: No new TypeScript errors

---

### Task 5: Update Card Component

**Files:**
- Modify: `src/components/ui/card.tsx`

**What:** Replace border-hierarchy cards with shadow-based elevated cards + hover lift + glow border.

- [ ] **Step 1: Rewrite card.tsx**

```typescript
import * as React from 'react'
import { cn } from '@/lib/utils'

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { hover?: 'lift' | 'none' }
>(({ className, hover = 'lift', ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-lg border border-white/[0.06] bg-surface-elevated text-card-foreground shadow-xs',
      hover === 'lift' && 'transition-all duration-200 ease-out hover:-translate-y-1 hover:shadow-sm hover:border-brand-sky/15',
      hover === 'none' && '',
      className
    )}
    {...props}
  />
))
Card.displayName = 'Card'

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 p-5 border-b border-white/[0.04]', className)}
    {...props}
  />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('text-base font-semibold leading-none tracking-tight text-primary-foreground', className)}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-tertiary leading-relaxed', className)}
    {...props}
  />
))
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-5 pt-4', className)} {...props} />
))
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex items-center p-5 pt-0', className)} {...props} />
))
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
```

Note: `surface-elevated` maps to `--bg-elevated: #0f2744` from Tailwind config `surface: { elevated: '#0f2744' }` → generates `bg-surface-elevated`.

Wait, actually I need to check — `surface` has sub-keys `base`, `DEFAULT`, `elevated`, `overlay`. In Tailwind, `DEFAULT` maps to just `bg-surface`, and sub-keys map to `bg-surface-elevated`, etc. So `bg-surface-elevated` is correct.

Also `text-tertiary` — we defined `--text-tertiary: #94a3b8` but we don't have this as a Tailwind color key. Let me check... Actually, Tailwind's text colors come from the `colors` config. We don't have a `tertiary` key in `colors`. So `text-tertiary` won't work as a Tailwind utility.

I need to either:
1. Add `tertiary` as a color key in tailwind config
2. Use inline styles or CSS variables
3. Use `text-muted-foreground` which maps to `#94a3b8`

Actually, `text-muted-foreground` is `#94a3b8` from the `muted.foreground` key. So let me use that instead.

Let me also reconsider - we need `text-secondary` and `text-primary`. The foreground color is `#f8fafc` (text-primary). `secondary.foreground` is `#cbd5e1` (text-secondary). `muted.foreground` is `#94a3b8` (text-tertiary).

So:
- `text-foreground` = #f8fafc (primary text)
- `text-secondary-foreground` = #cbd5e1 (secondary text)  
- `text-muted-foreground` = #94a3b8 (tertiary text)

Let me fix the card component to use these standard Tailwind class names.

Let me also double-check: `brand-sky/15` for border on hover — this uses Tailwind's opacity modifier syntax which should work. `border-brand-sky/15` = border color brand-sky at 15% opacity.

OK, let me fix the card component:

```typescript
className={cn(
  'rounded-lg border border-white/[0.06] bg-surface-elevated text-card-foreground shadow-xs',
  hover === 'lift' && 'transition-all duration-200 ease-out hover:-translate-y-1 hover:shadow-sm hover:border-brand-sky/15',
  hover === 'none' && '',
  className
)}
```

`text-card-foreground` is `#f8fafc` from `card.foreground`. Good.

`text-base font-semibold leading-none tracking-tight text-foreground` for CardTitle - that works.

`text-sm text-muted-foreground leading-relaxed` for CardDescription - that works.

Alright, the plan is getting very long. Let me write it more efficiently for the remaining tasks, including the full code but being less verbose about step structure.

Actually, the writing-plans skill says each step should be detailed with exact code and commands. But given the massive scope here, let me group related steps within each task more efficiently.<｜end▁of▁thinking｜>

<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="Write">
<｜｜DSML｜｜parameter name="content" string="true"># MediAI UI/UX Visual Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the frontend from Clinical IA (border-based, no-shadow, light teal) to MediAI dark medical-tech design (navy base, teal accent, glass nav, shadow depth, animated interactions).

**Architecture:** Deep-first design token rewrite (CSS variables + Tailwind config) flows into component layer (button/card/input/skeleton), then layout (glass nav), then page-by-page visual refresh. All pages share one dark theme via `:root` CSS custom properties. No light/dark toggle.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS 3.x, framer-motion

**Source spec:** `docs/superpowers/specs/2026-05-03-medical-ui-redesign-design.md`

---

### Task 1: Foundation — Tailwind Config

**Files:**
- Modify: `tailwind.config.ts`

Replace Clinical IA token system with MediAI dark theme tokens.

- [ ] **Step 1: Rewrite tailwind.config.ts**

```typescript
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
```

---

### Task 2: Foundation — index.css (Complete Rewrite)

**Files:**
- Modify: `src/index.css`

Complete CSS rewrite. Remove all Clinical IA code. Add MediAI design tokens, base styles, component classes, animations.

- [ ] **Step 1: Write new index.css**

Write this complete file to `src/index.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============================================
   MediAI Design System — Dark Medical Tech
   Navy Base · Teal Accent · Glass Depth
   ============================================ */

@layer base {
  :root {
    --bg-base: #060f1e;
    --bg-surface: #0a1628;
    --bg-elevated: #0f2744;
    --bg-overlay: #132f4c;
    --text-primary: #f8fafc;
    --text-secondary: #cbd5e1;
    --text-tertiary: #94a3b8;
    --text-disabled: #64748b;
    --border-subtle: rgba(255,255,255,0.06);
    --border-default: rgba(255,255,255,0.10);
    --border-emphasis: rgba(14,165,233,0.20);
    --brand-primary: #0ea5e9;
    --brand-accent: #14b8a6;
    --shadow-xs: 0 1px 3px rgba(0,0,0,0.30);
    --shadow-sm: 0 4px 12px rgba(0,0,0,0.40);
    --shadow-md: 0 8px 24px rgba(0,0,0,0.50);
    --text-hero: clamp(2.25rem, 5vw, 3rem);
    --text-section: 1.375rem;
    --text-card-title: 1rem;
    --text-body: 0.9375rem;
    --text-caption: 0.8125rem;
    --text-micro: 0.6875rem;
    --radius-xs: 4px;
    --radius-sm: 8px;
    --radius-md: 10px;
    --radius-lg: 12px;
    --radius-xl: 16px;
    --radius-2xl: 24px;
  }

  * { border-color: var(--border-subtle); }

  html {
    scroll-behavior: smooth;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    background: var(--bg-base);
    color: var(--text-secondary);
    font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont,
                 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-feature-settings: "kern" 1, "liga" 1;
    line-height: 1.6;
  }

  h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary);
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
  }

  h1 { font-size: var(--text-hero); font-weight: 800; letter-spacing: -0.03em; }
  h2 { font-size: var(--text-section); }
  h3 { font-size: var(--text-card-title); font-weight: 600; }

  p { line-height: 1.65; color: var(--text-secondary); }

  a { color: var(--brand-primary); text-decoration: none; transition: color 0.2s ease; }
  a:hover { color: #38bdf8; }
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }
::selection { background: rgba(14,165,233,0.25); color: var(--text-primary); }
:focus-visible { outline: 2px solid var(--brand-primary); outline-offset: 2px; }

@layer components {
  .container {
    width: 100%;
    margin-left: auto;
    margin-right: auto;
    padding-left: 1rem;
    padding-right: 1rem;
  }

  @media (min-width: 768px) {
    .container { max-width: 768px; padding-left: 1.5rem; padding-right: 1.5rem; }
  }
  @media (min-width: 1024px) {
    .container { max-width: 1024px; padding-left: 2rem; padding-right: 2rem; }
  }
  @media (min-width: 1280px) {
    .container { max-width: 1280px; }
  }
  @media (min-width: 1536px) {
    .container { max-width: 1400px; }
  }

  /* Section Utilities */
  .section-dark {
    background: var(--bg-overlay);
    border-top: 1px solid var(--border-subtle);
    border-bottom: 1px solid var(--border-subtle);
  }
  .section-dark p { color: var(--text-tertiary); }
  .section-dark h1, .section-dark h2, .section-dark h3 { color: var(--text-primary); }
  .section-light {
    background: var(--bg-surface);
    border-top: 1px solid var(--border-subtle);
    border-bottom: 1px solid var(--border-subtle);
  }
  .section-base { background: var(--bg-base); }

  /* Card Base */
  .ia-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xs);
    transition: transform 0.2s ease-out, box-shadow 0.2s ease-out, border-color 0.2s ease-out;
  }
  .ia-card-hover:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-sm);
    border-color: var(--border-emphasis);
  }
  .ia-card-active {
    border-color: rgba(14,165,233,0.40);
    box-shadow: var(--shadow-sm), 0 0 20px rgba(20,184,166,0.12);
  }
  .ia-card-dark {
    background: var(--bg-overlay);
    border-color: var(--border-subtle);
    color: var(--text-primary);
  }

  /* Badge */
  .ia-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    font-size: var(--text-micro);
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: 1px solid;
    border-radius: var(--radius-xs);
  }
  .ia-badge-primary { color: var(--brand-primary); border-color: rgba(14,165,233,0.30); background: rgba(14,165,233,0.10); }
  .ia-badge-success { color: #22c55e; border-color: rgba(34,197,94,0.30); background: rgba(34,197,94,0.10); }
  .ia-badge-warning { color: #f59e0b; border-color: rgba(245,158,11,0.30); background: rgba(245,158,11,0.10); }
  .ia-badge-danger { color: #ef4444; border-color: rgba(239,68,68,0.30); background: rgba(239,68,68,0.10); }
  .ia-badge-info { color: #3b82f6; border-color: rgba(59,130,246,0.30); background: rgba(59,130,246,0.10); }

  /* Data Table */
  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--text-caption);
  }
  .data-table thead {
    border-bottom: 2px solid rgba(255,255,255,0.08);
    background: var(--bg-surface);
  }
  .data-table th {
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: var(--text-micro);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }
  .data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: var(--text-secondary);
  }
  .data-table tbody tr { transition: background-color 0.15s ease; }
  .data-table tbody tr:nth-child(even) { background: rgba(14,165,233,0.03); }
  .data-table tbody tr:hover { background: rgba(14,165,233,0.08); }
  .data-table tbody tr:last-child td { border-bottom: none; }

  /* Progress Bar */
  .progress-bar {
    width: 100%;
    height: 4px;
    background: rgba(255,255,255,0.06);
    border-radius: 2px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--brand-primary), var(--brand-accent));
    border-radius: 2px;
    transition: width 0.4s ease;
  }
  .progress-bar-fill-success { background: linear-gradient(90deg, #22c55e, #16a34a); }
  .progress-bar-fill-warning { background: linear-gradient(90deg, #f59e0b, #d97706); }
  .progress-bar-fill-danger { background: linear-gradient(90deg, #ef4444, #dc2626); }

  /* Skeleton */
  .skeleton {
    position: relative;
    overflow: hidden;
    background: linear-gradient(90deg, rgba(14,165,233,0.06), rgba(20,184,166,0.04), rgba(14,165,233,0.06));
    border-radius: var(--radius-sm);
  }
  .skeleton::after {
    content: '';
    position: absolute;
    inset: 0;
    transform: translateX(-100%);
    background: linear-gradient(90deg, transparent, rgba(14,165,233,0.08), transparent);
    animation: skeletonShimmer 1.5s infinite;
  }

  /* Gradient Text */
  .gradient-text {
    background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* Hero Decorations */
  .hero-circle {
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
  }
  .hero-circle-lg { border: 2px solid rgba(14,165,233,0.08); }
  .hero-circle-md { border: 1.5px solid rgba(20,184,166,0.06); }
  .hero-dot {
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
    background: rgba(14,165,233,0.2);
  }
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes skeletonShimmer {
  100% { transform: translateX(100%); }
}
.animate-fade-in { animation: fadeIn 0.25s ease-out forwards; }
.animate-slide-up { animation: slideUp 0.3s ease-out forwards; }

/* Print */
@media print {
  .no-print { display: none !important; }
  .print-area { break-inside: avoid; }
  body { background: white !important; color: #0f172a !important; }
  .ia-card { background: white !important; border: 1px solid #cbd5e1 !important; box-shadow: none !important; }
  h1, h2, h3, h4 { color: #0f172a !important; }
  .gradient-text { background: none !important; -webkit-text-fill-color: #0ea5e9 !important; }
}

/* Responsive */
@media (max-width: 640px) {
  .mobile-stack { flex-direction: column; }
  .mobile-full { width: 100%; }
  .mobile-hide { display: none; }
}
@media (min-width: 641px) {
  .desktop-hide { display: none; }
}

/* Accessibility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 2: Verify build**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1`
Expected: No new CSS-related TypeScript errors

---

### Task 3: Update UI Components (button, card, input, skeleton)

**Files:**
- Modify: `src/components/ui/button.tsx`
- Modify: `src/components/ui/card.tsx`
- Modify: `src/components/ui/input.tsx`
- Modify: `src/components/ui/skeleton.tsx`

- [ ] **Step 1: Rewrite button.tsx** — gradient primary + scale transforms + glow shadow

```typescript
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold tracking-tight transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-sky/40 focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default:
          'bg-gradient-to-br from-brand-sky to-sky-600 text-white shadow-btn-primary hover:shadow-btn-primary-hover hover:scale-[1.02]',
        destructive:
          'bg-red-500/12 border border-red-500/20 text-red-400 hover:bg-red-500/20 hover:border-red-500/30',
        outline:
          'border border-white/10 bg-transparent text-secondary-foreground hover:bg-white/[0.06] hover:border-white/20 hover:text-foreground',
        secondary:
          'bg-white/[0.06] text-secondary-foreground hover:bg-white/[0.10] hover:text-foreground',
        ghost:
          'hover:bg-white/[0.06] hover:text-foreground text-muted-foreground',
        link:
          'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-5 py-2',
        sm: 'h-8 rounded-sm px-3 text-xs',
        lg: 'h-12 rounded-lg px-6 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={loading || props.disabled}
        {...props}
      >
        {loading ? (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : children}
      </button>
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
```

- [ ] **Step 2: Rewrite card.tsx** — shadow-based cards + hover lift + glow border

```typescript
import * as React from 'react'
import { cn } from '@/lib/utils'

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { hover?: 'lift' | 'none' }
>(({ className, hover = 'lift', ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-lg border border-white/[0.06] bg-surface-elevated text-card-foreground shadow-xs',
      hover === 'lift' && 'transition-all duration-200 ease-out hover:-translate-y-1 hover:shadow-sm hover:border-brand-sky/15',
      hover === 'none' && '',
      className
    )}
    {...props}
  />
))
Card.displayName = 'Card'

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex flex-col space-y-1.5 p-5 border-b border-white/[0.04]', className)} {...props} />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3 ref={ref} className={cn('text-base font-semibold leading-none tracking-tight text-foreground', className)} {...props} />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm text-muted-foreground leading-relaxed', className)} {...props} />
))
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-5 pt-4', className)} {...props} />
))
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex items-center p-5 pt-0', className)} {...props} />
))
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
```

- [ ] **Step 3: Rewrite input.tsx** — dark bg + focus ring glow

```typescript
import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, icon, ...props }, ref) => {
    const classes = cn(
      'flex h-10 w-full rounded-sm border border-white/10 bg-surface px-3 py-2 text-sm text-secondary-foreground placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:border-brand-sky focus-visible:shadow-glow-sm disabled:cursor-not-allowed disabled:opacity-40 transition-all duration-150',
      className
    )

    if (icon) {
      return (
        <div className="relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{icon}</div>
          <input type={type} className={cn(classes, 'pl-10')} ref={ref} {...props} />
        </div>
      )
    }

    return <input type={type} className={classes} ref={ref} {...props} />
  }
)
Input.displayName = 'Input'

export { Input }
```

- [ ] **Step 4: Rewrite skeleton.tsx** — brand-colored shimmer

```typescript
interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`animate-brand-pulse rounded-sm bg-surface-elevated ${className}`} />
  )
}

export function PatientCardSkeleton() {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-surface-elevated p-6 shadow-xs">
      <div className="flex items-start gap-4">
        <Skeleton className="h-14 w-14 rounded-sm" />
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-6 w-20" />
          </div>
          <div className="flex gap-4">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-28" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-6 w-24" />
          </div>
        </div>
      </div>
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-surface-elevated p-5 shadow-xs">
      <Skeleton className="mb-3 h-10 w-10 rounded-sm" />
      <Skeleton className="h-8 w-16 mb-1" />
      <Skeleton className="h-4 w-20" />
    </div>
  )
}

export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
  return (
    <tr className="border-t border-white/[0.04]">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="p-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

export function FormFieldSkeleton() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-11 w-full rounded-sm" />
    </div>
  )
}
```

- [ ] **Step 5: Verify build after component changes**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1`
Expected: No TypeScript errors

---

### Task 4: Layout — Glass Navigation

**Files:**
- Modify: `src/components/Layout.tsx`

**What:** Replace solid border-based header with glass morphism navbar. Add scroll detection for background opacity transition. Keep the same login modal and mobile menu logic.

- [ ] **Step 1: Add scroll state and apply glass classes**

In `Layout.tsx`, add a scroll state hook and modify the `<header>` element:

Add after the existing `useState` declarations (around line 34):

```typescript
const [scrolled, setScrolled] = useState(false)

useEffect(() => {
  const handleScroll = () => setScrolled(window.scrollY > 10)
  window.addEventListener('scroll', handleScroll, { passive: true })
  return () => window.removeEventListener('scroll', handleScroll)
}, [])
```

Replace the `<header>` opening tag (line 105):

From:
```tsx
<header className="sticky top-0 z-50 w-full border-b border-ia-border bg-card/95">
```

To:
```tsx
<header
  className={cn(
    'sticky top-0 z-50 w-full backdrop-blur-xl transition-all duration-300',
    scrolled
      ? 'bg-[rgba(10,22,40,0.96)] border-b border-white/[0.10] shadow-sm'
      : 'bg-[rgba(10,22,40,0.85)] border-b border-white/[0.06]'
  )}
>
```

- [ ] **Step 2: Update navigation link pill styles**

The nav link classes reference `rounded-standard`, `bg-primary/8`, `border-ia-border` etc. Update to new design tokens. The active nav link currently uses:

```tsx
'bg-primary/8 text-primary border border-primary/20'
```

Change to:
```tsx
'bg-brand-sky/10 text-brand-sky border border-brand-sky/20'
```

And inactive link `text-muted-foreground hover:text-foreground hover:bg-muted` stays the same conceptually (these are Tailwind color keys that map to the new values).

- [ ] **Step 3: Update the Logo heart icon container style**

From:
```tsx
<div className="flex h-8 w-8 items-center justify-center rounded-standard bg-primary">
```

To:
```tsx
<div className="flex h-8 w-8 items-center justify-center rounded-sm bg-gradient-to-br from-brand-sky to-sky-600 shadow-btn-primary">
```

- [ ] **Step 4: Update footer style**

The footer currently has `border-t border-ia-border bg-card`. Change to:
```tsx
className="border-t border-white/[0.06] bg-surface"
```

- [ ] **Step 5: Verify build**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1`
Expected: No errors in Layout.tsx

---

### Task 5: HomePage Redesign

**Files:**
- Modify: `src/pages/HomePage.tsx`

**What:** Asymmetric hero with geometric decoration, gradient text, glass-morphism cards, dark CTA. Replace Clinical IA editorial layout entirely.

- [ ] **Step 1: Rewrite HomePage.tsx**

```typescript
import { Link } from 'react-router-dom'
import {
  Shield, Brain, Activity, Lock, ArrowRight,
  TrendingUp, Users, Stethoscope, BarChart3, Settings, Heart, Database,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/authStore'
import { canAccessFeature } from '@/lib/permissions'

const features = [
  { icon: Shield, title: '差分隐私保护', description: '采用先进的差分隐私技术，为患者医疗数据提供可证明的隐私保障', color: 'sky' as const },
  { icon: Brain, title: '深度学习推荐', description: '基于深度因子分解机模型，精准捕捉药物-疾病-患者之间的复杂关系', color: 'teal' as const },
  { icon: Activity, title: '个性化用药', description: '综合考虑患者个体差异、疾病特征、药物相互作用，提供定制化建议', color: 'sky' as const },
  { icon: Lock, title: '安全可控', description: '隐私预算可调、噪声机制可选，在隐私保护与推荐性能间实现最佳平衡', color: 'teal' as const },
]

const stats = [
  { label: '隐私保护等级', value: 'ε ≤ 1.0', icon: Shield, valueColor: 'text-brand-sky' },
  { label: '推荐准确率', value: '92%+', icon: TrendingUp, valueColor: 'text-brand-teal' },
  { label: '药物种类', value: '5,000+', icon: Database, valueColor: 'text-brand-sky' },
  { label: '服务患者', value: '10,000+', icon: Users, valueColor: 'text-brand-teal' },
]

const iconBgMap: Record<string, string> = {
  sky: 'bg-brand-sky/10',
  teal: 'bg-brand-teal/10',
}

const iconColorMap: Record<string, string> = {
  sky: 'text-brand-sky',
  teal: 'text-brand-teal',
}

export default function HomePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-20 pb-12">
      {/* Hero Section — Asymmetric split layout */}
      <section className="relative overflow-hidden rounded-xl bg-gradient-to-br from-background via-surface to-surface-elevated border border-white/[0.06]">
        {/* Geometric decorations */}
        <div className="hero-circle hero-circle-lg" style={{ top: -80, right: -40, width: 320, height: 320 }} />
        <div className="hero-circle hero-circle-md" style={{ bottom: -40, right: 120, width: 180, height: 180 }} />
        <div className="hero-dot" style={{ top: 60, right: 200, width: 8, height: 8 }} />
        <div className="hero-dot" style={{ bottom: 100, right: 80, width: 6, height: 6 }} />

        <div className="relative z-10 grid lg:grid-cols-2 gap-8 p-8 md:p-12 lg:p-16">
          {/* Left content */}
          <div className="flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-brand-sky/20 bg-brand-sky/8 text-xs text-brand-sky font-medium mb-6 w-fit">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-sky animate-brand-pulse" />
              AI-Powered Clinical Decision Support
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-[3rem] font-extrabold text-foreground mb-4 leading-[1.1] tracking-[-0.03em]">
              精准用药推荐<br />
              <span className="gradient-text">守护患者隐私</span>
            </h1>

            <p className="text-base text-muted-foreground max-w-lg mb-8 leading-relaxed">
              融合差分隐私技术与深度学习算法，在严格保护患者隐私的前提下，
              提供精准、安全、个性化的医疗用药推荐服务
            </p>

            <div className="flex flex-wrap gap-3">
              <Link to="/recommendation">
                <Button size="lg" className="gap-2">
                  开始用药推荐
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              {canAccessFeature(user?.role, 'visualization') && (
                <Link to="/visualization">
                  <Button variant="outline" size="lg" className="gap-2">
                    <BarChart3 className="h-4 w-4" />
                    效果可视化
                  </Button>
                </Link>
              )}
              {canAccessFeature(user?.role, 'admin') && (
                <Link to="/admin">
                  <Button variant="outline" size="lg" className="gap-2">
                    <Settings className="h-4 w-4" />
                    管理后台
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Right — Privacy budget visual */}
          <div className="flex items-center justify-center">
            <div className="w-52 h-64 rounded-xl border border-white/[0.08] bg-surface-elevated/50 flex flex-col items-center justify-center gap-3 shadow-sm">
              <div className="text-5xl font-extrabold text-brand-sky">ε</div>
              <div className="text-[10px] text-brand-teal tracking-[0.12em] uppercase font-semibold">Differential Privacy</div>
              <div className="w-20 h-px bg-gradient-to-r from-transparent via-brand-sky/30 to-transparent" />
              <div className="text-3xl font-bold text-foreground">≤ 1.0</div>
              <div className="text-xs text-muted-foreground">PRIVACY BUDGET</div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Row */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} className="group">
              <CardContent className="pt-5 pb-5">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-sm bg-surface">
                  <Icon className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
                </div>
                <div className={`text-2xl font-bold mb-0.5 ${stat.valueColor}`}>{stat.value}</div>
                <div className="text-xs text-muted-foreground font-medium">{stat.label}</div>
              </CardContent>
            </Card>
          )
        })}
      </section>

      {/* Features Grid */}
      <section className="space-y-8">
        <div className="max-w-2xl">
          <h2 className="text-2xl font-bold text-foreground mb-3">核心功能</h2>
          <p className="text-base text-muted-foreground">
            本系统结合医疗用药场景的数据特点与隐私保护需求，打造全方位的智能用药推荐解决方案
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <Card key={feature.title} className="group">
                <CardHeader>
                  <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-sm ${iconBgMap[feature.color]}`}>
                    <Icon className={`h-5 w-5 ${iconColorMap[feature.color]}`} />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription className="mt-1">{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            )
          })}
        </div>
      </section>

      {/* CTA Section */}
      <section className="rounded-xl bg-gradient-to-br from-surface-overlay to-surface-elevated border border-white/[0.06] px-8 py-14 md:px-14 md:py-16 text-center">
        <h2 className="text-2xl font-bold text-foreground mb-3">准备好开始了吗？</h2>
        <p className="text-base text-muted-foreground mb-8 max-w-lg mx-auto">
          体验隐私保护与智能推荐的完美结合，为医疗用药决策提供科学依据
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {canAccessFeature(user?.role, 'patients') && (
            <Link to="/patients">
              <Button size="lg" className="gap-2">
                <Users className="h-4 w-4" />
                管理患者档案
              </Button>
            </Link>
          )}
          <Link to="/recommendation">
            <Button variant="outline" size="lg" className="gap-2">
              <Stethoscope className="h-4 w-4" />
              获取用药推荐
            </Button>
          </Link>
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1`
Expected: No TypeScript errors

---

### Task 6: Page-by-Page Refresh

**Files:**
- Modify: `src/pages/DrugRecommendation.tsx`
- Modify: `src/pages/PatientRecords.tsx`
- Modify: `src/pages/LoginPage.tsx`

- [ ] **Step 1: Update DrugRecommendation.tsx** — drug card rank colors + dark form styling

In `DrugRecommendation.tsx`, find the drug result card rendering (the map over `topRecommendations`). Each drug card has a rank. Apply rank-based color coding:

```tsx
const rankColors: Record<number, { dot: string; tag: string }> = {
  0: { dot: 'bg-green-500', tag: 'text-brand-mint' },
  1: { dot: 'bg-brand-teal', tag: 'text-brand-teal' },
  2: { dot: 'bg-brand-sky', tag: 'text-brand-sky' },
  3: { dot: 'bg-amber-500', tag: 'text-amber-400' },
}
```

For each drug card, use the rank color for the rank indicator dot and category tag. Also update the card wrapper to use dark card styling:

```tsx
<div
  key={idx}
  className="rounded-lg border border-white/[0.06] bg-surface-elevated p-4 shadow-xs transition-all duration-200 hover:-translate-y-1 hover:shadow-sm hover:border-brand-sky/15"
>
```

The form section styling updates:
- Input fields already inherit from `Input` component changes
- Mode toggle pills: update active state to `bg-brand-sky/12 text-brand-sky border border-brand-sky/20 rounded-full`
- Submit section buttons: already use `<Button>` component

Update the DP/no-DP toggle pill button from `bg-primary/8` → `bg-brand-sky/10 text-brand-sky`.

- [ ] **Step 2: Update PatientRecords.tsx** — dark table + zebra stripes

Replace all `border-ia-border` references with `border-white/[0.06]` or `border-white/[0.04]`.
Replace `bg-card` with `bg-surface-elevated`.
Replace `text-foreground` → `text-foreground` (already maps to new value).
Replace `text-muted-foreground` → already correct.
Replace `bg-muted` → `bg-surface`.
Replace `rounded-standard` → `rounded-sm`.
Replace `bg-primary` → `bg-gradient-to-br from-brand-sky to-sky-600`.

For the table specifically, find the `<table>` elements and add `data-table` class. Existing inline table styles will be overridden by the new `.data-table` CSS.

- [ ] **Step 3: Update LoginPage.tsx** — dark card styling

Update classes:
- `border-ia-border` → `border-white/[0.06]`
- `bg-card` → `bg-surface-elevated`
- `rounded-standard` → `rounded-sm`
- `bg-primary` on shield icon → `bg-gradient-to-br from-brand-sky to-sky-600 shadow-btn-primary`
- `text-primary` links → `text-brand-sky`
- Footer text `text-muted-foreground` → already correct

- [ ] **Step 4: Update remaining pages**

For `PrivacyConfig.tsx`, `PrivacyVisualization.tsx`, `AdminDashboard.tsx`, `ForbiddenPage.tsx`:
- Global find-and-replace for common class patterns from old to new:
  - `border-ia-border` → `border-white/[0.06]`
  - `bg-card` → `bg-surface-elevated`
  - `rounded-standard` → `rounded-sm`
  - `bg-primary` (icon containers) → `bg-gradient-to-br from-brand-sky to-sky-600`
  - `bg-primary/8` (subtle backgrounds) → `bg-brand-sky/8`
  - `text-primary` (links/actions) → `text-brand-sky`
  - `border-primary/20` → `border-brand-sky/20`
  - `bg-muted` → `bg-surface`
  - `text-foreground` → keep (maps correctly)
  - `text-muted-foreground` → keep (maps correctly)

- [ ] **Step 5: Add page transitions in App.tsx**

```typescript
import { AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'

// Inside App component:
const location = useLocation()

// Wrap <Outlet /> in AnimatePresence (in Layout.tsx approach):
// Actually, Outlet is in Layout.tsx, not App.tsx. We can add page transitions
// in Layout.tsx by wrapping Outlet.
```

In `Layout.tsx`, wrap `<Outlet />`:

```tsx
import { AnimatePresence, motion } from 'framer-motion'

// Replace:
// <main className="container py-6"><Outlet /></main>

// With:
<main className="container py-6">
  <AnimatePresence mode="wait">
    <motion.div
      key={location.pathname}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      <Outlet />
    </motion.div>
  </AnimatePresence>
</main>
```

- [ ] **Step 6: Verify build**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1`
Expected: No TypeScript errors

---

### Task 7: Build, Verify & Polish

- [ ] **Step 1: Run TypeScript check**

Run: `cd D:/grad_medical && npx tsc --noEmit 2>&1`
Expected: Zero errors

- [ ] **Step 2: Start dev server and visually verify all pages**

Run:
```bash
cd D:/grad_medical && npm run dev
```

Navigate to each page and verify:
- `/` — HomePage: asymmetric hero, gradient text, stats cards with shadows
- `/login` — LoginPage: dark card, gradient shield icon
- `/recommendation` — DrugRecommendation: dark form, drug cards with rank colors
- `/patients` — PatientRecords: dark zebra-striped table
- `/privacy` — PrivacyConfig: dark theme applied
- `/visualization` — PrivacyVisualization: dark theme applied
- `/admin` — AdminDashboard: dark theme applied

- [ ] **Step 3: Verify interactions**

Check:
- Button hover: scale(1.02) + shadow increase (200ms)
- Button active: scale(0.98)
- Card hover: translateY(-3px) + border glow
- Input focus: teal border + ring glow
- Nav scroll: background transitions from transparent to solid

- [ ] **Step 4: Verify accessibility**

- Text contrast on dark backgrounds (WCAG AA ≥ 4.5:1)
- Focus visible rings on all interactive elements
- `prefers-reduced-motion` disables animations
- Print mode inverts dark backgrounds

- [ ] **Step 5: Commit**

```bash
git add tailwind.config.ts src/index.css src/components/ui/button.tsx src/components/ui/card.tsx src/components/ui/input.tsx src/components/ui/skeleton.tsx src/components/Layout.tsx src/pages/HomePage.tsx src/pages/DrugRecommendation.tsx src/pages/PatientRecords.tsx src/pages/LoginPage.tsx src/pages/PrivacyConfig.tsx src/pages/PrivacyVisualization.tsx src/pages/AdminDashboard.tsx src/pages/ForbiddenPage.tsx src/App.tsx
git commit -m "feat: MediAI dark medical-tech UI redesign

Complete visual overhaul from Clinical IA (border-based, light teal) to
MediAI dark theme (navy base, teal accent, glass nav, shadow depth).

- New design tokens: navy/teal palette, real shadows, system fonts
- Components: gradient buttons, shadow cards, focus glow inputs
- Layout: glass morphism navbar with scroll detection
- Pages: asymmetric hero, drug rank colors, dark zebra table
- Animations: page transitions, hover lift, brand shimmer
- Print styles, reduced-motion support, WCAG AA contrast"
```
