'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ArrowLeft, Plus, Trash2, FileText, Eye, ExternalLink } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Customer, Contact, Address, Document } from '@/lib/types'

const EMPTY_ADDRESS_FORM = {
  name: '', address_line: '', city: '', state: '', zip_code: '', country: 'USA',
  address_type: 'shipping' as string, label: '',
}

const EMPTY_CONTACT_FORM = {
  name: '', email: '', phone: '', role: '', is_primary: false,
}

export default function CustomerDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [customer, setCustomer] = useState<Customer | null>(null)
  const [contacts, setContacts] = useState<Contact[]>([])
  const [addresses, setAddresses] = useState<Address[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ company_name: '', customer_code: '', notes: '' })

  const [addressDialogOpen, setAddressDialogOpen] = useState(false)
  const [addressForm, setAddressForm] = useState({ ...EMPTY_ADDRESS_FORM })

  const [contactDialogOpen, setContactDialogOpen] = useState(false)
  const [contactForm, setContactForm] = useState({ ...EMPTY_CONTACT_FORM })

  useEffect(() => {
    Promise.all([
      api.get<Customer>(`/api/customers/${id}`),
      api.get<Contact[]>(`/api/customers/${id}/contacts`),
      api.get<Address[]>(`/api/addresses?customer_id=${id}`),
      api.get<Document[]>(`/api/documents?customer_id=${id}`),
    ])
      .then(([c, co, a, docs]) => {
        setCustomer(c)
        setContacts(co)
        setAddresses(a)
        setDocuments(docs)
        setForm({ company_name: c.company_name, customer_code: c.customer_code || '', notes: c.notes || '' })
      })
      .catch(() => router.push('/customers'))
      .finally(() => setLoading(false))
  }, [id, router])

  async function handleSave() {
    const updates: Record<string, string | undefined> = {}
    if (form.company_name !== customer?.company_name) updates.company_name = form.company_name
    if ((form.customer_code || null) !== customer?.customer_code) updates.customer_code = form.customer_code || undefined
    if ((form.notes || null) !== customer?.notes) updates.notes = form.notes || undefined

    if (Object.keys(updates).length > 0) {
      const updated = await api.patch<Customer>(`/api/customers/${id}`, updates)
      setCustomer(updated)
    }
    setEditing(false)
  }

  async function handleCreateAddress(e: React.FormEvent) {
    e.preventDefault()
    try {
      const created = await api.post<Address>('/api/addresses', {
        ...addressForm,
        customer_id: id,
        label: addressForm.label || undefined,
      })
      setAddresses(prev => [...prev, created])
      setAddressDialogOpen(false)
      setAddressForm({ ...EMPTY_ADDRESS_FORM })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create address')
    }
  }

  async function handleDeleteDoc(docId: string) {
    if (!confirm('Delete this document permanently?')) return
    try {
      await api.delete(`/api/documents/${docId}`)
      setDocuments(prev => prev.filter(d => d.id !== docId))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete document')
    }
  }

  async function handleDeleteAddress(addressId: string) {
    if (!confirm('Delete this address?')) return
    await api.delete(`/api/addresses/${addressId}`)
    setAddresses(prev => prev.filter(a => a.id !== addressId))
  }

  async function handleCreateContact(e: React.FormEvent) {
    e.preventDefault()
    try {
      const created = await api.post<Contact>(`/api/customers/${id}/contacts`, {
        ...contactForm,
        email: contactForm.email || undefined,
        phone: contactForm.phone || undefined,
        role: contactForm.role || undefined,
      })
      setContacts(prev => [...prev, created])
      setContactDialogOpen(false)
      setContactForm({ ...EMPTY_CONTACT_FORM })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create contact')
    }
  }

  async function handleDeleteContact(contactId: string) {
    if (!confirm('Delete this contact?')) return
    await api.delete(`/api/customers/${id}/contacts/${contactId}`)
    setContacts(prev => prev.filter(c => c.id !== contactId))
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>
  if (!customer) return <p className="text-muted-foreground">Customer not found</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/customers">
          <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold tracking-tight">{customer.company_name}</h1>
          {customer.customer_code && <Badge variant="secondary" className="mt-1">{customer.customer_code}</Badge>}
        </div>
        <Button variant="outline" onClick={() => setEditing(!editing)}>
          {editing ? 'Cancel' : 'Edit'}
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Details</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {editing ? (
              <>
                <div className="space-y-2">
                  <Label>Company Name</Label>
                  <Input value={form.company_name} onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>Customer Code</Label>
                  <Input value={form.customer_code} onChange={e => setForm(f => ({ ...f, customer_code: e.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={3} />
                </div>
                <Button onClick={handleSave}>Save Changes</Button>
              </>
            ) : (
              <>
                <div>
                  <p className="text-sm text-muted-foreground">Payment Terms</p>
                  <p>{customer.default_payment_terms}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Delivery Terms</p>
                  <p>{customer.default_delivery_terms}</p>
                </div>
                {customer.notes && (
                  <div>
                    <p className="text-sm text-muted-foreground">Notes</p>
                    <p>{customer.notes}</p>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Contacts</CardTitle>
            <Button variant="outline" size="sm" onClick={() => setContactDialogOpen(true)}>
              <Plus className="mr-1.5 h-3.5 w-3.5" />Add
            </Button>
          </CardHeader>
          <CardContent>
            {contacts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No contacts yet. Add one above.</p>
            ) : (
              <div className="space-y-3">
                {contacts.map(contact => (
                  <div key={contact.id} className="flex items-center justify-between rounded-lg border p-3 group">
                    <div>
                      <p className="font-medium">{contact.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {[contact.email, contact.phone, contact.role].filter(Boolean).join(' · ')}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {contact.is_primary && <Badge>Primary</Badge>}
                      <Button
                        variant="ghost" size="icon"
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => handleDeleteContact(contact.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Addresses</CardTitle>
          <Button variant="outline" size="sm" onClick={() => setAddressDialogOpen(true)}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />Add Address
          </Button>
        </CardHeader>
        <CardContent>
          {addresses.length === 0 ? (
            <p className="text-sm text-muted-foreground">No addresses yet. Add a shipping or billing address above.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {addresses.map(addr => (
                <div key={addr.id} className="rounded-lg border p-4 relative group">
                  <Button
                    variant="ghost" size="icon"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDeleteAddress(addr.id)}
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

      {/* Documents for this customer */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Documents</CardTitle>
          <Link href={`/documents/upload?customer_id=${id}`}>
            <Button variant="outline" size="sm">
              <Plus className="mr-1.5 h-3.5 w-3.5" />Upload PO
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="mx-auto h-10 w-10 text-muted-foreground/40" />
              <p className="mt-3 text-sm text-muted-foreground">No documents yet for this customer.</p>
              <Link href={`/documents/upload?customer_id=${id}`}>
                <Button variant="outline" size="sm" className="mt-3">
                  <Plus className="mr-1.5 h-3.5 w-3.5" />Upload a Purchase Order
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map(doc => (
                <div key={doc.id} className="flex items-center justify-between rounded-lg border p-3 group hover:bg-muted/50 transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{doc.document_name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Badge variant="outline" className="text-xs">{doc.document_type}</Badge>
                        <Badge className="text-xs">{doc.status}</Badge>
                        <span className="text-xs text-muted-foreground">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Link href={`/documents/${doc.id}/view`}>
                      <Button variant="ghost" size="icon" title="View PDF">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </Link>
                    {doc.document_type === 'PO' && (
                      <Link href={`/documents/${doc.id}/review`}>
                        <Button variant="ghost" size="icon" title="Pipeline">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </Link>
                    )}
                    <Button
                      variant="ghost" size="icon" title="Delete"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleDeleteDoc(doc.id)}
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={addressDialogOpen} onOpenChange={setAddressDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Address for {customer.company_name}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateAddress} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Name *</Label>
                <Input value={addressForm.name} onChange={e => setAddressForm(f => ({ ...f, name: e.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>Label</Label>
                <Input placeholder="e.g., Main Warehouse" value={addressForm.label} onChange={e => setAddressForm(f => ({ ...f, label: e.target.value }))} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Street Address *</Label>
              <Input value={addressForm.address_line} onChange={e => setAddressForm(f => ({ ...f, address_line: e.target.value }))} required />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>City *</Label>
                <Input value={addressForm.city} onChange={e => setAddressForm(f => ({ ...f, city: e.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>State *</Label>
                <Input value={addressForm.state} onChange={e => setAddressForm(f => ({ ...f, state: e.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>ZIP *</Label>
                <Input value={addressForm.zip_code} onChange={e => setAddressForm(f => ({ ...f, zip_code: e.target.value }))} required />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Country</Label>
                <Input value={addressForm.country} onChange={e => setAddressForm(f => ({ ...f, country: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={addressForm.address_type}
                  onChange={e => setAddressForm(f => ({ ...f, address_type: e.target.value }))}
                >
                  <option value="shipping">Shipping</option>
                  <option value="billing">Billing</option>
                  <option value="warehouse">Warehouse</option>
                  <option value="office">Office</option>
                </select>
              </div>
            </div>
            <Button type="submit" className="w-full">Create Address</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={contactDialogOpen} onOpenChange={setContactDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Contact for {customer.company_name}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateContact} className="space-y-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input value={contactForm.name} onChange={e => setContactForm(f => ({ ...f, name: e.target.value }))} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input type="email" value={contactForm.email} onChange={e => setContactForm(f => ({ ...f, email: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input value={contactForm.phone} onChange={e => setContactForm(f => ({ ...f, phone: e.target.value }))} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Role</Label>
                <Input placeholder="e.g., Purchasing Manager" value={contactForm.role} onChange={e => setContactForm(f => ({ ...f, role: e.target.value }))} />
              </div>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={contactForm.is_primary}
                    onChange={e => setContactForm(f => ({ ...f, is_primary: e.target.checked }))}
                    className="rounded"
                  />
                  Primary contact
                </label>
              </div>
            </div>
            <Button type="submit" className="w-full">Create Contact</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
