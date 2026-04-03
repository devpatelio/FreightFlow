'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Building2, MapPin, Plus, Save, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { SellerProfile, Address } from '@/lib/types'

const EMPTY_ADDRESS_FORM = {
  name: '', address_line: '', city: '', state: '', zip_code: '', country: 'USA',
  address_type: 'warehouse', phone: '', email: '', label: '',
}

export default function OrganizationPage() {
  const [profile, setProfile] = useState<SellerProfile | null>(null)
  const [addresses, setAddresses] = useState<Address[]>([])
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [loadingAddresses, setLoadingAddresses] = useState(true)
  const [saving, setSaving] = useState(false)
  const [addressDialogOpen, setAddressDialogOpen] = useState(false)

  const [profileForm, setProfileForm] = useState({
    company_name: '',
    display_name: '',
    default_salesperson: '',
    phone: '',
    email: '',
    context_text: '',
  })

  const [addressForm, setAddressForm] = useState({ ...EMPTY_ADDRESS_FORM })

  useEffect(() => {
    api.get<SellerProfile>('/api/sellers/default')
      .then(p => {
        setProfile(p)
        setProfileForm({
          company_name: p.company_name,
          display_name: p.display_name || '',
          default_salesperson: p.default_salesperson || '',
          phone: p.phone || '',
          email: p.email || '',
          context_text: p.context_text || '',
        })
      })
      .catch(() => setProfile(null))
      .finally(() => setLoadingProfile(false))

    api.get<Address[]>('/api/addresses')
      .then(list => setAddresses(list.filter(a => !a.customer_id)))
      .catch(() => setAddresses([]))
      .finally(() => setLoadingAddresses(false))
  }, [])

  async function handleSaveProfile() {
    setSaving(true)
    try {
      if (profile) {
        const updated = await api.patch<SellerProfile>(`/api/sellers/${profile.id}`, {
          ...profileForm,
          display_name: profileForm.display_name || undefined,
          default_salesperson: profileForm.default_salesperson || undefined,
          phone: profileForm.phone || undefined,
          email: profileForm.email || undefined,
          context_text: profileForm.context_text || undefined,
        })
        setProfile(updated)
      } else {
        const created = await api.post<SellerProfile>('/api/sellers', {
          ...profileForm,
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

  async function handleCreateAddress(e: React.FormEvent) {
    e.preventDefault()
    try {
      const created = await api.post<Address>('/api/addresses', {
        ...addressForm,
        phone: addressForm.phone || undefined,
        email: addressForm.email || undefined,
        label: addressForm.label || undefined,
      })
      setAddresses(prev => [...prev, created])
      setAddressDialogOpen(false)
      setAddressForm({ ...EMPTY_ADDRESS_FORM })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create address')
    }
  }

  async function handleDeleteAddress(id: string) {
    if (!confirm('Delete this address?')) return
    await api.delete(`/api/addresses/${id}`)
    setAddresses(prev => prev.filter(a => a.id !== id))
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Organization</h1>
        <p className="text-muted-foreground mt-1">
          Manage your company profile, warehouses, and office locations
        </p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList variant="line">
          <TabsTrigger value="profile">
            <Building2 className="h-4 w-4 mr-1.5" />
            Seller Profile
          </TabsTrigger>
          <TabsTrigger value="addresses">
            <MapPin className="h-4 w-4 mr-1.5" />
            Addresses
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-6">
          {loadingProfile ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : (
            <div className="max-w-3xl space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Building2 className="h-5 w-5" />
                    Company Information
                  </CardTitle>
                  <CardDescription>
                    Your organization&apos;s identity used in document generation and AI prompts
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="company_name">Company Name *</Label>
                      <Input
                        id="company_name"
                        value={profileForm.company_name}
                        onChange={e => setProfileForm(f => ({ ...f, company_name: e.target.value }))}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="display_name">Display Name</Label>
                      <Input
                        id="display_name"
                        placeholder="Shown on documents"
                        value={profileForm.display_name}
                        onChange={e => setProfileForm(f => ({ ...f, display_name: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="salesperson">Default Salesperson</Label>
                      <Input
                        id="salesperson"
                        value={profileForm.default_salesperson}
                        onChange={e => setProfileForm(f => ({ ...f, default_salesperson: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="phone">Phone</Label>
                      <Input
                        id="phone"
                        value={profileForm.phone}
                        onChange={e => setProfileForm(f => ({ ...f, phone: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        type="email"
                        value={profileForm.email}
                        onChange={e => setProfileForm(f => ({ ...f, email: e.target.value }))}
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
                    value={profileForm.context_text}
                    onChange={e => setProfileForm(f => ({ ...f, context_text: e.target.value }))}
                    rows={12}
                    className="font-mono text-sm"
                    placeholder="You are a logistics support assistant that fills out import logistics forms for [your company name]..."
                  />
                </CardContent>
              </Card>

              <div className="flex justify-end">
                <Button onClick={handleSaveProfile} disabled={saving || !profileForm.company_name}>
                  <Save className="mr-2 h-4 w-4" />
                  {saving ? 'Saving...' : 'Save Profile'}
                </Button>
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="addresses" className="mt-6">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Warehouses, offices, and other locations that appear on your shipping documents
              </p>
              <Button onClick={() => setAddressDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />Add Address
              </Button>
              <Dialog open={addressDialogOpen} onOpenChange={setAddressDialogOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>New Organization Address</DialogTitle>
                  </DialogHeader>
                  <AddressForm
                    form={addressForm}
                    setForm={setAddressForm}
                    onSubmit={handleCreateAddress}
                    submitLabel="Create Address"
                  />
                </DialogContent>
              </Dialog>
            </div>

            {loadingAddresses ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : addresses.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <MapPin className="mx-auto h-10 w-10 text-muted-foreground/40" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    No organization addresses yet. Add your first warehouse or office location.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {addresses.map(addr => (
                  <AddressCard key={addr.id} address={addr} onDelete={handleDeleteAddress} />
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function AddressCard({ address, onDelete }: { address: Address; onDelete: (id: string) => void }) {
  return (
    <div className="rounded-lg border p-4 relative group">
      <Button
        variant="ghost" size="icon"
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={() => onDelete(address.id)}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
      <div className="flex items-center gap-2 mb-2">
        <p className="font-medium">{address.name}</p>
        <Badge variant="outline" className="text-xs">{address.address_type}</Badge>
        {address.is_default && <Badge className="text-xs">Default</Badge>}
      </div>
      {address.label && <p className="text-xs text-muted-foreground mb-1">{address.label}</p>}
      <p className="text-sm text-muted-foreground">
        {address.address_line}<br />
        {address.city}, {address.state} {address.zip_code}<br />
        {address.country}
      </p>
    </div>
  )
}

function AddressForm({
  form,
  setForm,
  onSubmit,
  submitLabel,
}: {
  form: typeof EMPTY_ADDRESS_FORM
  setForm: React.Dispatch<React.SetStateAction<typeof EMPTY_ADDRESS_FORM>>
  onSubmit: (e: React.FormEvent) => void
  submitLabel: string
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Name *</Label>
          <Input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
        </div>
        <div className="space-y-2">
          <Label>Label</Label>
          <Input placeholder="e.g., US Warehouse" value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
        </div>
      </div>
      <div className="space-y-2">
        <Label>Street Address *</Label>
        <Input value={form.address_line} onChange={e => setForm(f => ({ ...f, address_line: e.target.value }))} required />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>City *</Label>
          <Input value={form.city} onChange={e => setForm(f => ({ ...f, city: e.target.value }))} required />
        </div>
        <div className="space-y-2">
          <Label>State *</Label>
          <Input value={form.state} onChange={e => setForm(f => ({ ...f, state: e.target.value }))} required />
        </div>
        <div className="space-y-2">
          <Label>ZIP *</Label>
          <Input value={form.zip_code} onChange={e => setForm(f => ({ ...f, zip_code: e.target.value }))} required />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Country</Label>
          <Input value={form.country} onChange={e => setForm(f => ({ ...f, country: e.target.value }))} />
        </div>
        <div className="space-y-2">
          <Label>Type</Label>
          <select
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            value={form.address_type}
            onChange={e => setForm(f => ({ ...f, address_type: e.target.value }))}
          >
            <option value="warehouse">Warehouse</option>
            <option value="office">Office</option>
            <option value="shipping">Shipping</option>
            <option value="billing">Billing</option>
          </select>
        </div>
      </div>
      <Button type="submit" className="w-full">{submitLabel}</Button>
    </form>
  )
}
