'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Users,
  FileText,
  Package,
  Upload,
  ArrowRight,
  TrendingUp,
} from 'lucide-react'
import Link from 'next/link'
import type { OrgStats } from '@/lib/types'
import { api } from '@/lib/api'

export default function DashboardPage() {
  const [stats, setStats] = useState<OrgStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<OrgStats>('/api/organizations/stats')
      .then(setStats)
      .catch(() => {
        setStats({
          total_customers: 0,
          total_products: 0,
          total_documents: 0,
          total_pos: 0,
          total_bols: 0,
          total_packing_slips: 0,
        })
      })
      .finally(() => setLoading(false))
  }, [])

  const statCards = [
    { label: 'Customers', value: stats?.total_customers ?? 0, icon: Users, href: '/customers' },
    { label: 'Purchase Orders', value: stats?.total_pos ?? 0, icon: FileText, href: '/documents?type=PO' },
    { label: 'Bills of Lading', value: stats?.total_bols ?? 0, icon: FileText, href: '/documents?type=BOL' },
    { label: 'Packing Slips', value: stats?.total_packing_slips ?? 0, icon: Package, href: '/documents?type=PACKING_SLIP' },
  ]

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Overview of your logistics operations
          </p>
        </div>
        <Link href="/documents/upload">
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Upload PO
          </Button>
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <Link key={card.label} href={card.href}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {card.label}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {loading ? '—' : card.value}
                  </div>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/documents/upload" className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                <Upload className="h-5 w-5 text-primary" />
                <span className="font-medium">Upload Purchase Order</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
            <Link href="/customers/new" className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                <Users className="h-5 w-5 text-primary" />
                <span className="font-medium">Add New Customer</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
            <Link href="/organization" className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span className="font-medium">Manage Organization</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Pipeline Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Documents</span>
                <Badge variant="secondary">{loading ? '—' : stats?.total_documents ?? 0}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">POs Processed</span>
                <Badge variant="secondary">{loading ? '—' : stats?.total_pos ?? 0}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">BOLs Generated</span>
                <Badge variant="secondary">{loading ? '—' : stats?.total_bols ?? 0}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Packing Slips Generated</span>
                <Badge variant="secondary">{loading ? '—' : stats?.total_packing_slips ?? 0}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
