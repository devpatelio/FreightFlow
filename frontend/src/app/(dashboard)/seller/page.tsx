'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Building2, Save } from 'lucide-react'
import { api } from '@/lib/api'
import type { SellerProfile } from '@/lib/types'

export default function SellerProfilePage() {
  const [profile, setProfile] = useState<SellerProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    company_name: '',
    display_name: '',
    default_salesperson: '',
    phone: '',
    email: '',
    context_text: '',
  })

  useEffect(() => {
    api.get<SellerProfile>('/api/sellers/default')
      .then(p => {
        setProfile(p)
        setForm({
          company_name: p.company_name,
          display_name: p.display_name || '',
          default_salesperson: p.default_salesperson || '',
          phone: p.phone || '',
          email: p.email || '',
          context_text: p.context_text || '',
        })
      })
      .catch(() => setProfile(null))
      .finally(() => setLoading(false))
  }, [])

  async function handleSave() {
    setSaving(true)
    try {
      if (profile) {
        const updated = await api.patch<SellerProfile>(`/api/sellers/${profile.id}`, {
          ...form,
          display_name: form.display_name || undefined,
          default_salesperson: form.default_salesperson || undefined,
          phone: form.phone || undefined,
          email: form.email || undefined,
          context_text: form.context_text || undefined,
        })
        setProfile(updated)
      } else {
        const created = await api.post<SellerProfile>('/api/sellers', {
          ...form,
          is_default: true,
        })
        setProfile(created)
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Seller Profile</h1>
        <p className="text-muted-foreground mt-1">
          Your organization&apos;s identity for document generation
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Company Information
          </CardTitle>
          <CardDescription>
            This data replaces the legacy HansonChemicals.txt file. It&apos;s used as context for AI prompts.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="company_name">Company Name *</Label>
              <Input
                id="company_name"
                value={form.company_name}
                onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="display_name">Display Name</Label>
              <Input
                id="display_name"
                placeholder="Shown on documents"
                value={form.display_name}
                onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="salesperson">Default Salesperson</Label>
              <Input
                id="salesperson"
                value={form.default_salesperson}
                onChange={e => setForm(f => ({ ...f, default_salesperson: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Context</CardTitle>
          <CardDescription>
            Free-form text prepended to all AI prompts. Tells the model who you are, your default addresses, and any instructions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={form.context_text}
            onChange={e => setForm(f => ({ ...f, context_text: e.target.value }))}
            rows={12}
            className="font-mono text-sm"
            placeholder="You are a logistics support assistant that fills out import logistics forms for [your company name]..."
          />
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving || !form.company_name}>
          <Save className="mr-2 h-4 w-4" />
          {saving ? 'Saving...' : 'Save Profile'}
        </Button>
      </div>
    </div>
  )
}
