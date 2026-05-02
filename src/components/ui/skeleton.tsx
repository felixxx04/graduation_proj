interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`animate-brand-pulse rounded-sm bg-surface-elevated ${className}`} />
  )
}

export function PatientCardSkeleton() {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-surface-elevated p-6 shadow-xs">
      <div className="flex items-start gap-4">
        <Skeleton className="h-14 w-14 rounded-sm" />
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-6 w-20" />
          </div>
          <div className="flex gap-4">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-28" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-6 w-24" />
          </div>
        </div>
      </div>
    </div>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-surface-elevated p-5 shadow-xs">
      <Skeleton className="mb-3 h-10 w-10 rounded-sm" />
      <Skeleton className="h-8 w-16 mb-1" />
      <Skeleton className="h-4 w-20" />
    </div>
  )
}

export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
  return (
    <tr className="border-t border-white/[0.04]">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="p-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

export function FormFieldSkeleton() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-11 w-full rounded-sm" />
    </div>
  )
}
