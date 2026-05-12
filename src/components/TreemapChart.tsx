import { useEffect, useRef } from 'react'

interface TreemapData {
  name: string
  value: number
}

interface TreemapChartProps {
  data: TreemapData[]
  width?: number
  height?: number
}

const COLORS = ['#0284c7', '#16a34a', '#ca8a04', '#dc2626', '#7c3aed', '#db2777', '#0d9488']

export default function TreemapChart({ data, width = 400, height = 220 }: TreemapChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || data.length === 0) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = width + 'px'
    canvas.style.height = height + 'px'
    const ctx = canvas.getContext('2d')!
    ctx.scale(dpr, dpr)

    const total = data.reduce((s, d) => s + d.value, 0)
    if (total === 0) return

    // Simple squarified treemap layout
    const sorted = [...data].sort((a, b) => b.value - a.value)
    const pad = 3
    const items = sorted.map((d, i) => ({
      ...d,
      area: (d.value / total) * width * (height - 24),
      color: COLORS[i % COLORS.length],
    }))

    let x = 0, y = 0
    let row: typeof items = [], rowArea = 0

    for (const item of items) {
      row.push(item)
      rowArea += item.area
      // Layout a row
      const rh = rowArea / width
      let rx = x
      for (const ri of row) {
        const rw = ri.area / rh
        if (rw > 24 && rh > 20) {
          ctx.fillStyle = ri.color
          ctx.fillRect(rx + pad, y + pad, rw - pad * 2, rh - pad * 2)
          if (rw > 48 && rh > 28) {
            ctx.fillStyle = '#fff'
            ctx.font = '11px system-ui, -apple-system, sans-serif'
            ctx.textAlign = 'center'
            ctx.fillText(ri.name, rx + rw / 2, y + rh / 2 - 2)
            ctx.font = '9px system-ui, -apple-system, sans-serif'
            ctx.fillStyle = 'rgba(255,255,255,0.7)'
            ctx.fillText(String(ri.value), rx + rw / 2, y + rh / 2 + 10)
          }
        }
        rx += rw
      }
      y += rh
      row = []
      rowArea = 0
    }

    // Legend at bottom
    let lx = 4, ly = height - 18
    for (let i = 0; i < Math.min(sorted.length, 8); i++) {
      const d = sorted[i]
      ctx.fillStyle = COLORS[i % COLORS.length]
      ctx.fillRect(lx, ly, 8, 8)
      ctx.fillStyle = '#cbd5e1'
      ctx.font = '9px system-ui, -apple-system, sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(d.name + ' (' + d.value + ')', lx + 10, ly + 7)
      lx += ctx.measureText(d.name + ' (' + d.value + ')  ').width + 14
      if (lx > width - 50) break
    }
  }, [data, width, height])

  return <canvas ref={canvasRef} />
}
