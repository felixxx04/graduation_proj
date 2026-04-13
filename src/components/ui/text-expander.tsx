import { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { measureText } from '@/lib/textMeasurement'
import { ChevronDown, ChevronUp } from 'lucide-react'

export interface TextExpanderProps {
  text: string
  maxLines?: number
  className?: string
  expandText?: string
  collapseText?: string
  width?: number
}

const DEFAULT_FONT = '14px Inter, system-ui, sans-serif'
const DEFAULT_LINE_HEIGHT = 22

export function TextExpander({
  text,
  maxLines = 3,
  className,
  expandText = '展开',
  collapseText = '收起',
  width,
}: TextExpanderProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [needsExpand, setNeedsExpand] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!text) {
      setNeedsExpand(false)
      return
    }

    // 使用容器宽度或传入的宽度
    const containerWidth = width || containerRef.current?.offsetWidth || 300

    const result = measureText({
      text,
      width: containerWidth,
      font: DEFAULT_FONT,
      lineHeight: DEFAULT_LINE_HEIGHT,
    })

    setNeedsExpand(result.lineCount > maxLines)
  }, [text, maxLines, width])

  if (!text) {
    return null
  }

  const maxHeight = isExpanded ? undefined : `${maxLines * DEFAULT_LINE_HEIGHT}px`

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <p
        className={cn(
          'text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap',
          !isExpanded && needsExpand && 'overflow-hidden'
        )}
        style={{ maxHeight }}
      >
        {text}
      </p>
      {needsExpand && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-1 flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
        >
          {isExpanded ? (
            <>
              <span>{collapseText}</span>
              <ChevronUp className="h-3 w-3" />
            </>
          ) : (
            <>
              <span>{expandText}</span>
              <ChevronDown className="h-3 w-3" />
            </>
          )}
        </button>
      )}
    </div>
  )
}
