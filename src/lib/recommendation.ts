import type { PrivacyConfig } from './privacy'
import { applyDpNoiseToScore } from './privacy'

export type PatientProfile = {
  age?: number
  gender?: '男' | '女'
  diseases: string[]
  symptomsText?: string
  allergies: string[]
  currentMedications: string[]
}

export type Drug = {
  id: string
  name: string
  category: string
  indications: string[]
  contraindications: string[]
  commonSideEffects: string[]
  interactionsWith: string[] // drug names / classes in plain text
  typicalDosage: string
  typicalFrequency: string
}

export type RecommendationItem = {
  id: string
  drugName: string
  category: string
  dosage: string
  frequency: string
  confidence: number
  score: number
  dpNoise?: number
  reason: string
  interactions: string[]
  sideEffects: string[]
  explanation: {
    features: { name: string; weight: number; contribution: number; note?: string }[]
    warnings: string[]
  }
}

const DRUGS: Drug[] = [
  {
    id: 'metformin_xr',
    name: '二甲双胍缓释片',
    category: '降糖药',
    indications: ['2 型糖尿病', '糖尿病'],
    contraindications: ['严重肾功能不全', '乳酸性酸中毒', '重度肝功能异常'],
    commonSideEffects: ['胃肠道反应', '乏力', '乳酸酸中毒（罕见）'],
    interactionsWith: ['造影剂', '酒精'],
    typicalDosage: '500mg',
    typicalFrequency: '每日 2 次，随餐服用',
  },
  {
    id: 'amlodipine',
    name: '氨氯地平',
    category: '降压药',
    indications: ['高血压', '冠心病'],
    contraindications: ['严重低血压', '对二氢吡啶类过敏'],
    commonSideEffects: ['外周水肿', '头痛', '面部潮红'],
    interactionsWith: ['葡萄柚汁'],
    typicalDosage: '5mg',
    typicalFrequency: '每日 1 次，晨服',
  },
  {
    id: 'atorvastatin',
    name: '阿托伐他汀',
    category: '降脂药',
    indications: ['高脂血症', '动脉粥样硬化', '冠心病'],
    contraindications: ['活动性肝病', '妊娠期'],
    commonSideEffects: ['肌痛', '肝功能异常', '消化不良'],
    interactionsWith: ['大环内酯类抗生素', '葡萄柚汁'],
    typicalDosage: '20mg',
    typicalFrequency: '每日 1 次，睡前服用',
  },
  {
    id: 'aspirin_ec',
    name: '阿司匹林肠溶片',
    category: '抗血小板药',
    indications: ['冠心病', '动脉粥样硬化', '缺血性卒中风险'],
    contraindications: ['活动性消化道出血', '阿司匹林过敏', '哮喘急性发作'],
    commonSideEffects: ['胃肠道出血风险', '皮疹', '胃痛'],
    interactionsWith: ['抗凝药', 'NSAIDs'],
    typicalDosage: '100mg',
    typicalFrequency: '每日 1 次',
  },
  {
    id: 'losartan',
    name: '氯沙坦钾片',
    category: '降压药',
    indications: ['高血压', '糖尿病肾病'],
    contraindications: ['妊娠期', '双侧肾动脉狭窄'],
    commonSideEffects: ['头晕', '乏力', '高钾血症（风险）'],
    interactionsWith: ['保钾利尿剂', '补钾制剂'],
    typicalDosage: '50mg',
    typicalFrequency: '每日 1 次',
  },
  {
    id: 'omeprazole',
    name: '奥美拉唑',
    category: '消化系统用药',
    indications: ['胃溃疡', '胃食管反流', '消化道出血风险'],
    contraindications: ['对质子泵抑制剂过敏'],
    commonSideEffects: ['腹泻', '腹痛', '头痛'],
    interactionsWith: ['氯吡格雷（相互作用争议）'],
    typicalDosage: '20mg',
    typicalFrequency: '每日 1 次，早餐前',
  },
]

function tokenizeList(s: string) {
  return s
    .split(/[，,、;；]/)
    .map((x) => x.trim())
    .filter(Boolean)
}

export function buildPatientProfile(raw: {
  age?: string
  gender?: string
  diseases?: string
  symptoms?: string
  allergies?: string
  currentMedications?: string
}): PatientProfile {
  const ageNum = raw.age ? Number(raw.age) : undefined
  return {
    age: Number.isFinite(ageNum) ? ageNum : undefined,
    gender: raw.gender === '女' ? '女' : raw.gender === '男' ? '男' : undefined,
    diseases: tokenizeList(raw.diseases ?? ''),
    symptomsText: raw.symptoms ?? '',
    allergies: tokenizeList(raw.allergies ?? ''),
    currentMedications: tokenizeList(raw.currentMedications ?? ''),
  }
}

function includesAny(haystack: string[], needles: string[]) {
  const hs = haystack.map((x) => x.toLowerCase())
  return needles.some((n) => hs.some((h) => h.includes(n.toLowerCase())))
}

function matchCount(haystack: string[], needles: string[]) {
  const hs = haystack.map((x) => x.toLowerCase())
  return needles.reduce((acc, n) => (hs.some((h) => h.includes(n.toLowerCase())) ? acc + 1 : acc), 0)
}

function softConfidence(scores: number[], score: number) {
  // Map score to a demo-friendly 70~98 range via softmax-ish normalization.
  const shifted = scores.map((s) => Math.exp((s - Math.max(...scores)) / 6))
  const sum = shifted.reduce((a, b) => a + b, 0) || 1
  const p = Math.exp((score - Math.max(...scores)) / 6) / sum
  const conf = 70 + 28 * Math.min(1, Math.max(0, p * 3.2))
  return Math.round(conf * 10) / 10
}

function scoreDrug(patient: PatientProfile, drug: Drug) {
  const features: RecommendationItem['explanation']['features'] = []
  const warnings: string[] = []

  // Indication match (primary signal)
  const indicationMatches = matchCount(patient.diseases, drug.indications)
  const indicationWeight = 3.2
  const indicationContribution = indicationMatches * indicationWeight
  features.push({
    name: '适应症匹配',
    weight: indicationWeight,
    contribution: indicationContribution,
    note: indicationMatches ? `匹配 ${indicationMatches} 项` : '未匹配',
  })

  // Chronic comorbidity coverage (secondary)
  const comorbidityWeight = 1.6
  const comorbidityContribution = includesAny(patient.diseases, ['冠心病', '动脉粥样硬化']) &&
    includesAny(drug.indications, ['冠心病', '动脉粥样硬化'])
    ? comorbidityWeight
    : 0
  features.push({
    name: '合并症覆盖',
    weight: comorbidityWeight,
    contribution: comorbidityContribution,
  })

  // Allergy / contraindication penalty (safety)
  const allergyPenaltyWeight = -6.5
  const allergyHit = includesAny(patient.allergies, [drug.name]) || includesAny(patient.allergies, ['阿司匹林']) && drug.name.includes('阿司匹林')
  const allergyPenalty = allergyHit ? allergyPenaltyWeight : 0
  if (allergyHit) warnings.push(`患者过敏史可能与「${drug.name}」相关`)
  features.push({
    name: '过敏风险',
    weight: allergyPenaltyWeight,
    contribution: allergyPenalty,
    note: allergyHit ? '命中' : '未命中',
  })

  const contraindicationPenaltyWeight = -4.0
  const contraindicationHit = includesAny(patient.diseases, drug.contraindications)
  const contraindicationPenalty = contraindicationHit ? contraindicationPenaltyWeight : 0
  if (contraindicationHit) warnings.push(`患者病情可能存在「${drug.name}」禁忌/慎用点`)
  features.push({
    name: '禁忌/慎用',
    weight: contraindicationPenaltyWeight,
    contribution: contraindicationPenalty,
    note: contraindicationHit ? '命中' : '未命中',
  })

  // Interaction penalty (current meds / common foods)
  const interactionPenaltyWeight = -2.4
  const interactionHit = includesAny(patient.currentMedications, drug.interactionsWith)
  const interactionPenalty = interactionHit ? interactionPenaltyWeight : 0
  if (interactionHit) warnings.push(`与当前用药/习惯可能存在相互作用：${drug.interactionsWith.join('、')}`)
  features.push({
    name: '相互作用风险',
    weight: interactionPenaltyWeight,
    contribution: interactionPenalty,
    note: interactionHit ? '存在风险' : '未发现明显风险',
  })

  // Age heuristic (demo)
  const ageWeight = 0.6
  const ageContribution = patient.age && patient.age >= 60 ? ageWeight : 0
  features.push({
    name: '年龄因素（老年用药）',
    weight: ageWeight,
    contribution: ageContribution,
    note: patient.age ? `${patient.age} 岁` : '未知',
  })

  const score = features.reduce((acc, f) => acc + f.contribution, 0)

  return { score, features, warnings }
}

export function recommendDrugs(input: {
  patient: PatientProfile
  topK?: number
  dp?: { enabled: boolean; config: PrivacyConfig }
}) {
  const { patient, topK = 4, dp } = input
  const raw = DRUGS.map((drug) => {
    const { score, features, warnings } = scoreDrug(patient, drug)
    const interactions: string[] = []
    if (includesAny(patient.currentMedications, drug.interactionsWith)) {
      interactions.push(`注意与 ${drug.interactionsWith.join('、')} 的相互作用风险`)
    } else if (drug.interactionsWith.length) {
      interactions.push(`一般注意：${drug.interactionsWith.join('、')}`)
    }
    return { drug, score, features, warnings, interactions }
  })

  const scores = raw.map((r) => r.score)
  const items = raw
    .map((r) => {
      let finalScore = r.score
      let dpNoise = 0
      if (dp?.enabled) {
        const noisy = applyDpNoiseToScore(r.score, dp.config)
        finalScore = noisy.noisy
        dpNoise = noisy.noise
      }

      const reasonCore =
        r.features
          .filter((f) => f.contribution !== 0)
          .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
          .slice(0, 3)
          .map((f) => `${f.name}${f.note ? `（${f.note}）` : ''}`)
          .join('、') || '综合患者特征与药物知识图谱特征'

      return {
        id: r.drug.id,
        drugName: r.drug.name,
        category: r.drug.category,
        dosage: r.drug.typicalDosage,
        frequency: r.drug.typicalFrequency,
        confidence: softConfidence(scores, r.score),
        score: finalScore,
        dpNoise: dp?.enabled ? dpNoise : undefined,
        reason: `模型关键依据：${reasonCore}。在「${dp?.enabled ? '差分隐私' : '非差分隐私'}」推理设置下生成。`,
        interactions: r.interactions,
        sideEffects: r.drug.commonSideEffects,
        explanation: {
          features: r.features,
          warnings: r.warnings,
        },
      } satisfies RecommendationItem
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)

  return { items }
}

