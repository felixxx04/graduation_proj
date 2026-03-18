import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldAlert, ArrowLeft } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function ForbiddenPage() {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto">
      <Card className="border-destructive/20 bg-gradient-to-br from-destructive/5 to-warning/5 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-destructive to-warning flex items-center justify-center shadow-lg">
              <ShieldAlert className="h-6 w-6 text-white" />
            </div>
            <div>
              <CardTitle className="text-2xl">无权限访问</CardTitle>
              <CardDescription>该页面仅管理员可进入</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <p className="text-muted-foreground">
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
    </motion.div>
  )
}

