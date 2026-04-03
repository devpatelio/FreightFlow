'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Save, GitBranch } from 'lucide-react'
import { api } from '@/lib/api'

interface PipelineDefinition {
  id: string
  org_id: string | null
  name: string
  document_type: string
  steps: Array<{ name: string; type: string; config: Record<string, unknown> }>
  is_default: boolean
  description: string | null
  created_at: string
}

interface GenerationConfig {
  default_model: string
  temperature: number
  enable_few_shot: boolean
  max_few_shot_examples: number
  default_edit_options: Record<string, unknown>
}

export default function PipelinesPage() {
  const [definitions, setDefinitions] = useState<PipelineDefinition[]>([])
  const [config, setConfig] = useState<GenerationConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [savingConfig, setSavingConfig] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get<PipelineDefinition[]>('/api/pipelines/definitions'),
      api.get<GenerationConfig>('/api/pipelines/config'),
    ])
      .then(([defs, c]) => {
        setDefinitions(defs)
        setConfig(c)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleSaveConfig() {
    if (!config) return
    setSavingConfig(true)
    try {
      const updated = await api.patch<GenerationConfig>('/api/pipelines/config', config)
      setConfig(updated)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSavingConfig(false)
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Pipelines</h1>
        <p className="text-muted-foreground mt-1">Pipeline definitions and AI generation settings</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Pipeline Definitions
          </CardTitle>
          <CardDescription>Active pipeline variants for document generation</CardDescription>
        </CardHeader>
        <CardContent>
          {definitions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No pipeline definitions yet. System defaults will be used.</p>
          ) : (
            <div className="space-y-3">
              {definitions.map(def => (
                <div key={def.id} className="rounded-lg border p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{def.name}</span>
                      <Badge variant="outline">{def.document_type}</Badge>
                      {def.is_default && <Badge>Default</Badge>}
                      {!def.org_id && <Badge variant="secondary">System</Badge>}
                    </div>
                  </div>
                  {def.description && (
                    <p className="text-sm text-muted-foreground mb-2">{def.description}</p>
                  )}
                  <div className="flex gap-2 flex-wrap">
                    {def.steps.map((step, i) => (
                      <div key={i} className="flex items-center gap-1 text-xs">
                        {i > 0 && <span className="text-muted-foreground">→</span>}
                        <Badge variant="outline" className="text-xs">
                          {step.name}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {config && (
        <Card>
          <CardHeader>
            <CardTitle>Generation Config</CardTitle>
            <CardDescription>AI model preferences and extraction settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Default Model</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={config.default_model}
                  onChange={e => setConfig({ ...config, default_model: e.target.value })}
                >
                  <option value="gpt-5.4">GPT-5.4</option>
                  <option value="gpt-5.4-mini">GPT-5.4 Mini</option>
                  <option value="gpt-5.4-nano">GPT-5.4 Nano</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Temperature</Label>
                <Input
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.temperature}
                  onChange={e => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="few-shot"
                  checked={config.enable_few_shot}
                  onChange={e => setConfig({ ...config, enable_few_shot: e.target.checked })}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="few-shot">Enable Few-Shot Learning</Label>
              </div>
              <div className="space-y-2">
                <Label>Max Few-Shot Examples</Label>
                <Input
                  type="number"
                  min="0"
                  max="10"
                  value={config.max_few_shot_examples}
                  onChange={e => setConfig({ ...config, max_few_shot_examples: parseInt(e.target.value) })}
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button onClick={handleSaveConfig} disabled={savingConfig}>
                <Save className="mr-2 h-4 w-4" />
                {savingConfig ? 'Saving...' : 'Save Config'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
