'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Key, Check, AlertCircle, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { ApiKey } from '@/lib/types'

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [openaiKey, setOpenaiKey] = useState('')
  const [reductoKey, setReductoKey] = useState('')
  const [saving, setSaving] = useState<string | null>(null)
  const [validated, setValidated] = useState<Record<string, boolean | null>>({})

  useEffect(() => {
    api.get<ApiKey[]>('/api/organizations/keys')
      .then(setKeys)
      .catch(() => setKeys([]))
      .finally(() => setLoading(false))
  }, [])

  async function handleSave(provider: 'openai' | 'reducto') {
    const key = provider === 'openai' ? openaiKey : reductoKey
    if (!key) return

    setSaving(provider)
    setValidated(v => ({ ...v, [provider]: null }))

    try {
      const result = await api.post<{ valid: boolean }>('/api/organizations/keys/validate', { provider, key })
      if (!result.valid) {
        setValidated(v => ({ ...v, [provider]: false }))
        return
      }

      await api.post('/api/organizations/keys', { provider, key })
      setValidated(v => ({ ...v, [provider]: true }))

      const updated = await api.get<ApiKey[]>('/api/organizations/keys')
      setKeys(updated)

      if (provider === 'openai') setOpenaiKey('')
      else setReductoKey('')
    } catch {
      setValidated(v => ({ ...v, [provider]: false }))
    } finally {
      setSaving(null)
    }
  }

  function getExistingKey(provider: string) {
    return keys.find(k => k.provider === provider)
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/settings">
          <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API Keys</h1>
          <p className="text-muted-foreground mt-1">
            Add your own API keys for OpenAI and Reducto (BYOK)
          </p>
        </div>
      </div>

      {(['openai', 'reducto'] as const).map(provider => {
        const existing = getExistingKey(provider)
        const key = provider === 'openai' ? openaiKey : reductoKey
        const setKey = provider === 'openai' ? setOpenaiKey : setReductoKey

        return (
          <Card key={provider}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 capitalize">
                <Key className="h-5 w-5" />
                {provider}
              </CardTitle>
              <CardDescription>
                {provider === 'openai'
                  ? 'Used for extracting structured data from Purchase Orders'
                  : 'Used for parsing PDFs and filling document templates'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {existing && (
                <div className="flex items-center gap-2 text-sm">
                  <Badge variant="secondary">
                    ····{existing.key_hint}
                  </Badge>
                  <span className="text-muted-foreground">
                    Added {new Date(existing.created_at).toLocaleDateString()}
                  </span>
                </div>
              )}

              <div className="flex gap-2">
                <Input
                  type="password"
                  placeholder={existing ? 'Replace existing key...' : `Enter ${provider} API key`}
                  value={key}
                  onChange={e => setKey(e.target.value)}
                />
                <Button
                  onClick={() => handleSave(provider)}
                  disabled={!key || saving === provider}
                >
                  {saving === provider ? 'Validating...' : existing ? 'Update' : 'Save'}
                </Button>
              </div>

              {validated[provider] === true && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <Check className="h-4 w-4" />
                  Key validated and saved
                </div>
              )}
              {validated[provider] === false && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  Key validation failed. Please check and try again.
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
