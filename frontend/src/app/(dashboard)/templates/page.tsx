'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { FileCode, FileUp, Plus, Trash2, Pencil, Eye, Save, Upload } from 'lucide-react'
import { api } from '@/lib/api'

interface Template {
  id: string
  name: string
  template_type: 'prompt' | 'pdf'
  document_type: 'BOL' | 'PACKING_SLIP' | null
  content: string | null
  storage_path: string | null
  description: string | null
  linked_prompt_id: string | null
  version: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)

  const [promptDialogOpen, setPromptDialogOpen] = useState(false)
  const [promptForm, setPromptForm] = useState({ name: '', content: '', description: '' })

  const [pdfDialogOpen, setPdfDialogOpen] = useState(false)
  const [pdfForm, setPdfForm] = useState({ name: '', description: '', linked_prompt_id: '', document_type: '' as '' | 'BOL' | 'PACKING_SLIP' })
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [linkingId, setLinkingId] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [saving, setSaving] = useState(false)

  const [viewingTemplate, setViewingTemplate] = useState<Template | null>(null)

  useEffect(() => {
    api.get<Template[]>('/api/templates')
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false))
  }, [])

  const promptTemplates = templates.filter(t => t.template_type === 'prompt')
  const pdfTemplates = templates.filter(t => t.template_type === 'pdf')

  async function handleCreatePrompt(e: React.FormEvent) {
    e.preventDefault()
    try {
      const created = await api.post<Template>('/api/templates', {
        name: promptForm.name,
        template_type: 'prompt',
        content: promptForm.content,
        description: promptForm.description || undefined,
      })
      setTemplates(prev => [...prev, created])
      setPromptDialogOpen(false)
      setPromptForm({ name: '', content: '', description: '' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create template')
    }
  }

  async function handleUploadPdf(e: React.FormEvent) {
    e.preventDefault()
    if (!pdfFile) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', pdfFile)
      formData.append('name', pdfForm.name)
      if (pdfForm.description) formData.append('description', pdfForm.description)
      if (pdfForm.linked_prompt_id) formData.append('linked_prompt_id', pdfForm.linked_prompt_id)
      if (pdfForm.document_type) formData.append('document_type', pdfForm.document_type)

      const created = await api.upload<Template>('/api/templates/upload', formData)
      setTemplates(prev => [...prev, created])
      setPdfDialogOpen(false)
      setPdfForm({ name: '', description: '', linked_prompt_id: '', document_type: '' })
      setPdfFile(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to upload template')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this template?')) return
    await api.delete(`/api/templates/${id}`)
    setTemplates(prev => prev.filter(t => t.id !== id))
    if (viewingTemplate?.id === id) setViewingTemplate(null)
  }

  async function handleLinkPrompt(pdfId: string, promptId: string | null) {
    try {
      const updated = await api.patch<Template>(`/api/templates/${pdfId}`, {
        linked_prompt_id: promptId,
      })
      setTemplates(prev => prev.map(t => t.id === pdfId ? updated : t))
      setLinkingId(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to link prompt')
    }
  }

  async function handleSetDocumentType(templateId: string, docType: string | null) {
    try {
      const updated = await api.patch<Template>(`/api/templates/${templateId}`, {
        document_type: docType,
      })
      setTemplates(prev => prev.map(t => t.id === templateId ? updated : t))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update document type')
    }
  }

  function startEditing(template: Template) {
    setEditingId(template.id)
    setEditContent(template.content || '')
    setEditDescription(template.description || '')
  }

  async function handleSaveEdit(id: string) {
    setSaving(true)
    try {
      const updated = await api.patch<Template>(`/api/templates/${id}`, {
        content: editContent,
        description: editDescription,
      })
      setTemplates(prev => prev.map(t => t.id === id ? updated : t))
      setEditingId(null)
      if (viewingTemplate?.id === id) setViewingTemplate(updated)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Templates</h1>
          <p className="text-muted-foreground mt-1">
            AI prompt instructions and PDF files used by the document generation pipeline
          </p>
        </div>
      </div>

      <Tabs defaultValue="prompt">
        <TabsList variant="line">
          <TabsTrigger value="prompt">
            <FileCode className="h-4 w-4 mr-1.5" />
            Prompt Templates ({promptTemplates.length})
          </TabsTrigger>
          <TabsTrigger value="pdf">
            <FileUp className="h-4 w-4 mr-1.5" />
            PDF Templates ({pdfTemplates.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="prompt" className="mt-6">
          <div className="space-y-4">
            <div className="flex justify-end">
              <Button onClick={() => setPromptDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />New Prompt Template
              </Button>
            </div>
            {loading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : promptTemplates.length === 0 ? (
              <EmptyState
                message="No prompt templates yet"
                sub="Prompt templates are instruction sets that guide AI models when extracting and transforming data from purchase orders."
                actionLabel="Create Prompt Template"
                onAdd={() => setPromptDialogOpen(true)}
              />
            ) : (
              promptTemplates.map(t => (
                <PromptTemplateCard
                  key={t.id}
                  template={t}
                  isEditing={editingId === t.id}
                  editContent={editContent}
                  editDescription={editDescription}
                  saving={saving}
                  onEditContent={setEditContent}
                  onEditDescription={setEditDescription}
                  onStartEdit={() => startEditing(t)}
                  onSaveEdit={() => handleSaveEdit(t.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onDelete={() => handleDelete(t.id)}
                  onView={() => setViewingTemplate(t)}
                />
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="pdf" className="mt-6">
          <div className="space-y-4">
            <div className="flex justify-end">
              <Button onClick={() => setPdfDialogOpen(true)}>
                <Upload className="mr-2 h-4 w-4" />Upload PDF Template
              </Button>
            </div>
            {loading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : pdfTemplates.length === 0 ? (
              <EmptyState
                message="No PDF templates uploaded yet"
                sub="Upload the actual PDF files (BOL forms, Packing Slip forms, etc.) that the pipeline fills with extracted data via Reducto."
                actionLabel="Upload PDF Template"
                onAdd={() => setPdfDialogOpen(true)}
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {pdfTemplates.map(t => {
                  const linkedPrompt = t.linked_prompt_id
                    ? promptTemplates.find(p => p.id === t.linked_prompt_id)
                    : null
                  return (
                    <Card key={t.id} className="relative group">
                      <Button
                        variant="ghost" size="icon"
                        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => handleDelete(t.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                      <CardHeader className="pb-3">
                        <div className="flex items-center gap-2">
                          <FileUp className="h-5 w-5 text-muted-foreground" />
                          <CardTitle className="text-base">{t.name}</CardTitle>
                        </div>
                        {t.description && (
                          <CardDescription className="text-xs">{t.description}</CardDescription>
                        )}
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                          <Badge variant="outline">PDF</Badge>
                          <select
                            className="rounded border border-input bg-background px-1.5 py-0.5 text-xs font-medium"
                            value={t.document_type || ''}
                            onChange={e => handleSetDocumentType(t.id, e.target.value || null)}
                          >
                            <option value="">No type</option>
                            <option value="BOL">BOL</option>
                            <option value="PACKING_SLIP">Packing Slip</option>
                          </select>
                          <span>v{t.version}</span>
                          <span>·</span>
                          <span>Uploaded {new Date(t.created_at).toLocaleDateString()}</span>
                        </div>
                        {t.storage_path && (
                          <p className="text-xs text-muted-foreground truncate font-mono">
                            {t.storage_path.split('/').pop()}
                          </p>
                        )}
                        <div className="border-t pt-3">
                          <p className="text-xs font-medium mb-1.5">Linked Prompt</p>
                          {linkingId === t.id ? (
                            <select
                              className="w-full text-xs rounded-md border border-input bg-background px-2 py-1.5"
                              value={t.linked_prompt_id || ''}
                              onChange={(e) => handleLinkPrompt(t.id, e.target.value || null)}
                              onBlur={() => setLinkingId(null)}
                              autoFocus
                            >
                              <option value="">No prompt linked</option>
                              {promptTemplates.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                              ))}
                            </select>
                          ) : (
                            <button
                              onClick={() => setLinkingId(t.id)}
                              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                            >
                              <FileCode className="h-3.5 w-3.5" />
                              {linkedPrompt ? (
                                <span className="text-foreground font-medium">{linkedPrompt.name}</span>
                              ) : (
                                <span className="italic">Click to link a prompt template</span>
                              )}
                            </button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={promptDialogOpen} onOpenChange={setPromptDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Prompt Template</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreatePrompt} className="space-y-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                placeholder="e.g., BOL Data Extraction"
                value={promptForm.name}
                onChange={e => setPromptForm(f => ({ ...f, name: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                placeholder="When is this prompt used in the pipeline?"
                value={promptForm.description}
                onChange={e => setPromptForm(f => ({ ...f, description: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Content *</Label>
              <Textarea
                placeholder="You are a logistics assistant that extracts structured data from purchase orders..."
                value={promptForm.content}
                onChange={e => setPromptForm(f => ({ ...f, content: e.target.value }))}
                rows={10}
                className="font-mono text-sm"
                required
              />
            </div>
            <Button type="submit" className="w-full">Create Prompt Template</Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={pdfDialogOpen} onOpenChange={setPdfDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload PDF Template</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUploadPdf} className="space-y-4">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                placeholder="e.g., Standard Bill of Lading"
                value={pdfForm.name}
                onChange={e => setPdfForm(f => ({ ...f, name: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                placeholder="e.g., Blank BOL form used for domestic shipments"
                value={pdfForm.description}
                onChange={e => setPdfForm(f => ({ ...f, description: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Document Type *</Label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={pdfForm.document_type}
                onChange={e => setPdfForm(f => ({ ...f, document_type: e.target.value as '' | 'BOL' | 'PACKING_SLIP' }))}
                required
              >
                <option value="">Select type...</option>
                <option value="BOL">Bill of Lading</option>
                <option value="PACKING_SLIP">Packing Slip</option>
              </select>
              <p className="text-xs text-muted-foreground">
                Which document this PDF template produces during the fill step
              </p>
            </div>
            <div className="space-y-2">
              <Label>Linked Prompt Template</Label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={pdfForm.linked_prompt_id}
                onChange={e => setPdfForm(f => ({ ...f, linked_prompt_id: e.target.value }))}
              >
                <option value="">None (select later)</option>
                {promptTemplates.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                The prompt that guides AI extraction for documents filled with this PDF template
              </p>
            </div>
            <div className="space-y-2">
              <Label>PDF File *</Label>
              <div
                className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-8 cursor-pointer hover:border-muted-foreground/50 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                {pdfFile ? (
                  <div className="text-center">
                    <FileUp className="mx-auto h-8 w-8 text-primary mb-2" />
                    <p className="text-sm font-medium">{pdfFile.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {(pdfFile.size / 1024).toFixed(0)} KB
                    </p>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="mt-2"
                      onClick={(e) => { e.stopPropagation(); setPdfFile(null) }}
                    >
                      Remove
                    </Button>
                  </div>
                ) : (
                  <div className="text-center">
                    <Upload className="mx-auto h-8 w-8 text-muted-foreground/40 mb-2" />
                    <p className="text-sm text-muted-foreground">Click to select a PDF file</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      BOL form, Packing Slip form, or any document template
                    </p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={e => {
                    const file = e.target.files?.[0]
                    if (file) setPdfFile(file)
                  }}
                />
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={uploading || !pdfFile}>
              {uploading ? 'Uploading...' : 'Upload Template'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!viewingTemplate} onOpenChange={() => setViewingTemplate(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{viewingTemplate?.name}</DialogTitle>
          </DialogHeader>
          {viewingTemplate?.content && (
            <pre className="whitespace-pre-wrap text-sm font-mono bg-muted/50 rounded-lg p-4 max-h-[60vh] overflow-y-auto">
              {viewingTemplate.content}
            </pre>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function EmptyState({ message, sub, actionLabel, onAdd }: {
  message: string; sub: string; actionLabel: string; onAdd: () => void
}) {
  return (
    <Card>
      <CardContent className="py-12 text-center">
        <FileCode className="mx-auto h-10 w-10 text-muted-foreground/40" />
        <p className="mt-3 text-muted-foreground">{message}</p>
        <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">{sub}</p>
        <Button variant="outline" className="mt-4" onClick={onAdd}>
          <Plus className="mr-2 h-4 w-4" />{actionLabel}
        </Button>
      </CardContent>
    </Card>
  )
}

function PromptTemplateCard({
  template, isEditing, editContent, editDescription, saving,
  onEditContent, onEditDescription, onStartEdit, onSaveEdit, onCancelEdit, onDelete, onView,
}: {
  template: Template
  isEditing: boolean
  editContent: string
  editDescription: string
  saving: boolean
  onEditContent: (v: string) => void
  onEditDescription: (v: string) => void
  onStartEdit: () => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  onDelete: () => void
  onView: () => void
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div className="space-y-1">
          <CardTitle className="text-base">{template.name}</CardTitle>
          {!isEditing && template.description && (
            <CardDescription className="text-xs">{template.description}</CardDescription>
          )}
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-1">
            <Badge variant="outline">Prompt</Badge>
            <span>v{template.version}</span>
            <span>·</span>
            <span>Updated {new Date(template.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {isEditing ? (
            <>
              <Button variant="ghost" size="sm" onClick={onCancelEdit}>Cancel</Button>
              <Button size="sm" onClick={onSaveEdit} disabled={saving}>
                <Save className="mr-1.5 h-3.5 w-3.5" />
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="icon" onClick={onView}>
                <Eye className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={onStartEdit}>
                <Pencil className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={onDelete}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </CardHeader>
      {isEditing && (
        <CardContent className="space-y-3 pt-0">
          <div className="space-y-2">
            <Label className="text-xs">Description</Label>
            <Input
              value={editDescription}
              onChange={e => onEditDescription(e.target.value)}
              placeholder="Template description"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs">Content</Label>
            <Textarea
              value={editContent}
              onChange={e => onEditContent(e.target.value)}
              rows={12}
              className="font-mono text-sm"
            />
          </div>
        </CardContent>
      )}
      {!isEditing && template.content && (
        <CardContent className="pt-0">
          <pre className="whitespace-pre-wrap text-xs font-mono text-muted-foreground line-clamp-3">
            {template.content}
          </pre>
        </CardContent>
      )}
    </Card>
  )
}
