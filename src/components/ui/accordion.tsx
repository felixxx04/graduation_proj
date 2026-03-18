import * as React from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AccordionContextValue {
  value: string | string[]
  setValue: React.Dispatch<React.SetStateAction<string | string[]>>
  type?: 'single' | 'multiple'
  collapsible?: boolean
}

const AccordionContext = React.createContext<AccordionContextValue | undefined>(undefined)

function useAccordion() {
  const context = React.useContext(AccordionContext)
  if (!context) {
    throw new Error('useAccordion must be used within an Accordion')
  }
  return context
}

interface AccordionProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: 'single' | 'multiple'
  collapsible?: boolean
  value?: string | string[]
  onValueChange?: (value: string | string[]) => void
}

const Accordion = React.forwardRef<HTMLDivElement, AccordionProps>(
  ({ className, type = 'single', collapsible, value: controlledValue, onValueChange, children, ...props }, ref) => {
    const [internalValue, setInternalValue] = React.useState<string | string[]>(type === 'single' ? '' : [])
    
    const isControlled = controlledValue !== undefined
    const value = isControlled ? controlledValue : internalValue
    const setValue: React.Dispatch<React.SetStateAction<string | string[]>> = React.useCallback(
      (next) => {
        if (isControlled) {
          const resolved = typeof next === 'function' ? next(value) : next
          onValueChange?.(resolved)
          return
        }
        setInternalValue(next)
      },
      [isControlled, onValueChange, setInternalValue, value]
    )

    return (
      <AccordionContext.Provider value={{ value, setValue, type, collapsible }}>
        <div ref={ref} className={cn('w-full', className)} {...props}>
          {children}
        </div>
      </AccordionContext.Provider>
    )
  }
)
Accordion.displayName = 'Accordion'

const AccordionItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    value: string
  }
>(({ className, value, ...props }, ref) => {
  const { value: contextValue } = useAccordion()
  const isOpen = Array.isArray(contextValue) 
    ? contextValue.includes(value)
    : contextValue === value

  return (
    <div
      ref={ref}
      className={cn('border-b border-border last:border-b-0', className)}
      data-state={isOpen ? 'open' : 'closed'}
      data-value={value}
      {...props}
    />
  )
})
AccordionItem.displayName = 'AccordionItem'

const AccordionTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, children, onClick, ...props }, ref) => {
  const { value, setValue, type, collapsible } = useAccordion()
  const itemValue = React.useMemo(() => {
    const parent = (ref as React.RefObject<HTMLButtonElement>)?.current?.closest('[data-value]')
    return parent?.getAttribute('data-value') || ''
  }, [ref])
  
  const isOpen = Array.isArray(value) 
    ? value.includes(itemValue)
    : value === itemValue

  const handleClick = React.useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    if (type === 'single') {
      if (collapsible && isOpen) {
        setValue('')
      } else {
        setValue(itemValue)
      }
    } else {
      const values = Array.isArray(value) ? value : []
      if (isOpen) {
        setValue(values.filter((v) => v !== itemValue))
      } else {
        setValue([...values, itemValue])
      }
    }
    onClick?.(e)
  }, [type, collapsible, isOpen, value, itemValue, setValue, onClick])

  return (
    <button
      ref={ref}
      className={cn(
        'flex flex-1 items-center justify-between py-4 font-medium transition-all hover:underline text-left w-full focus:outline-none',
        className
      )}
      onClick={handleClick}
      {...props}
    >
      {children}
      <ChevronDown className={cn('h-4 w-4 shrink-0 transition-transform duration-200', isOpen && 'rotate-180')} />
    </button>
  )
})
AccordionTrigger.displayName = 'AccordionTrigger'

const AccordionContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  const { value } = useAccordion()
  const itemValue = React.useMemo(() => {
    const parent = (ref as React.RefObject<HTMLDivElement>)?.current?.closest('[data-value]')
    return parent?.getAttribute('data-value') || ''
  }, [ref])
  
  const isOpen = Array.isArray(value) 
    ? value.includes(itemValue)
    : value === itemValue

  return (
    <div
      ref={ref}
      className={cn(
        'overflow-hidden text-sm transition-all',
        isOpen ? 'data-[state=open]:animate-accordion-down' : 'data-[state=closed]:animate-accordion-up',
        className
      )}
      data-state={isOpen ? 'open' : 'closed'}
      {...props}
    >
      <div className={cn('pb-4 pt-0', isOpen ? 'block' : 'hidden')}>
        {children}
      </div>
    </div>
  )
})
AccordionContent.displayName = 'AccordionContent'

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
