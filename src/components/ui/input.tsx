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
