'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  ArrowLeft, Save, Plus, Trash2, Loader2, Eye, EyeOff,
  ChevronLeft, ChevronRight,
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'

interface SchemaField {
  bbox: {
    height: number
    left: number
    page: number
    top: number
    width: number
    original_page?: number
  }
  description: string
  type: string
  fill: boolean
  value: string | null
}

interface FormSchema {
  id: string
  template_name: string
  schema: SchemaField[]
  num_fields: number | null
  description: string | null
  pdf_url: string | null
  created_at: string
  updated_at: string
}

type DragMode = null | 'move' | 'resize-br' | 'resize-bl' | 'resize-tr' | 'resize-tl' | 'draw'

export default function SchemaEditorPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [schema, setSchema] = useState<FormSchema | null>(null)
  const [fields, setFields] = useState<SchemaField[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [drawMode, setDrawMode] = useState(false)
  const [hiddenFields, setHiddenFields] = useState<Set<number>>(new Set())

  const [zoom, setZoom] = useState(1)
  const containerRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  const dragRef = useRef<{
    mode: DragMode
    fieldIdx: number
    startX: number
    startY: number
    startBbox: SchemaField['bbox']
  } | null>(null)

  const drawRef = useRef<{
    startX: number
    startY: number
    currentX: number
    currentY: number
  } | null>(null)

  const [drawRect, setDrawRect] = useState<{ left: number; top: number; width: number; height: number } | null>(null)

  const totalPages = fields.length > 0
    ? Math.max(...fields.map(f => f.bbox.page))
    : 1

  const pageFields = fields
    .map((f, i) => ({ field: f, idx: i }))
    .filter(({ field }) => field.bbox.page === currentPage)

  const noneVisible = pageFields.length > 0 && pageFields.every(({ idx }) => hiddenFields.has(idx))

  const toggleFieldVisibility = useCallback((idx: number) => {
    setHiddenFields(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }, [])

  const toggleAllVisibility = useCallback(() => {
    setHiddenFields(prev => {
      const allPageIdxs = pageFields.map(pf => pf.idx)
      const allHidden = allPageIdxs.every(i => prev.has(i))
      const next = new Set(prev)
      if (allHidden) {
        allPageIdxs.forEach(i => next.delete(i))
      } else {
        allPageIdxs.forEach(i => next.add(i))
      }
      return next
    })
  }, [pageFields])

  useEffect(() => {
    api.get<FormSchema>(`/api/schemas/${id}`)
      .then(data => {
        setSchema(data)
        const parsed = Array.isArray(data.schema) ? data.schema : []
        setFields(parsed)
      })
      .catch(() => router.push('/schemas'))
      .finally(() => setLoading(false))
  }, [id, router])

  const updateField = useCallback((idx: number, patch: Partial<SchemaField>) => {
    setFields(prev => prev.map((f, i) => i === idx ? { ...f, ...patch } : f))
    setDirty(true)
  }, [])

  const updateBbox = useCallback((idx: number, bboxPatch: Partial<SchemaField['bbox']>) => {
    setFields(prev => prev.map((f, i) =>
      i === idx ? { ...f, bbox: { ...f.bbox, ...bboxPatch } } : f
    ))
    setDirty(true)
  }, [])

  const deleteField = useCallback((idx: number) => {
    setFields(prev => prev.filter((_, i) => i !== idx))
    setSelectedIdx(null)
    setDirty(true)
  }, [])

  const addField = useCallback((bbox: SchemaField['bbox']) => {
    const newField: SchemaField = {
      bbox,
      description: 'New field',
      type: 'text',
      fill: true,
      value: null,
    }
    setFields(prev => [...prev, newField])
    setSelectedIdx(fields.length)
    setDirty(true)
  }, [fields.length])

  async function handleSave() {
    if (!schema) return
    setSaving(true)
    try {
      await api.patch(`/api/schemas/${schema.id}`, {
        schema: fields,
      })
      setDirty(false)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  // Coordinate conversion helpers
  function clientToNormalized(clientX: number, clientY: number) {
    const overlay = overlayRef.current
    if (!overlay) return { x: 0, y: 0 }
    const rect = overlay.getBoundingClientRect()
    return {
      x: (clientX - rect.left) / rect.width,
      y: (clientY - rect.top) / rect.height,
    }
  }

  function handleOverlayMouseDown(e: React.MouseEvent) {
    if (!drawMode) return
    if (e.button !== 0) return
    e.preventDefault()
    const { x, y } = clientToNormalized(e.clientX, e.clientY)
    drawRef.current = { startX: x, startY: y, currentX: x, currentY: y }
  }

  function handleFieldMouseDown(e: React.MouseEvent, idx: number, mode: DragMode) {
    e.preventDefault()
    e.stopPropagation()
    setSelectedIdx(idx)
    if (mode === null) return

    const field = fields[idx]
    dragRef.current = {
      mode,
      fieldIdx: idx,
      startX: e.clientX,
      startY: e.clientY,
      startBbox: { ...field.bbox },
    }
  }

  useEffect(() => {
    function handleMouseMove(e: MouseEvent) {
      // Drawing new box
      if (drawRef.current) {
        const { x, y } = clientToNormalized(e.clientX, e.clientY)
        drawRef.current.currentX = x
        drawRef.current.currentY = y
        const d = drawRef.current
        setDrawRect({
          left: Math.min(d.startX, d.currentX),
          top: Math.min(d.startY, d.currentY),
          width: Math.abs(d.currentX - d.startX),
          height: Math.abs(d.currentY - d.startY),
        })
        return
      }

      // Dragging / resizing existing field
      if (!dragRef.current) return
      const { mode, fieldIdx, startX, startY, startBbox } = dragRef.current
      const overlay = overlayRef.current
      if (!overlay) return

      const rect = overlay.getBoundingClientRect()
      const dx = (e.clientX - startX) / rect.width
      const dy = (e.clientY - startY) / rect.height

      if (mode === 'move') {
        updateBbox(fieldIdx, {
          left: Math.max(0, Math.min(1 - startBbox.width, startBbox.left + dx)),
          top: Math.max(0, Math.min(1 - startBbox.height, startBbox.top + dy)),
        })
      } else if (mode === 'resize-br') {
        updateBbox(fieldIdx, {
          width: Math.max(0.01, startBbox.width + dx),
          height: Math.max(0.005, startBbox.height + dy),
        })
      } else if (mode === 'resize-bl') {
        updateBbox(fieldIdx, {
          left: startBbox.left + dx,
          width: Math.max(0.01, startBbox.width - dx),
          height: Math.max(0.005, startBbox.height + dy),
        })
      } else if (mode === 'resize-tr') {
        updateBbox(fieldIdx, {
          top: startBbox.top + dy,
          width: Math.max(0.01, startBbox.width + dx),
          height: Math.max(0.005, startBbox.height - dy),
        })
      } else if (mode === 'resize-tl') {
        updateBbox(fieldIdx, {
          left: startBbox.left + dx,
          top: startBbox.top + dy,
          width: Math.max(0.01, startBbox.width - dx),
          height: Math.max(0.005, startBbox.height - dy),
        })
      }
    }

    function handleMouseUp() {
      if (drawRef.current) {
        const d = drawRef.current
        const left = Math.min(d.startX, d.currentX)
        const top = Math.min(d.startY, d.currentY)
        const width = Math.abs(d.currentX - d.startX)
        const height = Math.abs(d.currentY - d.startY)

        if (width > 0.005 && height > 0.003) {
          addField({
            page: currentPage,
            left,
            top,
            width,
            height,
          })
        }
        drawRef.current = null
        setDrawRect(null)
        setDrawMode(false)
        return
      }

      dragRef.current = null
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [updateBbox, addField, currentPage])

  const selectedField = selectedIdx !== null ? fields[selectedIdx] : null

  if (loading) return <p className="text-muted-foreground p-6">Loading schema...</p>
  if (!schema) return <p className="text-muted-foreground p-6">Schema not found</p>

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b px-4 py-2 bg-background shrink-0">
        <Link href="/schemas">
          <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold truncate">{schema.template_name}</h1>
          <p className="text-xs text-muted-foreground">{fields.length} fields · Page {currentPage}/{totalPages}</p>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant={drawMode ? 'default' : 'outline'}
            onClick={() => { setDrawMode(!drawMode); setSelectedIdx(null) }}
            title="Draw new field"
          >
            <Plus className="mr-1 h-3.5 w-3.5" />{drawMode ? 'Drawing...' : 'Add Field'}
          </Button>

          <Button size="sm" variant="outline" onClick={toggleAllVisibility} title="Toggle all field boxes">
            {noneVisible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          </Button>

          <div className="flex items-center border rounded-md">
            <Button size="sm" variant="ghost" className="px-2" onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}>−</Button>
            <span className="text-xs w-12 text-center">{Math.round(zoom * 100)}%</span>
            <Button size="sm" variant="ghost" className="px-2" onClick={() => setZoom(z => Math.min(3, z + 0.25))}>+</Button>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center gap-1">
              <Button size="sm" variant="ghost" disabled={currentPage <= 1} onClick={() => setCurrentPage(p => p - 1)}>
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <span className="text-xs">{currentPage}/{totalPages}</span>
              <Button size="sm" variant="ghost" disabled={currentPage >= totalPages} onClick={() => setCurrentPage(p => p + 1)}>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}

          <Button size="sm" onClick={handleSave} disabled={saving || !dirty}>
            {saving ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Save className="mr-1.5 h-3.5 w-3.5" />}
            {dirty ? 'Save Changes' : 'Saved'}
          </Button>
        </div>
      </div>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {/* PDF + Overlay */}
        <div ref={containerRef} className="flex-1 overflow-auto bg-zinc-100 dark:bg-zinc-900 p-4">
          <div
            className="relative mx-auto bg-white shadow-lg"
            style={{
              width: `${612 * zoom}px`,
              height: `${792 * zoom}px`,
            }}
          >
            {/* PDF Background */}
            {schema.pdf_url ? (
              <iframe
                src={`${schema.pdf_url}#page=${currentPage}&toolbar=0&navpanes=0`}
                className="absolute inset-0 w-full h-full border-0 pointer-events-none"
                title="PDF Template"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
                No PDF template linked — upload one in Templates
              </div>
            )}

            {/* Field overlay */}
            <div
              ref={overlayRef}
              className={`absolute inset-0 ${drawMode ? 'cursor-crosshair' : ''}`}
              onMouseDown={handleOverlayMouseDown}
              onClick={() => { if (!drawMode) setSelectedIdx(null) }}
            >
              {pageFields.filter(({ idx }) => !hiddenFields.has(idx)).map(({ field, idx }) => {
                const isSelected = selectedIdx === idx
                const isHovered = hoveredIdx === idx
                return (
                  <div
                    key={idx}
                    className={`absolute border-2 transition-colors ${
                      isSelected
                        ? 'border-blue-500 bg-blue-500/10 z-20'
                        : isHovered
                          ? 'border-blue-400/70 bg-blue-400/5 z-10'
                          : field.fill
                            ? 'border-emerald-500/50 bg-emerald-500/5'
                            : 'border-amber-500/40 bg-amber-500/5'
                    }`}
                    style={{
                      left: `${field.bbox.left * 100}%`,
                      top: `${field.bbox.top * 100}%`,
                      width: `${field.bbox.width * 100}%`,
                      height: `${field.bbox.height * 100}%`,
                    }}
                    onMouseDown={e => handleFieldMouseDown(e, idx, 'move')}
                    onMouseEnter={() => setHoveredIdx(idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                    title={field.description}
                  >
                    {/* Resize handles (only when selected) */}
                    {isSelected && (
                      <>
                        <div className="absolute -top-1 -left-1 w-2.5 h-2.5 bg-blue-500 rounded-full cursor-nw-resize"
                          onMouseDown={e => handleFieldMouseDown(e, idx, 'resize-tl')} />
                        <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-blue-500 rounded-full cursor-ne-resize"
                          onMouseDown={e => handleFieldMouseDown(e, idx, 'resize-tr')} />
                        <div className="absolute -bottom-1 -left-1 w-2.5 h-2.5 bg-blue-500 rounded-full cursor-sw-resize"
                          onMouseDown={e => handleFieldMouseDown(e, idx, 'resize-bl')} />
                        <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 bg-blue-500 rounded-full cursor-se-resize"
                          onMouseDown={e => handleFieldMouseDown(e, idx, 'resize-br')} />
                      </>
                    )}

                    {/* Field label */}
                    <div className="absolute -top-5 left-0 text-[10px] font-medium leading-none whitespace-nowrap pointer-events-none truncate max-w-[200px]"
                      style={{ color: isSelected ? '#3b82f6' : field.fill ? '#10b981' : '#f59e0b' }}
                    >
                      {field.description?.split(' - ')[0] || `Field ${idx + 1}`}
                    </div>
                  </div>
                )
              })}

              {/* Draw preview rect */}
              {drawRect && (
                <div
                  className="absolute border-2 border-dashed border-blue-500 bg-blue-500/10 pointer-events-none z-30"
                  style={{
                    left: `${drawRect.left * 100}%`,
                    top: `${drawRect.top * 100}%`,
                    width: `${drawRect.width * 100}%`,
                    height: `${drawRect.height * 100}%`,
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Properties panel */}
        <div className="w-80 border-l bg-background overflow-y-auto shrink-0">
          {selectedField && selectedIdx !== null ? (
            <FieldProperties
              field={selectedField}
              idx={selectedIdx}
              onChange={(patch) => updateField(selectedIdx, patch)}
              onBboxChange={(patch) => updateBbox(selectedIdx, patch)}
              onDelete={() => deleteField(selectedIdx)}
              onBack={() => setSelectedIdx(null)}
            />
          ) : (
            <div className="p-4">
              <h2 className="font-semibold text-sm mb-3">Fields ({pageFields.length} on page)</h2>
              <div className="space-y-0.5">
                {pageFields.map(({ field, idx }) => {
                  const isVisible = !hiddenFields.has(idx)
                  return (
                    <div
                      key={idx}
                      className={`flex items-start gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted cursor-pointer ${
                        selectedIdx === idx ? 'bg-muted' : ''
                      } ${!isVisible ? 'opacity-50' : ''}`}
                      onMouseEnter={() => setHoveredIdx(idx)}
                      onMouseLeave={() => setHoveredIdx(null)}
                    >
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={() => toggleFieldVisibility(idx)}
                        className="mt-1 shrink-0 accent-emerald-600 cursor-pointer"
                        title={isVisible ? 'Hide on PDF' : 'Show on PDF'}
                      />
                      <div className="flex-1 min-w-0" onClick={() => setSelectedIdx(idx)}>
                        <span className="truncate block text-sm">{field.description || `Field ${idx + 1}`}</span>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <Badge variant="outline" className="text-[10px] px-1 py-0">{field.type}</Badge>
                          {field.fill && <Badge className="text-[10px] px-1 py-0 bg-emerald-100 text-emerald-700 hover:bg-emerald-100">fill</Badge>}
                        </div>
                      </div>
                    </div>
                  )
                })}
                {pageFields.length === 0 && (
                  <p className="text-xs text-muted-foreground py-4 text-center">
                    No fields on this page.
                    <br />Click &quot;Add Field&quot; and draw on the PDF.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function FieldProperties({
  field, idx, onChange, onBboxChange, onDelete, onBack,
}: {
  field: SchemaField
  idx: number
  onChange: (patch: Partial<SchemaField>) => void
  onBboxChange: (patch: Partial<SchemaField['bbox']>) => void
  onDelete: () => void
  onBack: () => void
}) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Button size="sm" variant="ghost" className="px-1.5" onClick={onBack} title="Back to field list">
          <ArrowLeft className="h-3.5 w-3.5" />
        </Button>
        <h2 className="font-semibold text-sm flex-1">Field {idx + 1}</h2>
        <Button size="sm" variant="ghost" onClick={onDelete}>
          <Trash2 className="h-3.5 w-3.5 text-destructive" />
        </Button>
      </div>

      <div className="space-y-2">
        <Label className="text-xs">Description</Label>
        <Input
          value={field.description}
          onChange={e => onChange({ description: e.target.value })}
          className="text-sm"
          placeholder="Field description"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label className="text-xs">Type</Label>
          <select
            className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm"
            value={field.type}
            onChange={e => onChange({ type: e.target.value })}
          >
            <option value="text">text</option>
            <option value="checkbox">checkbox</option>
            <option value="number">number</option>
            <option value="date">date</option>
            <option value="signature">signature</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label className="text-xs">Fill</Label>
          <select
            className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm"
            value={field.fill ? 'true' : 'false'}
            onChange={e => onChange({ fill: e.target.value === 'true' })}
          >
            <option value="true">Yes (fill)</option>
            <option value="false">No (skip)</option>
          </select>
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-xs">Default Value</Label>
        <Input
          value={field.value ?? ''}
          onChange={e => onChange({ value: e.target.value || null })}
          className="text-sm"
          placeholder="Leave blank for AI fill"
        />
      </div>

      <div className="border-t pt-4">
        <h3 className="font-medium text-xs text-muted-foreground mb-3">BOUNDING BOX</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label className="text-[10px] text-muted-foreground">Left</Label>
            <Input
              type="number"
              step="0.001"
              min="0" max="1"
              value={field.bbox.left.toFixed(4)}
              onChange={e => onBboxChange({ left: parseFloat(e.target.value) || 0 })}
              className="text-xs font-mono h-8"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[10px] text-muted-foreground">Top</Label>
            <Input
              type="number"
              step="0.001"
              min="0" max="1"
              value={field.bbox.top.toFixed(4)}
              onChange={e => onBboxChange({ top: parseFloat(e.target.value) || 0 })}
              className="text-xs font-mono h-8"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[10px] text-muted-foreground">Width</Label>
            <Input
              type="number"
              step="0.001"
              min="0.005" max="1"
              value={field.bbox.width.toFixed(4)}
              onChange={e => onBboxChange({ width: parseFloat(e.target.value) || 0.01 })}
              className="text-xs font-mono h-8"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[10px] text-muted-foreground">Height</Label>
            <Input
              type="number"
              step="0.001"
              min="0.003" max="1"
              value={field.bbox.height.toFixed(4)}
              onChange={e => onBboxChange({ height: parseFloat(e.target.value) || 0.005 })}
              className="text-xs font-mono h-8"
            />
          </div>
        </div>
        <div className="mt-2 space-y-1">
          <Label className="text-[10px] text-muted-foreground">Page</Label>
          <Input
            type="number"
            min="1"
            value={field.bbox.page}
            onChange={e => onBboxChange({ page: parseInt(e.target.value) || 1 })}
            className="text-xs font-mono h-8 w-20"
          />
        </div>
      </div>

      <div className="border-t pt-4">
        <h3 className="font-medium text-xs text-muted-foreground mb-2">PREVIEW</h3>
        <div className="rounded-md bg-muted p-3 text-xs font-mono whitespace-pre-wrap break-all">
          {JSON.stringify(field, null, 2)}
        </div>
      </div>
    </div>
  )
}
