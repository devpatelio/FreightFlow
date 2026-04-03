'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Plus, Trash2, MapPin, Building2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { Address } from '@/lib/types'

export default function AddressesPage() {
  const [addresses, setAddresses] = useState<Address[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState({
    name: '', address_line: '', city: '', state: '', zip_code: '', country: 'USA',
    address_type: 'warehouse', phone: '', email: '', label: '',
  })

  useEffect(() => {
    api.get<Address[]>('/api/addresses')
      .then(setAddresses)
      .catch(() => setAddresses([]))
      .finally(() => setLoading(false))
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      const created = await api.post<Address>('/api/addresses', {
        ...form,
        phone: form.phone || undefined,
        email: form.email || undefined,
        label: form.label || undefined,
      })
      setAddresses(prev => [...prev, created])
      setDialogOpen(false)
      setForm({ name: '', address_line: '', city: '', state: '', zip_code: '', country: 'USA', address_type: 'warehouse', phone: '', email: '', label: '' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create address')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this address?')) return
    await api.delete(`/api/addresses/${id}`)
    setAddresses(prev => prev.filter(a => a.id !== id))
  }

  const orgAddresses = addresses.filter(a => !a.customer_id)
  const customerAddresses = addresses.filter(a => a.customer_id)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Addresses</h1>
          <p className="text-muted-foreground mt-1">Organization warehouses and customer shipping addresses</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />Add Address
        </Button>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New Address</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
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
              <Button type="submit" className="w-full">Create Address</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />Organization Addresses
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? <p className="text-muted-foreground">Loading...</p> : orgAddresses.length === 0 ? (
            <p className="text-muted-foreground text-sm">No organization addresses yet.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {orgAddresses.map(addr => (
                <div key={addr.id} className="rounded-lg border p-4 relative group">
                  <Button
                    variant="ghost" size="icon"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDelete(addr.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-medium">{addr.name}</p>
                    <Badge variant="outline" className="text-xs">{addr.address_type}</Badge>
                    {addr.is_default && <Badge className="text-xs">Default</Badge>}
                  </div>
                  {addr.label && <p className="text-xs text-muted-foreground mb-1">{addr.label}</p>}
                  <p className="text-sm text-muted-foreground">
                    {addr.address_line}<br />
                    {addr.city}, {addr.state} {addr.zip_code}<br />
                    {addr.country}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />Customer Addresses
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? <p className="text-muted-foreground">Loading...</p> : customerAddresses.length === 0 ? (
            <p className="text-muted-foreground text-sm">No customer addresses yet. Add them from customer detail pages.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {customerAddresses.map(addr => (
                <div key={addr.id} className="rounded-lg border p-4 relative group">
                  <Button
                    variant="ghost" size="icon"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDelete(addr.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-medium">{addr.name}</p>
                    <Badge variant="outline" className="text-xs">{addr.address_type}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {addr.address_line}<br />
                    {addr.city}, {addr.state} {addr.zip_code}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
