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
  onSubmitReview: (decision: 'confirm' | 'modify' | 'reject', selectedDrug?: string, reason?: string) => void;
}

export default function ReviewPanel({ recommendationId: _recommendationId, diseaseCn, drugs, onSubmitReview }: ReviewPanelProps) {
  const [decision, setDecision] = useState<'confirm' | 'modify' | 'reject' | null>(null);
  const [selectedDrug, setSelectedDrug] = useState('');
  const [reason, setReason] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = () => {
    if (!decision) return;
    onSubmitReview(decision, selectedDrug || undefined, reason || undefined);
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
