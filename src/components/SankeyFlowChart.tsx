import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts/core'
import { SankeyChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { api } from '@/lib/api'

echarts.use([SankeyChart, TooltipComponent, CanvasRenderer])

interface FlowNode { name: string }
interface FlowLink { source: number; target: number; value: number }
interface DiseaseItem { name: string; count: number }

interface FlowData {
  nodes: FlowNode[]
  links: FlowLink[]
  diseases: DiseaseItem[]
}

export default function SankeyFlowChart() {
  const chartRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<echarts.ECharts | null>(null)
  const [data, setData] = useState<FlowData | null>(null)
  const [selectedDiseases, setSelectedDiseases] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<FlowData>('/api/stats/recommendation-flow').then(d => {
      setData(d)
      const top5 = (d.diseases || []).slice(0, 5).map(x => x.name)
      setSelectedDiseases(new Set(top5))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!chartRef.current || !data) return
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, 'dark')
    }
    const chart = instanceRef.current

    // Filter nodes & links by selected diseases
    const selectedIndices = new Set<number>()
    const diseaseNames = new Set(selectedDiseases)
    const diseaseIdxMap = new Map<string, number>()
    data.nodes.forEach((n, i) => {
      const isInDiseaseList = data.diseases?.some(d => d.name === n.name)
      if (isInDiseaseList) diseaseIdxMap.set(n.name, i)
    })

    for (const link of data.links) {
      const srcName = data.nodes[link.source]?.name
      if (srcName && diseaseNames.has(srcName)) {
        selectedIndices.add(link.source)
        selectedIndices.add(link.target)
      }
    }

    // Build filtered nodes and index mapping
    const filteredNodes: FlowNode[] = []
    const remap = new Map<number, number>()
    const seen = new Set<string>()
    data.nodes.forEach((n, i) => {
      if (selectedIndices.has(i) && !seen.has(n.name)) {
        remap.set(i, filteredNodes.length)
        filteredNodes.push(n)
        seen.add(n.name)
      }
    })

    // Build filtered links
    const filteredLinks: FlowLink[] = []
    for (const link of data.links) {
      const srcName = data.nodes[link.source]?.name
      if (srcName && diseaseNames.has(srcName)) {
        const newSrc = remap.get(link.source)
        const newTgt = remap.get(link.target)
        if (newSrc != null && newTgt != null) {
          filteredLinks.push({ source: newSrc, target: newTgt, value: link.value })
        }
      }
    }

    chart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: '#0f1d32',
        borderColor: '#334155',
        textStyle: { color: '#e2e8f0', fontSize: 12 },
      },
      series: [{
        type: 'sankey',
        layout: 'none',
        emphasis: { focus: 'adjacency' },
        nodeAlign: 'left',
        nodeWidth: 14,
        nodeGap: 10,
        label: { color: '#cbd5e1', fontSize: 10 },
        lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.18 },
        data: filteredNodes,
        links: filteredLinks,
      }],
    }, true)

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)
    return () => { window.removeEventListener('resize', handleResize) }
  }, [data, selectedDiseases])

  const toggleDisease = (name: string) => {
    setSelectedDiseases(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const selectAll = () => setSelectedDiseases(new Set((data?.diseases || []).map(d => d.name)))
  const clearAll = () => setSelectedDiseases(new Set())

  if (loading) return <div className="h-[260px] flex items-center justify-center text-muted-foreground text-sm">加载流向数据...</div>

  return (
    <div>
      {/* Disease tag selector */}
      <div className="flex flex-wrap gap-1 mb-2 max-h-20 overflow-y-auto">
        <button onClick={selectAll} className="px-1.5 py-0.5 rounded text-[10px] bg-surface border border-white/[0.06] text-muted-foreground hover:text-brand-sky transition-colors">全选</button>
        <button onClick={clearAll} className="px-1.5 py-0.5 rounded text-[10px] bg-surface border border-white/[0.06] text-muted-foreground hover:text-red-400 transition-colors">全清</button>
        {(data?.diseases || []).map(d => (
          <button
            key={d.name}
            onClick={() => toggleDisease(d.name)}
            className="px-1.5 py-0.5 rounded text-[10px] transition-colors"
            style={{
              background: selectedDiseases.has(d.name) ? '#0c4a6e' : '#1e293b',
              color: selectedDiseases.has(d.name) ? '#38bdf8' : '#64748b',
              border: `1px solid ${selectedDiseases.has(d.name) ? '#0c4a6e' : '#334155'}`,
            }}
          >
            {d.name} ({d.count})
          </button>
        ))}
      </div>
      {/* Sankey chart */}
      <div ref={chartRef} style={{ width: '100%', height: 240 }} />
    </div>
  )
}
