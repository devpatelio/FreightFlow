'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  ArrowLeft, Download, Upload, FileText, ExternalLink, Loader2, RefreshCw, Trash2,
} from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Document, UserProfile } from '@/lib/types'

function initials(profile: UserProfile | undefined): string {
  if (!profile?.display_name) return '?'
  return profile.display_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

export default function DocumentViewPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [doc, setDoc] = useState<Document | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [profiles, setProfiles] = useState<Record<string, UserProfile>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadDocument()
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadDocument() {
    setLoading(true)
    try {
      const [d, urlData] = await Promise.all([
        api.get<Document>(`/api/documents/${id}`),
        api.get<{ url: string; filename: string }>(`/api/documents/${id}/url`),
      ])
      setDoc(d)
      setPdfUrl(urlData.url)

      const userIds = [...new Set([d.created_by, d.updated_by].filter(Boolean) as string[])]
      if (userIds.length > 0) {
        api.post<Record<string, UserProfile>>('/api/profile/resolve', { user_ids: userIds })
          .then(setProfiles).catch(() => {})
      }
    } catch {
      router.push('/documents')
    } finally {
      setLoading(false)
    }
  }

  async function handleDownload() {
    if (!pdfUrl) return
    const a = document.createElement('a')
    a.href = pdfUrl
    a.download = doc?.document_name || 'document.pdf'
    a.target = '_blank'
    a.click()
  }

  async function handleReupload() {
    const file = fileInputRef.current?.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.upload(`/api/documents/${id}/reupload`, formData)
      if (fileInputRef.current) fileInputRef.current.value = ''
      await loadDocument()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete() {
    if (!confirm('Delete this document permanently? This cannot be undone.')) return
    try {
      await api.delete(`/api/documents/${id}`)
      router.push('/documents')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!doc) return <p className="text-muted-foreground p-6">Document not found</p>

  const isPO = doc.document_type === 'PO'
  const creator = doc.created_by ? profiles[doc.created_by] : undefined
  const updater = doc.updated_by ? profiles[doc.updated_by] : undefined
  const hasAttribution = doc.created_by || doc.updated_by

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold tracking-tight truncate">{doc.document_name}</h1>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <Badge variant="outline">{doc.document_type}</Badge>
            <Badge>{doc.status}</Badge>
            {doc.created_at && (
              <span className="text-xs text-muted-foreground">
                Created {new Date(doc.created_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isPO && (
            <Link href={`/documents/${id}/review`}>
              <Button variant="outline" size="sm">
                <ExternalLink className="mr-1.5 h-3.5 w-3.5" />Pipeline
              </Button>
            </Link>
          )}
          <Button variant="outline" size="sm" onClick={handleDownload} disabled={!pdfUrl}>
            <Download className="mr-1.5 h-3.5 w-3.5" />Download
          </Button>
          <div className="relative">
            <Button
              variant="outline" size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading
                ? <><Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />Uploading...</>
                : <><Upload className="mr-1.5 h-3.5 w-3.5" />Replace PDF</>
              }
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleReupload}
            />
          </div>
          <Button variant="ghost" size="icon" onClick={handleDelete} title="Delete document">
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
          </Button>
          <Button variant="ghost" size="icon" onClick={loadDocument} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Attribution timeline */}
      {hasAttribution && (
        <div className="flex items-center gap-4 rounded-lg border bg-muted/30 px-4 py-2.5 text-sm">
          {doc.created_by && (
            <div className="flex items-center gap-1.5">
              <Avatar className="h-5 w-5">
                <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-medium">
                  {initials(creator)}
                </AvatarFallback>
              </Avatar>
              <span className="text-muted-foreground">
                <span className="font-medium text-foreground">{creator?.display_name || 'Unknown'}</span>
                {' '}created {new Date(doc.created_at).toLocaleString()}
              </span>
            </div>
          )}
          {doc.updated_by && doc.updated_at !== doc.created_at && (
            <>
              <span className="text-muted-foreground">·</span>
              <div className="flex items-center gap-1.5">
                <Avatar className="h-5 w-5">
                  <AvatarFallback className="bg-orange-100 text-orange-700 text-[10px] font-medium">
                    {initials(updater)}
                  </AvatarFallback>
                </Avatar>
                <span className="text-muted-foreground">
                  <span className="font-medium text-foreground">{updater?.display_name || 'Unknown'}</span>
                  {' '}last edited {new Date(doc.updated_at).toLocaleString()}
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {/* PDF Viewer */}
      {pdfUrl ? (
        <div className="rounded-lg border bg-muted/30 overflow-hidden" style={{ height: 'calc(100vh - 240px)' }}>
          <iframe
            src={pdfUrl}
            className="w-full h-full"
            title={doc.document_name}
          />
        </div>
      ) : (
        <Card>
          <CardContent className="py-20 text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-muted-foreground">No PDF file available for this document.</p>
            <p className="text-sm text-muted-foreground mt-1">
              {isPO ? 'The file may not have been uploaded correctly.' : 'Run the generation pipeline to create this document.'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
