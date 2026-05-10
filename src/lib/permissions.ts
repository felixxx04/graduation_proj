import type { UserRole } from '@/lib/authStore'

export type AppFeature =
  | 'recommendation'
  | 'my_records'
  | 'patients'
  | 'review'
  | 'drug_database'
  | 'recommendation_stats'
  | 'privacy'
  | 'admin'

export const FEATURE_LABEL: Record<AppFeature, string> = {
  recommendation: '用药推荐',
  my_records: '我的记录',
  patients: '患者档案',
  review: '推荐审核',
  drug_database: '药物数据库',
  recommendation_stats: '推荐统计',
  privacy: '隐私配置',
  admin: '后台管理',
}

export const ROLE_FEATURES: Record<UserRole, AppFeature[]> = {
  patient: ['recommendation', 'my_records'],
  doctor: ['patients', 'review'],
  admin: ['patients', 'review', 'drug_database', 'recommendation_stats', 'privacy', 'admin'],
}

export function canAccessFeature(role: UserRole | undefined, feature: AppFeature) {
  if (!role) return false
  return ROLE_FEATURES[role].includes(feature)
}
