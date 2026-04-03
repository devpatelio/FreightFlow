'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Users,
  Users2,
  Building2,
  FileText,
  Upload,
  Settings,
  Key,
  FileCode,
  Layers,
  Workflow,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Customers', href: '/customers', icon: Users },
  { name: 'Organization', href: '/organization', icon: Building2 },
  { type: 'separator' as const, label: 'Documents' },
  { name: 'All Documents', href: '/documents', icon: FileText },
  { name: 'Upload PO', href: '/documents/upload', icon: Upload },
  { type: 'separator' as const, label: 'Configuration' },
  { name: 'Pipelines', href: '/pipelines', icon: Workflow },
  { name: 'Templates', href: '/templates', icon: FileCode },
  { name: 'Schemas', href: '/schemas', icon: Layers },
  { type: 'separator' as const, label: 'Settings' },
  { name: 'General', href: '/settings', icon: Settings },
  { name: 'API Keys', href: '/settings/keys', icon: Key },
  { name: 'Team', href: '/settings/team', icon: Users2 },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-background">
      <div className="flex h-16 items-center border-b px-6">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/logo.png" alt="FreightFlow" width={32} height={32} className="rounded-lg" />
          <span className="text-lg font-semibold tracking-tight">FreightFlow</span>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {navigation.map((item, i) => {
            if ('type' in item && item.type === 'separator') {
              return (
                <li key={i} className="pt-4 pb-1 px-3">
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {item.label}
                  </span>
                </li>
              )
            }

            if (!('href' in item)) return null

            const isActive = pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href))
            const Icon = item.icon

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.name}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}
