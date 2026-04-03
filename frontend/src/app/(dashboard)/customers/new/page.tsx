'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'

export default function NewCustomerPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    company_name: '',
    customer_code: '',
    default_payment_terms: 'NET 90 DAYS',
    default_delivery_terms: 'Free Carrier DESTINATION',
    notes: '',
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/api/customers', {
        ...form,
        customer_code: form.customer_code || undefined,
        notes: form.notes || undefined,
      })
      router.push('/customers')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create customer')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">New Customer</h1>
        <p className="text-muted-foreground mt-1">Add a new client company</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-4">
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
              <Label htmlFor="customer_code">Customer Code</Label>
              <Input
                id="customer_code"
                placeholder="e.g., SOL"
                value={form.customer_code}
                onChange={e => setForm(f => ({ ...f, customer_code: e.target.value }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="payment">Payment Terms</Label>
                <Input
                  id="payment"
                  value={form.default_payment_terms}
                  onChange={e => setForm(f => ({ ...f, default_payment_terms: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="delivery">Delivery Terms</Label>
                <Input
                  id="delivery"
                  value={form.default_delivery_terms}
                  onChange={e => setForm(f => ({ ...f, default_delivery_terms: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={form.notes}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                rows={3}
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button type="submit" disabled={loading}>
                {loading ? 'Creating...' : 'Create Customer'}
              </Button>
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
