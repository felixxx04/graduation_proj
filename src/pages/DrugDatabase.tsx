import { useEffect, useState, useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import { Search, Pill, ChevronDown, ChevronUp } from 'lucide-react'

interface Drug {
  id: number
  name: string
  genericName: string
  category: string
  indications: any
  contraindications: any
  sideEffects: any
  interactions: any
  pregnancyCategory: string
  typicalDosage: string
  typicalFrequency: string
}

function parseList(val: any): string[] {
  if (!val) return []
  if (Array.isArray(val)) return val.map(v => typeof v === 'string' ? v : String(v))
  if (typeof val === 'string') { try { return JSON.parse(val) } catch { return [val] } }
  return []
}

export default function DrugDatabase() {
  const [drugs, setDrugs] = useState<Drug[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    api.get<Drug[]>('/api/drugs')
      .then(setDrugs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const categories = useMemo(() => [...new Set(drugs.map(d => d.category).filter(Boolean))].sort(), [drugs])

  const filtered = useMemo(() => drugs.filter(d => {
    if (search && !d.name.includes(search) && !(d.genericName || '').includes(search)) return false
    if (categoryFilter && d.category !== categoryFilter) return false
    return true
  }), [drugs, search, categoryFilter])

  if (loading) return <div className="p-8 text-center text-muted-foreground">加载药物数据...</div>

  return (
    <div className="space-y-6">
      <section className="border-l-4 border-l-primary bg-surface-elevated px-6 py-8">
        <div className="flex items-center gap-3">
          <Pill className="h-5 w-5 text-brand-sky" />
          <div>
            <h1 className="text-ia-tile font-display font-bold text-foreground">药物数据库</h1>
            <p className="text-ia-body text-muted-foreground mt-1">浏览系统支持的 {drugs.length} 种药物完整临床数据</p>
          </div>
        </div>
      </section>

      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索药物名称..." className="pl-9" />
        </div>
        <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
          className="h-10 rounded-sm border border-white/[0.06] bg-surface-elevated px-3 text-sm">
          <option value="">所有分类 ({categories.length})</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="text-sm text-muted-foreground">共 {filtered.length} 种药物</div>

      <div className="space-y-2">
        {filtered.slice(0, 100).map(drug => (
          <Card key={drug.id} hover="none">
            <CardContent className="p-4">
              <div className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedId(expandedId === drug.id ? null : drug.id)}>
                <div className="flex items-center gap-3">
                  <Pill className="h-4 w-4 text-brand-sky" />
                  <span className="font-heading font-semibold">{drug.name}</span>
                  {drug.genericName && <span className="text-xs text-muted-foreground">({drug.genericName})</span>}
                  <span className="ia-badge ia-badge-primary text-[10px]">{drug.category}</span>
                </div>
                {expandedId === drug.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </div>
              {expandedId === drug.id && (
                <div className="mt-3 pt-3 border-t border-white/[0.06] grid md:grid-cols-2 gap-3 text-sm">
                  <div><div className="text-muted-foreground text-xs mb-1">适应症</div>
                    <div className="flex flex-wrap gap-1">
                      {parseList(drug.indications).map((ind, i) => <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-brand-sky/10 text-brand-sky">{ind}</span>)}
                    </div>
                  </div>
                  <div><div className="text-muted-foreground text-xs mb-1">禁忌症</div>
                    <div className="flex flex-wrap gap-1">
                      {parseList(drug.contraindications).map((c, i) => <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">{c}</span>)}
                    </div>
                  </div>
                  <div><div className="text-muted-foreground text-xs mb-1">副作用</div>
                    <div className="flex flex-wrap gap-1">
                      {parseList(drug.sideEffects).slice(0, 10).map((se, i) => <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">{se}</span>)}
                    </div>
                  </div>
                  <div><div className="text-muted-foreground text-xs mb-1">其他信息</div>
                    <div className="text-xs space-y-0.5">
                      {drug.pregnancyCategory && <div>妊娠分级: {drug.pregnancyCategory}</div>}
                      {drug.typicalDosage && <div>常用剂量: {drug.typicalDosage}</div>}
                      {drug.typicalFrequency && <div>用药频率: {drug.typicalFrequency}</div>}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
