'use client'

import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Key, Users2, Building2, UserCircle, ArrowRight } from 'lucide-react'

const sections = [
  {
    href: '/settings/profile',
    icon: UserCircle,
    title: 'Your Profile',
    description: 'Display name and account details',
  },
  {
    href: '/settings/keys',
    icon: Key,
    title: 'API Keys',
    description: 'Manage OpenAI and Reducto API keys',
  },
  {
    href: '/seller',
    icon: Building2,
    title: 'Seller Profile',
    description: 'Company identity used in document generation',
  },
  {
    href: '/settings/team',
    icon: Users2,
    title: 'Team',
    description: 'Members, invitations, and roles',
  },
]

export default function SettingsPage() {
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your account and organization</p>
      </div>

      <div className="grid gap-4">
        {sections.map(s => (
          <Link key={s.href} href={s.href}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="flex items-center justify-between py-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <s.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">{s.title}</p>
                    <p className="text-sm text-muted-foreground">{s.description}</p>
                  </div>
                </div>
                <ArrowRight className="h-5 w-5 text-muted-foreground" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
