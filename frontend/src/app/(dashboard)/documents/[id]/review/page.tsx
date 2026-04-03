'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  ArrowLeft, Play, Loader2, CheckCircle2, Edit2, FileText,
  Download, Sparkles, RotateCcw, ChevronRight, Settings2,
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Document, Address, SellerProfile } from '@/lib/types'

type Op = 'parse' | 'extract_bol' | 'extract_ps' | 'fill_bol' | 'fill_ps' | 'reset'

interface RelatedDoc {
  id: string
  generated_document_id: string
  relationship_type: string
  created_at: string
}

const STAGE_ORDER = ['uploaded', 'parsed', 'extracted', 'filled'] as const
type Stage = typeof STAGE_ORDER[number]

function stageIndex(status: string): number {
  if (['parsing'].includes(status)) return 0
  if (['parsed', 'extracting'].includes(status)) return 1
  if (['extracted', 'filling'].includes(status)) return 2
  if (['filled', 'generated', 'completed'].includes(status)) return 3
  if (status === 'error') return -1
  return 0
}

export default function ReviewPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [doc, setDoc] = useState<Document | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeOps, setActiveOps] = useState<Set<Op>>(new Set())
  const [bolJson, setBolJson] = useState('')
  const [psJson, setPsJson] = useState('')
  const [editingBol, setEditingBol] = useState(false)
  const [editingPs, setEditingPs] = useState(false)
  const [relatedDocs, setRelatedDocs] = useState<RelatedDoc[]>([])
  const [fillResults, setFillResults] = useState<Record<string, { document_id: string; file_path: string }>>({})

  // Org context for extraction
  const [addresses, setAddresses] = useState<Address[]>([])
  const [sellers, setSellers] = useState<SellerProfile[]>([])
  const [selectedAddressId, setSelectedAddressId] = useState('')
  const [selectedSellerId, setSelectedSellerId] = useState('')
  const [showContextPanel, setShowContextPanel] = useState(false)

  const bolRef = useRef(bolJson)
  const psRef = useRef(psJson)
  bolRef.current = bolJson
  psRef.current = psJson

  const startOp = (op: Op) => setActiveOps(prev => new Set(prev).add(op))
  const endOp = (op: Op) => setActiveOps(prev => { const next = new Set(prev); next.delete(op); return next })
  const hasAnyOp = activeOps.size > 0
  const isOp = (op: Op) => activeOps.has(op)

  const refreshDoc = useCallback(async (preserveLocal = false) => {
    const d = await api.get<Document>(`/api/documents/${id}`)
    setDoc(d)
    const gen = d.generated_data as Record<string, unknown> | null
    if (!preserveLocal || !bolRef.current) {
      if (gen?.bol) setBolJson(JSON.stringify(gen.bol, null, 2))
      else setBolJson('')
    }
    if (!preserveLocal || !psRef.current) {
      if (gen?.packing_slip) setPsJson(JSON.stringify(gen.packing_slip, null, 2))
      else setPsJson('')
    }
    const related = await api.get<RelatedDoc[]>(`/api/documents/${id}/related`).catch(() => [])
    setRelatedDocs(related)
    return d
  }, [id])

  useEffect(() => {
    refreshDoc()
      .catch(() => router.push('/documents'))
      .finally(() => setLoading(false))

    // Load org context options
    api.get<Address[]>('/api/addresses').then(all => {
      setAddresses(all.filter(a => !a.customer_id))
    }).catch(() => {})
    api.get<SellerProfile[]>('/api/sellers').then(setSellers).catch(() => {})
  }, [refreshDoc, router])

  async function handleReset(target: Stage) {
    if (!confirm(`Reset pipeline back to "${target}"? This will clear data from later steps.`)) return
    startOp('reset')
    try {
      await api.post(`/api/documents/${id}/reset`, { target_status: target })
      setFillResults({})
      await refreshDoc()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Reset failed')
    } finally {
      endOp('reset')
    }
  }

  async function handleParse() {
    startOp('parse')
    try {
      await api.post(`/api/documents/${id}/parse`)
      await refreshDoc()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Parse failed')
    } finally {
      endOp('parse')
    }
  }

  async function handleExtract(type: 'BOL' | 'PACKING_SLIP') {
    const op: Op = type === 'BOL' ? 'extract_bol' : 'extract_ps'
    startOp(op)
    try {
      const payload: Record<string, string> = { document_type: type }
      if (selectedAddressId) payload.address_id = selectedAddressId
      if (selectedSellerId) payload.seller_id = selectedSellerId

      const result = await api.post<{ data: unknown }>(`/api/documents/${id}/extract`, payload)
      if (type === 'BOL') setBolJson(JSON.stringify(result.data, null, 2))
      else setPsJson(JSON.stringify(result.data, null, 2))
      await refreshDoc(true)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Extraction failed')
    } finally {
      endOp(op)
    }
  }

  async function handleFill(type: 'BOL' | 'PACKING_SLIP') {
    const op: Op = type === 'BOL' ? 'fill_bol' : 'fill_ps'
    startOp(op)
    try {
      const jsonStr = type === 'BOL' ? bolJson : psJson
      let dataOverrides: Record<string, unknown> | undefined
      try {
        dataOverrides = JSON.parse(jsonStr)
      } catch {
        alert('Invalid JSON. Please fix the data before generating.')
        endOp(op)
        return
      }

      const result = await api.post<{
        status: string
        document_type: string
        generated_document_id: string
        file_path: string
      }>(`/api/documents/${id}/fill`, {
        document_type: type,
        data_overrides: dataOverrides,
      })

      setFillResults(prev => ({
        ...prev,
        [type]: { document_id: result.generated_document_id, file_path: result.file_path },
      }))
      await refreshDoc(true)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fill failed')
    } finally {
      endOp(op)
    }
  }

  async function handleExtractBoth() {
    await handleExtract('BOL')
    await handleExtract('PACKING_SLIP')
  }

  if (loading) return <p className="text-muted-foreground p-6">Loading...</p>
  if (!doc) return <p className="text-muted-foreground p-6">Document not found</p>

  const currentIdx = stageIndex(doc.status)
  const isParsed = currentIdx >= 1
  const isExtracted = currentIdx >= 2
  const parsedChunks = (doc.parsed_data as { chunks?: Array<{ content: string }> } | null)?.chunks || []

  const hasBolGenerated = relatedDocs.some(r => r.relationship_type === 'BOL') || !!fillResults['BOL']
  const hasPsGenerated = relatedDocs.some(r => r.relationship_type === 'PACKING_SLIP') || !!fillResults['PACKING_SLIP']

  const steps = [
    { key: 'uploaded', label: 'Uploaded', done: true, resettable: false },
    { key: 'parsed', label: 'Parsed', done: isParsed, resettable: isParsed },
    { key: 'extracted', label: 'Extracted', done: isExtracted && (!!bolJson || !!psJson), resettable: isExtracted },
    { key: 'filled', label: 'Generated', done: hasBolGenerated || hasPsGenerated, resettable: false },
  ]

  const hasContextOptions = addresses.length > 0 || sellers.length > 0

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/documents">
          <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{doc.document_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="outline">{doc.document_type}</Badge>
            <Badge>{doc.status}</Badge>
            {doc.status === 'error' && (
              <Button size="sm" variant="outline" onClick={() => handleReset('uploaded')}>
                <RotateCcw className="mr-1.5 h-3 w-3" />Restart
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Pipeline Stepper */}
      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {steps.map((step, i) => {
          const isCurrent = step.key === STAGE_ORDER[currentIdx]
          const canReset = step.resettable && currentIdx > i && !hasAnyOp
          return (
            <div key={step.key} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground/40 shrink-0" />}
              <button
                disabled={!canReset}
                onClick={() => canReset ? handleReset(step.key as Stage) : undefined}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors ${
                  step.done
                    ? canReset
                      ? 'bg-green-100 text-green-700 hover:bg-amber-100 hover:text-amber-700 cursor-pointer'
                      : 'bg-green-100 text-green-700'
                    : isCurrent || isOp('reset')
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-muted text-muted-foreground'
                }`}
                title={canReset ? `Reset back to ${step.label}` : undefined}
              >
                {step.done ? <CheckCircle2 className="h-4 w-4" /> :
                 (isCurrent && hasAnyOp) ? <Loader2 className="h-4 w-4 animate-spin" /> :
                 <FileText className="h-4 w-4" />}
                {step.label}
              </button>
            </div>
          )
        })}
      </div>

      {/* Step 1: Parse */}
      {!isParsed ? (
        <Card>
          <CardHeader>
            <CardTitle>Step 1: Parse Purchase Order</CardTitle>
            <CardDescription>
              Extract structured text and tables from the PDF using Reducto
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleParse} disabled={isOp('parse')}>
              {isOp('parse') ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Parsing...</>
              ) : (
                <><Play className="mr-2 h-4 w-4" />Parse PO</>
              )}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Parsed Data</CardTitle>
                <CardDescription>{parsedChunks.length} chunks extracted</CardDescription>
              </div>
              <Button size="sm" variant="ghost" onClick={() => handleReset('uploaded')} disabled={hasAnyOp}>
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" />Re-parse
              </Button>
            </div>
          </CardHeader>
          {parsedChunks.length > 0 && (
            <CardContent>
              <div className="max-h-60 overflow-y-auto rounded-lg bg-muted p-4 font-mono text-sm">
                {parsedChunks.map((chunk, i) => (
                  <div key={i} className="mb-3 last:mb-0">
                    <p className="text-xs text-muted-foreground mb-1">Chunk {i + 1}</p>
                    <p className="whitespace-pre-wrap">{chunk.content?.slice(0, 500)}{(chunk.content?.length ?? 0) > 500 ? '...' : ''}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* Step 2: Extract with org context */}
      {isParsed && (
        <>
          {/* Organization Context Panel */}
          {hasContextOptions && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base">Organization Context</CardTitle>
                    <CardDescription>Select address and seller info to use during extraction</CardDescription>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => setShowContextPanel(!showContextPanel)}>
                    <Settings2 className="mr-1.5 h-3.5 w-3.5" />{showContextPanel ? 'Hide' : 'Configure'}
                  </Button>
                </div>
              </CardHeader>
              {showContextPanel && (
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {addresses.length > 0 && (
                      <div className="space-y-2">
                        <Label className="text-sm">Ship From Address</Label>
                        <select
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          value={selectedAddressId}
                          onChange={e => setSelectedAddressId(e.target.value)}
                        >
                          <option value="">Default (auto-detect)</option>
                          {addresses.map(a => (
                            <option key={a.id} value={a.id}>
                              {a.name} — {a.address_line}, {a.city} {a.state}
                            </option>
                          ))}
                        </select>
                        <p className="text-xs text-muted-foreground">
                          Override the ship-from address on extracted BOL and Packing Slip
                        </p>
                      </div>
                    )}
                    {sellers.length > 0 && (
                      <div className="space-y-2">
                        <Label className="text-sm">Seller Profile</Label>
                        <select
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          value={selectedSellerId}
                          onChange={e => setSelectedSellerId(e.target.value)}
                        >
                          <option value="">Default seller profile</option>
                          {sellers.map(s => (
                            <option key={s.id} value={s.id}>
                              {s.company_name}{s.default_salesperson ? ` (${s.default_salesperson})` : ''}
                            </option>
                          ))}
                        </select>
                        <p className="text-xs text-muted-foreground">
                          Company info and salesperson passed to the AI model
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {!bolJson && !psJson && (
            <Card>
              <CardHeader>
                <CardTitle>Step 2: Extract Data</CardTitle>
                <CardDescription>Use AI to extract BOL and Packing Slip data from the parsed PO</CardDescription>
              </CardHeader>
              <CardContent className="flex gap-3 flex-wrap">
                <Button onClick={handleExtractBoth} disabled={isOp('extract_bol') || isOp('extract_ps')}>
                  {(isOp('extract_bol') || isOp('extract_ps'))
                    ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Extracting...</>
                    : <><Play className="mr-2 h-4 w-4" />Extract Both</>
                  }
                </Button>
                <Button onClick={() => handleExtract('BOL')} disabled={isOp('extract_bol')} variant="outline">
                  {isOp('extract_bol') ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                  Extract BOL Only
                </Button>
                <Button onClick={() => handleExtract('PACKING_SLIP')} disabled={isOp('extract_ps')} variant="outline">
                  {isOp('extract_ps') ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                  Extract PS Only
                </Button>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <ExtractCard
              title="Bill of Lading"
              description="AI-extracted BOL data"
              json={bolJson}
              onJsonChange={setBolJson}
              editing={editingBol}
              onToggleEdit={() => setEditingBol(!editingBol)}
              extracting={isOp('extract_bol')}
              filling={isOp('fill_bol')}
              onExtract={() => handleExtract('BOL')}
              onFill={() => handleFill('BOL')}
              extractDisabled={isOp('extract_bol')}
              fillDisabled={isOp('fill_bol')}
              hasGenerated={hasBolGenerated}
              generatedDocId={fillResults['BOL']?.document_id || relatedDocs.find(r => r.relationship_type === 'BOL')?.generated_document_id}
            />

            <ExtractCard
              title="Packing Slip"
              description="AI-extracted Packing Slip data"
              json={psJson}
              onJsonChange={setPsJson}
              editing={editingPs}
              onToggleEdit={() => setEditingPs(!editingPs)}
              extracting={isOp('extract_ps')}
              filling={isOp('fill_ps')}
              onExtract={() => handleExtract('PACKING_SLIP')}
              onFill={() => handleFill('PACKING_SLIP')}
              extractDisabled={isOp('extract_ps')}
              fillDisabled={isOp('fill_ps')}
              hasGenerated={hasPsGenerated}
              generatedDocId={fillResults['PACKING_SLIP']?.document_id || relatedDocs.find(r => r.relationship_type === 'PACKING_SLIP')?.generated_document_id}
            />
          </div>
        </>
      )}
    </div>
  )
}

function ExtractCard({
  title, description, json, onJsonChange,
  editing, onToggleEdit,
  extracting, filling, onExtract, onFill,
  extractDisabled, fillDisabled, hasGenerated, generatedDocId,
}: {
  title: string
  description: string
  json: string
  onJsonChange: (v: string) => void
  editing: boolean
  onToggleEdit: () => void
  extracting: boolean
  filling: boolean
  onExtract: () => void
  onFill: () => void
  extractDisabled: boolean
  fillDisabled: boolean
  hasGenerated: boolean
  generatedDocId?: string
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {json && (
              <>
                <Button size="sm" variant="ghost" onClick={onExtract} disabled={extractDisabled} title="Re-extract">
                  {extracting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
                </Button>
                <Button size="sm" variant="outline" onClick={onToggleEdit}>
                  <Edit2 className="mr-1.5 h-3 w-3" />{editing ? 'Preview' : 'Edit'}
                </Button>
              </>
            )}
            {!json && (
              <Button size="sm" onClick={onExtract} disabled={extractDisabled}>
                {extracting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                Extract
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {json ? (
          <>
            {editing ? (
              <Textarea
                value={json}
                onChange={e => onJsonChange(e.target.value)}
                className="font-mono text-xs min-h-[300px]"
              />
            ) : (
              <pre className="max-h-[400px] overflow-auto rounded-lg bg-muted p-4 font-mono text-xs">
                {json}
              </pre>
            )}

            <div className="border-t pt-4">
              {hasGenerated ? (
                <div className="flex items-center gap-3 flex-wrap">
                  <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                    <CheckCircle2 className="mr-1 h-3 w-3" />Generated
                  </Badge>
                  {generatedDocId && (
                    <Link href={`/documents/${generatedDocId}/view`}>
                      <Button size="sm" variant="outline">
                        <Download className="mr-2 h-3.5 w-3.5" />View {title}
                      </Button>
                    </Link>
                  )}
                  <Button size="sm" variant="ghost" onClick={onFill} disabled={fillDisabled}>
                    {filling
                      ? <><Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />Regenerating...</>
                      : <><Sparkles className="mr-1.5 h-3.5 w-3.5" />Regenerate</>
                    }
                  </Button>
                </div>
              ) : (
                <Button onClick={onFill} disabled={fillDisabled}>
                  {filling ? (
                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Generating {title}...</>
                  ) : (
                    <><Sparkles className="mr-2 h-4 w-4" />Generate {title}</>
                  )}
                </Button>
              )}
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            {extracting
              ? 'Extracting data...'
              : `Not yet extracted. Click Extract to generate ${title} data from the parsed PO.`}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
