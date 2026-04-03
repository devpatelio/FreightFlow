'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Layers, Plus, Trash2, Pencil, Eye, Save, Maximize2 } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'

interface FormSchema {
  id: string
  template_name: string
  schema: unknown
  num_fields: number | null
  description: string | null
  created_at: string
  updated_at: string
}

export default function SchemasPage() {
  const [schemas, setSchemas] = useState<FormSchema[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [viewingSchema, setViewingSchema] = useState<FormSchema | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editJson, setEditJson] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [saving, setSaving] = useState(false)

  const [form, setForm] = useState({
    template_name: '',
    description: '',
    schema_json: '',
  })

  useEffect(() => {
    api.get<FormSchema[]>('/api/schemas')
      .then(setSchemas)
      .catch(() => setSchemas([]))
      .finally(() => setLoading(false))
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      JSON.parse(form.schema_json)
    } catch {
      alert('Schema must be valid JSON')
      return
    }
    try {
      const created = await api.post<FormSchema>('/api/schemas', {
        template_name: form.template_name,
        schema: JSON.parse(form.schema_json),
        description: form.description || undefined,
      })
      setSchemas(prev => [...prev, created])
      setCreateOpen(false)
      setForm({ template_name: '', description: '', schema_json: '' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create schema')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this schema?')) return
    await api.delete(`/api/schemas/${id}`)
    setSchemas(prev => prev.filter(s => s.id !== id))
    if (viewingSchema?.id === id) setViewingSchema(null)
  }

  function startEditing(schema: FormSchema) {
    setEditingId(schema.id)
    setEditJson(JSON.stringify(schema.schema, null, 2))
    setEditDescription(schema.description || '')
  }

  async function handleSaveEdit(id: string) {
    try {
      JSON.parse(editJson)
    } catch {
      alert('Schema must be valid JSON')
      return
    }
    setSaving(true)
    try {
      const updated = await api.patch<FormSchema>(`/api/schemas/${id}`, {
        schema: JSON.parse(editJson),
        description: editDescription,
      })
      setSchemas(prev => prev.map(s => s.id === id ? updated : s))
      setEditingId(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      try {
        JSON.parse(text)
        setForm(f => ({ ...f, schema_json: text }))
      } catch {
        alert('File is not valid JSON')
      }
    }
    reader.readAsText(file)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Form Schemas</h1>
          <p className="text-muted-foreground mt-1">
            Field schemas that define bounding boxes and metadata for PDF template filling
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />New Schema
        </Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : schemas.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Layers className="mx-auto h-10 w-10 text-muted-foreground/40" />
            <p className="mt-3 text-muted-foreground">No form schemas yet</p>
            <p className="text-sm text-muted-foreground mt-1">
              Schemas define the fields, bounding boxes, and types in your PDF templates.
            </p>
            <Button variant="outline" className="mt-4" onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />Create One
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {schemas.map(s => (
            <Card key={s.id}>
              <CardHeader className="flex flex-row items-start justify-between pb-3">
                <div className="space-y-1">
                  <CardTitle className="text-base font-mono">{s.template_name}</CardTitle>
                  {editingId !== s.id && s.description && (
                    <CardDescription className="text-xs">{s.description}</CardDescription>
                  )}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground pt-1">
                    <Badge variant="secondary">{s.num_fields ?? '?'} fields</Badge>
                    <span>·</span>
                    <span>Updated {new Date(s.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {editingId === s.id ? (
                    <>
                      <Button variant="ghost" size="sm" onClick={() => setEditingId(null)}>Cancel</Button>
                      <Button size="sm" onClick={() => handleSaveEdit(s.id)} disabled={saving}>
                        <Save className="mr-1.5 h-3.5 w-3.5" />
                        {saving ? 'Saving...' : 'Save'}
                      </Button>
                    </>
                  ) : (
                    <>
                      <Link href={`/schemas/${s.id}/edit`}>
                        <Button variant="ghost" size="icon" title="Visual Editor">
                          <Maximize2 className="h-4 w-4" />
                        </Button>
                      </Link>
                      <Button variant="ghost" size="icon" onClick={() => setViewingSchema(s)} title="View JSON">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => startEditing(s)} title="Edit JSON">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(s.id)} title="Delete">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              </CardHeader>
              {editingId === s.id && (
                <CardContent className="space-y-3 pt-0">
                  <div className="space-y-2">
                    <Label className="text-xs">Description</Label>
                    <Input value={editDescription} onChange={e => setEditDescription(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs">Schema JSON</Label>
                    <Textarea
                      value={editJson}
                      onChange={e => setEditJson(e.target.value)}
                      rows={14}
                      className="font-mono text-xs"
                    />
                  </div>
                </CardContent>
              )}
              {editingId !== s.id && (
                <CardContent className="pt-0">
                  <pre className="whitespace-pre-wrap text-xs font-mono text-muted-foreground line-clamp-3">
                    {typeof s.schema === 'string' ? s.schema : JSON.stringify(s.schema, null, 2)}
                  </pre>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>New Form Schema</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Template Name *</Label>
                <Input
                  placeholder="e.g., bol_standard"
                  value={form.template_name}
                  onChange={e => setForm(f => ({ ...f, template_name: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  placeholder="What document does this schema map to?"
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Schema JSON *</Label>
                <label className="text-xs text-primary cursor-pointer hover:underline">
                  Upload JSON file
                  <input type="file" accept=".json" className="hidden" onChange={handleFileUpload} />
                </label>
              </div>
              <Textarea
                placeholder={'[\n  {\n    "bbox": { "height": 0.016, "left": 0.169, "page": 1, "top": 0.202, "width": 0.198 },\n    "description": "SHIP TO - Name",\n    "type": "text",\n    "fill": true,\n    "value": null\n  }\n]'}
                value={form.schema_json}
                onChange={e => setForm(f => ({ ...f, schema_json: e.target.value }))}
                rows={12}
                className="font-mono text-xs"
                required
              />
              <p className="text-xs text-muted-foreground">
                Array of field objects with bbox, description, type, and fill properties.
              </p>
            </div>
            <Button type="submit" className="w-full">Create Schema</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!viewingSchema} onOpenChange={() => setViewingSchema(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="font-mono">{viewingSchema?.template_name}</DialogTitle>
          </DialogHeader>
          <pre className="whitespace-pre-wrap text-xs font-mono bg-muted/50 rounded-lg p-4 max-h-[65vh] overflow-y-auto">
            {viewingSchema ? JSON.stringify(viewingSchema.schema, null, 2) : ''}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  )
}
