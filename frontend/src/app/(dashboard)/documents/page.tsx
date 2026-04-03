'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from '@/components/ui/tooltip'
import { Upload, Search, FileText, ExternalLink, Eye, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { Document, UserProfile } from '@/lib/types'

const STATUS_COLORS: Record<string, string> = {
  uploaded: 'bg-blue-100 text-blue-700',
  parsing: 'bg-yellow-100 text-yellow-700',
  parsed: 'bg-indigo-100 text-indigo-700',
  extracting: 'bg-yellow-100 text-yellow-700',
  extracted: 'bg-purple-100 text-purple-700',
  filling: 'bg-yellow-100 text-yellow-700',
  filled: 'bg-emerald-100 text-emerald-700',
  generating: 'bg-yellow-100 text-yellow-700',
  generated: 'bg-green-100 text-green-700',
  completed: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
}

function userInitials(profile: UserProfile | undefined): string {
  if (!profile?.display_name) return '?'
  return profile.display_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading...</p>}>
      <DocumentsContent />
    </Suspense>
  )
}

function DocumentsContent() {
  const searchParams = useSearchParams()
  const typeFilter = searchParams.get('type')

  const [documents, setDocuments] = useState<Document[]>([])
  const [profiles, setProfiles] = useState<Record<string, UserProfile>>({})
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const path = typeFilter ? `/api/documents?type=${typeFilter}` : '/api/documents'
    api.get<Document[]>(path)
      .then(docs => {
        setDocuments(docs)
        const userIds = [...new Set(
          docs.flatMap(d => [d.created_by, d.updated_by]).filter(Boolean) as string[]
        )]
        if (userIds.length > 0) {
          api.post<Record<string, UserProfile>>('/api/profile/resolve', { user_ids: userIds })
            .then(setProfiles)
            .catch(() => {})
        }
      })
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false))
  }, [typeFilter])

  const filtered = documents.filter(d =>
    d.document_name.toLowerCase().includes(search.toLowerCase()) ||
    d.document_type.toLowerCase().includes(search.toLowerCase())
  )

  async function handleDelete(docId: string) {
    if (!confirm('Delete this document permanently?')) return
    try {
      await api.delete(`/api/documents/${docId}`)
      setDocuments(prev => prev.filter(d => d.id !== docId))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
            <p className="text-muted-foreground mt-1">
              {typeFilter ? `Showing ${typeFilter} documents` : 'All Purchase Orders, Bills of Lading, and Packing Slips'}
            </p>
          </div>
          <Link href="/documents/upload">
            <Button><Upload className="mr-2 h-4 w-4" />Upload PO</Button>
          </Link>
        </div>

        <div className="flex gap-2">
          <Link href="/documents"><Badge variant={!typeFilter ? 'default' : 'outline'} className="cursor-pointer">All</Badge></Link>
          <Link href="/documents?type=PO"><Badge variant={typeFilter === 'PO' ? 'default' : 'outline'} className="cursor-pointer">POs</Badge></Link>
          <Link href="/documents?type=BOL"><Badge variant={typeFilter === 'BOL' ? 'default' : 'outline'} className="cursor-pointer">BOLs</Badge></Link>
          <Link href="/documents?type=PACKING_SLIP"><Badge variant={typeFilter === 'PACKING_SLIP' ? 'default' : 'outline'} className="cursor-pointer">Packing Slips</Badge></Link>
        </div>

        <Card>
          <CardHeader>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Search documents..." className="pl-9" value={search} onChange={e => setSearch(e.target.value)} />
            </div>
          </CardHeader>
          <CardContent>
            {loading ? <p className="text-center text-muted-foreground py-8">Loading...</p> : filtered.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground">No documents yet.</p>
                <Link href="/documents/upload">
                  <Button className="mt-4"><Upload className="mr-2 h-4 w-4" />Upload your first PO</Button>
                </Link>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Activity</TableHead>
                    <TableHead className="w-16" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map(doc => {
                    const creator = doc.created_by ? profiles[doc.created_by] : undefined
                    const updater = doc.updated_by ? profiles[doc.updated_by] : undefined
                    const showUpdater = doc.updated_by && doc.updated_by !== doc.created_by

                    return (
                      <TableRow key={doc.id}>
                        <TableCell className="font-medium">{doc.document_name}</TableCell>
                        <TableCell><Badge variant="outline">{doc.document_type}</Badge></TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[doc.status] || ''}`}>
                            {doc.status}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {doc.created_by && (
                              <Tooltip>
                                <TooltipTrigger className="flex items-center gap-1.5">
                                  <Avatar className="h-5 w-5">
                                    <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-medium">
                                      {userInitials(creator)}
                                    </AvatarFallback>
                                  </Avatar>
                                  <span className="text-xs text-muted-foreground">
                                    {new Date(doc.created_at).toLocaleDateString()}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  Created by {creator?.display_name || 'Unknown'}
                                </TooltipContent>
                              </Tooltip>
                            )}
                            {!doc.created_by && (
                              <span className="text-xs text-muted-foreground">
                                {new Date(doc.created_at).toLocaleDateString()}
                              </span>
                            )}
                            {showUpdater && (
                              <Tooltip>
                                <TooltipTrigger className="flex items-center gap-1">
                                  <span className="text-xs text-muted-foreground">·</span>
                                  <Avatar className="h-5 w-5">
                                    <AvatarFallback className="bg-orange-100 text-orange-700 text-[10px] font-medium">
                                      {userInitials(updater)}
                                    </AvatarFallback>
                                  </Avatar>
                                </TooltipTrigger>
                                <TooltipContent>
                                  Last updated by {updater?.display_name || 'Unknown'} on {new Date(doc.updated_at).toLocaleDateString()}
                                </TooltipContent>
                              </Tooltip>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Link href={`/documents/${doc.id}/view`}>
                              <Button variant="ghost" size="icon" title="View PDF"><Eye className="h-4 w-4" /></Button>
                            </Link>
                            {doc.document_type === 'PO' && (
                              <Link href={`/documents/${doc.id}/review`}>
                                <Button variant="ghost" size="icon" title="Pipeline"><ExternalLink className="h-4 w-4" /></Button>
                              </Link>
                            )}
                            <Button variant="ghost" size="icon" title="Delete" onClick={() => handleDelete(doc.id)}>
                              <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  )
}
