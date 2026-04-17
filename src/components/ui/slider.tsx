import * as React from 'react'
import { cn } from '@/lib/utils'

export interface SliderProps {
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
  className?: string
  showTooltip?: boolean
}

const Slider = React.forwardRef<HTMLDivElement, SliderProps>(
  ({ value, min, max, step = 0.1, onChange, className, showTooltip = true }, ref) => {
    const percentage = ((value - min) / (max - min)) * 100

    return (
      <div ref={ref} className={cn('relative w-full', className)}>
        <div className="relative h-2 w-full">
          {/* Track */}
          <div className="absolute h-full w-full rounded-standard bg-muted" />

          {/* Progress */}
          <div
            className="absolute h-full rounded-standard bg-primary"
            style={{ width: `${percentage}%` }}
          />

          {/* Thumb */}
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="absolute w-full h-full opacity-0 cursor-pointer"
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-standard bg-card border-2 border-primary pointer-events-none transition-all duration-150"
            style={{ left: `calc(${percentage}% - 8px)` }}
          />
        </div>

        {/* Tooltip */}
        {showTooltip && (
          <div
            className="absolute -top-9 bg-primary text-primary-foreground text-ia-micro font-heading font-semibold px-2 py-0.5 rounded-standard"
            style={{ left: `calc(${percentage}% - 20px)` }}
          >
            {value.toFixed(2)}
          </div>
        )}

        {/* Min/Max labels */}
        <div className="flex justify-between mt-2 text-ia-micro text-ia-muted">
          <span>{min}</span>
          <span>{max}</span>
        </div>
      </div>
    )
  }
)
Slider.displayName = 'Slider'

export { Slider }
