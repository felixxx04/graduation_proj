import type { UserRole } from '@/lib/authStore'

export type AppFeature = 'patients' | 'privacy' | 'recommendation' | 'visualization' | 'admin'

export const FEATURE_LABEL: Record<AppFeature, string> = {
  patients: '患者档案',
  privacy: '隐私配置',
  recommendation: '用药推荐',
  visualization: '效果可视化',
  admin: '后台管理',
}

/**
 * 权限策略（前端 demo）：
 * - **普通用户**：以”使用推荐系统”为主 → 用药推荐 + 效果可视化
 * - **医生**：可管理患者 → 患者档案 + 用药推荐 + 效果可视化
 * - **管理员**：包含运维/管理能力 → 额外开放隐私配置、后台管理
 *
 * 后端接入后可改为从服务端下发权限/菜单。
 */
export const ROLE_FEATURES: Record<UserRole, AppFeature[]> = {
  user: ['recommendation', 'visualization'],
  doctor: ['patients', 'recommendation', 'visualization'],
  admin: ['patients', 'privacy', 'recommendation', 'visualization', 'admin'],
}

export function canAccessFeature(role: UserRole | undefined, feature: AppFeature) {
  if (!role) return false
  return ROLE_FEATURES[role].includes(feature)
}

