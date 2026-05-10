import { useState } from 'react';

interface DrugOption {
  drugName: string;
  englishName: string;
  category: string;
  safetyType: string;
  score: number;
}

interface ReviewPanelProps {
  recommendationId: string;
  diseaseCn: string;
  drugs: DrugOption[];
  onSubmitReview: (decision: 'confirm' | 'modify' | 'reject', selectedDrug?: string, reason?: string, template?: string, advice?: string) => void;
}

export default function ReviewPanel({ recommendationId: _recommendationId, diseaseCn, drugs, onSubmitReview }: ReviewPanelProps) {
  const [decision, setDecision] = useState<'confirm' | 'modify' | 'reject' | null>(null);
  const [selectedDrug, setSelectedDrug] = useState('');
  const [reason, setReason] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const TREATMENT_TEMPLATES = [
    { name: '标准用法', text: '建议使用[药物名]，每日[N]次，每次[剂量]，连用[N]天。' },
    { name: '递增剂量', text: '起始剂量[小剂量]，根据耐受情况逐步调整至[目标剂量]。' },
    { name: '联合用药', text: '建议[药物A]联合[药物B]，注意监测[相互作用/不良反应]。' },
    { name: '对症治疗', text: '针对[症状]进行对症治疗，如症状持续或加重请及时复诊。' },
    { name: '自定义', text: '' },
  ];

  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [treatmentAdvice, setTreatmentAdvice] = useState('');

  const handleSubmit = () => {
    if (!decision) return;
    onSubmitReview(decision, selectedDrug || undefined, reason || undefined, selectedTemplate || undefined, treatmentAdvice || undefined);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="p-4 rounded-lg text-center" style={{ background: '#052e16' }}>
        <span style={{ color: '#4ade80', fontSize: '14px' }}>审核已提交</span>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl" style={{ background: '#1a1a2e', border: '1px solid #333', marginTop: '16px' }}>
      <h4 className="text-sm font-semibold mb-3" style={{ color: '#ccc' }}>
        医生审核确认{diseaseCn ? ` — ${diseaseCn}` : ''}
      </h4>

      <div className="flex gap-2 mb-3 flex-wrap">
        <button
          onClick={() => setDecision('confirm')}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: decision === 'confirm' ? '#166534' : '#0f172a',
            color: decision === 'confirm' ? '#4ade80' : '#888',
            border: `1px solid ${decision === 'confirm' ? '#4ade80' : '#333'}`,
          }}
        >
          确认推荐
        </button>
        <button
          onClick={() => setDecision('modify')}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: decision === 'modify' ? '#78350f' : '#0f172a',
            color: decision === 'modify' ? '#fbbf24' : '#888',
            border: `1px solid ${decision === 'modify' ? '#fbbf24' : '#333'}`,
          }}
        >
          修改选择
        </button>
        <button
          onClick={() => setDecision('reject')}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: decision === 'reject' ? '#7f1d1d' : '#0f172a',
            color: decision === 'reject' ? '#f87171' : '#888',
            border: `1px solid ${decision === 'reject' ? '#f87171' : '#333'}`,
          }}
        >
          拒绝
        </button>
      </div>

      {decision === 'modify' && (
        <div className="mb-3">
          <label className="block text-xs mb-1" style={{ color: '#888' }}>选择更合适的药物：</label>
          <select
            value={selectedDrug}
            onChange={e => setSelectedDrug(e.target.value)}
            className="w-full p-2 rounded-md text-sm"
            style={{ background: '#0f172a', color: '#ccc', border: '1px solid #333' }}
          >
            <option value="">-- 选择药物 --</option>
            {drugs.map(d => (
              <option key={d.englishName} value={d.englishName}>
                {d.drugName} ({d.category})
              </option>
            ))}
          </select>
        </div>
      )}

      {(decision === 'modify' || decision === 'reject') && (
        <div className="mb-3">
          <label className="block text-xs mb-1" style={{ color: '#888' }}>原因说明（可选）：</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="请输入审核意见..."
            rows={2}
            className="w-full p-2 rounded-md text-sm resize-y"
            style={{ background: '#0f172a', color: '#ccc', border: '1px solid #333' }}
          />
        </div>
      )}

      {decision && (
        <div className="mb-3">
          <label className="block text-xs mb-1" style={{ color: '#888' }}>诊疗建议模板（可选）：</label>
          <select
            value={selectedTemplate}
            onChange={e => { setSelectedTemplate(e.target.value); if (e.target.value && e.target.value !== '自定义') setTreatmentAdvice(TREATMENT_TEMPLATES.find(t => t.name === e.target.value)?.text || '') }}
            className="w-full p-2 rounded-md text-sm mb-2"
            style={{ background: '#0f172a', color: '#ccc', border: '1px solid #333' }}
          >
            <option value="">-- 选择模板 --</option>
            {TREATMENT_TEMPLATES.map(t => (
              <option key={t.name} value={t.name}>{t.name}</option>
            ))}
          </select>
          <label className="block text-xs mb-1" style={{ color: '#888' }}>诊疗建议（可编辑）：</label>
          <textarea
            value={treatmentAdvice}
            onChange={e => setTreatmentAdvice(e.target.value)}
            placeholder="请输入诊疗建议..."
            rows={3}
            className="w-full p-2 rounded-md text-sm resize-y"
            style={{ background: '#0f172a', color: '#ccc', border: '1px solid #333' }}
          />
        </div>
      )}

      {decision && (
        <button
          onClick={handleSubmit}
          className="w-full py-2.5 rounded-lg text-sm font-semibold text-white"
          style={{ background: '#2563eb' }}
        >
          提交审核
        </button>
      )}
    </div>
  );
}
