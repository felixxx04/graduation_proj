import { Link } from 'react-router-dom'
import { ShieldAlert, ArrowLeft } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function ForbiddenPage() {
  return (
    <div className="animate-fade-in max-w-2xl mx-auto">
      <Card hover="none" className="border-destructive/30">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-standard bg-destructive">
              <ShieldAlert className="h-5 w-5 text-destructive-foreground" />
            </div>
            <div>
              <CardTitle>无权限访问</CardTitle>
              <CardDescription>该页面仅管理员可进入</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <p className="text-ia-caption text-muted-foreground">
            请使用管理员账号登录后访问后台管理页面。
          </p>
          <Link to="/">
            <Button className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              返回首页
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
