'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Building2, Key, UserCircle, MapPin, FileUp, CheckCircle2,
  ArrowRight, ArrowLeft, Loader2, Mail, Upload,
} from 'lucide-react'
import { api } from '@/lib/api'
import { createClient } from '@/lib/supabase'

type Step = 'org' | 'keys' | 'profile' | 'address' | 'templates'

const STEPS: { key: Step; label: string; icon: React.ElementType }[] = [
  { key: 'org', label: 'Organization', icon: Building2 },
  { key: 'keys', label: 'API Keys', icon: Key },
  { key: 'profile', label: 'Company Profile', icon: UserCircle },
  { key: 'address', label: 'Address', icon: MapPin },
  { key: 'templates', label: 'Templates', icon: FileUp },
]

interface PendingInvitation {
  id: string
  org_id: string
  email: string
  role: string
  organizations?: { name: string; slug: string }
}

export default function OnboardingPage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState<Step>('org')
  const [loading, setLoading] = useState(false)
  const [orgCreated, setOrgCreated] = useState(false)
  const [inviteAccepted, setInviteAccepted] = useState(false)

  // Step 1: Org
  const [orgName, setOrgName] = useState('')
  const [orgSlug, setOrgSlug] = useState('')
  const [pendingInvites, setPendingInvites] = useState<PendingInvitation[]>([])
  const [loadingInvites, setLoadingInvites] = useState(true)
  const [orgError, setOrgError] = useState('')

  // Step 2: Keys
  const [openaiKey, setOpenaiKey] = useState('')
  const [reductoKey, setReductoKey] = useState('')
  const [openaiValid, setOpenaiValid] = useState<boolean | null>(null)
  const [reductoValid, setReductoValid] = useState<boolean | null>(null)
  const [validating, setValidating] = useState('')

  // Step 3: Profile
  const [companyName, setCompanyName] = useState('')
  const [salesperson, setSalesperson] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [contextText, setContextText] = useState('')

  // Step 4: Address
  const [addrName, setAddrName] = useState('')
  const [addrLine, setAddrLine] = useState('')
  const [addrCity, setAddrCity] = useState('')
  const [addrState, setAddrState] = useState('')
  const [addrZip, setAddrZip] = useState('')
  const [addrCountry, setAddrCountry] = useState('USA')

  // Step 5: Templates
  const [bolFile, setBolFile] = useState<File | null>(null)
  const [psFile, setPsFile] = useState<File | null>(null)
  const bolInputRef = useRef<HTMLInputElement>(null)
  const psInputRef = useRef<HTMLInputElement>(null)

  const currentIdx = STEPS.findIndex(s => s.key === currentStep)

  useEffect(() => {
    api.get<{ org_id: string | null; organization: { onboarding_completed_at: string | null } | null }>(
      '/api/organizations/me'
    ).then(data => {
      if (data.org_id && data.organization?.onboarding_completed_at) {
        router.replace('/')
        return
      }
      if (data.org_id) {
        setOrgCreated(true)
        setCurrentStep('keys')
      }
    }).catch(() => {})

    api.get<PendingInvitation[]>('/api/organizations/invitations/pending')
      .then(setPendingInvites)
      .catch(() => {})
      .finally(() => setLoadingInvites(false))
  }, [router])

  function autoSlug(name: string) {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  }

  async function handleCreateOrg() {
    setLoading(true)
    setOrgError('')
    try {
      await api.post('/api/organizations', { name: orgName, slug: orgSlug || autoSlug(orgName) })
      setOrgCreated(true)
      setCurrentStep('keys')
    } catch (err) {
      setOrgError(err instanceof Error ? err.message : 'Failed to create organization')
    } finally {
      setLoading(false)
    }
  }

  async function handleAcceptInvite(inviteId: string) {
    setLoading(true)
    setOrgError('')
    try {
      await api.post(`/api/organizations/invitations/${inviteId}/accept`)
      setInviteAccepted(true)
      router.replace('/')
    } catch (err) {
      setOrgError(err instanceof Error ? err.message : 'Failed to accept invitation')
    } finally {
      setLoading(false)
    }
  }

  async function handleValidateKey(provider: 'openai' | 'reducto') {
    const key = provider === 'openai' ? openaiKey : reductoKey
    if (!key) return
    setValidating(provider)
    try {
      const result = await api.post<{ valid: boolean }>('/api/organizations/keys/validate', { provider, key })
      if (provider === 'openai') setOpenaiValid(result.valid)
      else setReductoValid(result.valid)
    } catch {
      if (provider === 'openai') setOpenaiValid(false)
      else setReductoValid(false)
    } finally {
      setValidating('')
    }
  }

  async function handleSaveKeys() {
    setLoading(true)
    try {
      if (openaiKey) await api.post('/api/organizations/keys', { provider: 'openai', key: openaiKey })
      if (reductoKey) await api.post('/api/organizations/keys', { provider: 'reducto', key: reductoKey })
      setCurrentStep('profile')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save keys')
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveProfile() {
    if (!companyName) { alert('Company name is required'); return }
    setLoading(true)
    try {
      await api.post('/api/sellers', {
        company_name: companyName,
        default_salesperson: salesperson || undefined,
        phone: phone || undefined,
        email: email || undefined,
        context_text: contextText || undefined,
        is_default: true,
      })
      setCurrentStep('address')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveAddress() {
    if (!addrName || !addrLine || !addrCity || !addrState || !addrZip) {
      alert('Please fill in all required address fields')
      return
    }
    setLoading(true)
    try {
      await api.post('/api/addresses', {
        name: addrName,
        address_line: addrLine,
        city: addrCity,
        state: addrState,
        zip_code: addrZip,
        country: addrCountry,
      })
      setCurrentStep('templates')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save address')
    } finally {
      setLoading(false)
    }
  }

  async function handleUploadTemplate(file: File, docType: 'BOL' | 'PACKING_SLIP') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', docType === 'BOL' ? 'Bill of Lading Template' : 'Packing Slip Template')
    formData.append('document_type', docType)
    formData.append('description', `Default ${docType === 'BOL' ? 'BOL' : 'Packing Slip'} template`)
    await api.upload('/api/templates/upload', formData)
  }

  async function handleFinish() {
    setLoading(true)
    try {
      if (bolFile) await handleUploadTemplate(bolFile, 'BOL')
      if (psFile) await handleUploadTemplate(psFile, 'PACKING_SLIP')

      await api.post('/api/organizations/complete-onboarding')
      router.replace('/')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to complete onboarding')
    } finally {
      setLoading(false)
    }
  }

  async function handleSignOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome to FreightFlow</h1>
          <p className="text-muted-foreground mt-1">Let&apos;s get your organization set up</p>
        </div>
        <Button variant="ghost" size="sm" onClick={handleSignOut} className="text-muted-foreground">
          Sign out
        </Button>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {STEPS.map((step, i) => {
          const isDone = i < currentIdx
          const isCurrent = step.key === currentStep
          const Icon = step.icon
          return (
            <div key={step.key} className="flex items-center gap-1">
              {i > 0 && <div className={`h-px w-8 ${isDone ? 'bg-primary' : 'bg-border'}`} />}
              <div className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium whitespace-nowrap ${
                isDone ? 'bg-primary/10 text-primary' :
                isCurrent ? 'bg-primary text-primary-foreground' :
                'bg-muted text-muted-foreground'
              }`}>
                {isDone ? <CheckCircle2 className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                {step.label}
              </div>
            </div>
          )
        })}
      </div>

      {/* Step 1: Organization */}
      {currentStep === 'org' && (
        <Card>
          <CardHeader>
            <CardTitle>Create or Join an Organization</CardTitle>
            <CardDescription>
              Create a new organization or accept a pending invitation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {orgError && (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                {orgError}
              </div>
            )}

            {/* Pending invitations */}
            {!loadingInvites && pendingInvites.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Pending Invitations</h3>
                {pendingInvites.map(inv => (
                  <div key={inv.id} className="flex items-center justify-between rounded-lg border p-4">
                    <div className="flex items-center gap-3">
                      <Mail className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">{inv.organizations?.name || 'Organization'}</p>
                        <p className="text-xs text-muted-foreground">Role: {inv.role}</p>
                      </div>
                    </div>
                    <Button size="sm" onClick={() => handleAcceptInvite(inv.id)} disabled={loading}>
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Accept'}
                    </Button>
                  </div>
                ))}
                <div className="relative">
                  <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground">or create new</span>
                  </div>
                </div>
              </div>
            )}

            {/* Create org form */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Organization Name *</Label>
                <Input
                  placeholder="e.g., Hanson Chemicals"
                  value={orgName}
                  onChange={e => { setOrgName(e.target.value); if (!orgSlug) setOrgSlug(autoSlug(e.target.value)) }}
                />
              </div>
              <div className="space-y-2">
                <Label>Slug</Label>
                <Input
                  placeholder="e.g., hanson-chemicals"
                  value={orgSlug}
                  onChange={e => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                />
                <p className="text-xs text-muted-foreground">URL-friendly identifier. Auto-generated from name if left blank.</p>
              </div>
              <Button onClick={handleCreateOrg} disabled={loading || !orgName}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Building2 className="mr-2 h-4 w-4" />}
                Create Organization
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: API Keys */}
      {currentStep === 'keys' && (
        <Card>
          <CardHeader>
            <CardTitle>API Keys</CardTitle>
            <CardDescription>
              Connect your AI services. You can also add these later in Settings.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <Label>OpenAI API Key</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="sk-..."
                  value={openaiKey}
                  onChange={e => { setOpenaiKey(e.target.value); setOpenaiValid(null) }}
                  type="password"
                  className="flex-1"
                />
                <Button variant="outline" size="sm" onClick={() => handleValidateKey('openai')} disabled={!openaiKey || validating === 'openai'}>
                  {validating === 'openai' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Validate'}
                </Button>
              </div>
              {openaiValid !== null && (
                <p className={`text-xs ${openaiValid ? 'text-emerald-600' : 'text-destructive'}`}>
                  {openaiValid ? 'Key is valid' : 'Key validation failed'}
                </p>
              )}
            </div>

            <div className="space-y-3">
              <Label>Reducto API Key</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Your Reducto key"
                  value={reductoKey}
                  onChange={e => { setReductoKey(e.target.value); setReductoValid(null) }}
                  type="password"
                  className="flex-1"
                />
                <Button variant="outline" size="sm" onClick={() => handleValidateKey('reducto')} disabled={!reductoKey || validating === 'reducto'}>
                  {validating === 'reducto' ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Validate'}
                </Button>
              </div>
              {reductoValid !== null && (
                <p className={`text-xs ${reductoValid ? 'text-emerald-600' : 'text-destructive'}`}>
                  {reductoValid ? 'Key is valid' : 'Key validation failed'}
                </p>
              )}
            </div>

            <div className="flex justify-between pt-2">
              <Button variant="ghost" onClick={() => setCurrentStep('profile')}>
                Skip for now <ArrowRight className="ml-1.5 h-4 w-4" />
              </Button>
              <Button onClick={handleSaveKeys} disabled={loading || (!openaiKey && !reductoKey)}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
                Save &amp; Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Company Profile */}
      {currentStep === 'profile' && (
        <Card>
          <CardHeader>
            <CardTitle>Company Profile</CardTitle>
            <CardDescription>
              This information is used in document generation prompts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Company Name *</Label>
                <Input placeholder="e.g., Hanson Chemicals" value={companyName} onChange={e => setCompanyName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Default Salesperson</Label>
                <Input placeholder="e.g., Pan Patel" value={salesperson} onChange={e => setSalesperson(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input placeholder="e.g., 416-457-8271" value={phone} onChange={e => setPhone(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input placeholder="e.g., contact@company.com" value={email} onChange={e => setEmail(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Company Context</Label>
              <Textarea
                placeholder="Describe your company and what you do. This text is sent to the AI model to help it understand your business context..."
                rows={4}
                value={contextText}
                onChange={e => setContextText(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">This is included in AI prompts for document generation</p>
            </div>

            <div className="flex justify-between pt-2">
              <Button variant="outline" onClick={() => setCurrentStep('keys')}>
                <ArrowLeft className="mr-1.5 h-4 w-4" />Back
              </Button>
              <Button onClick={handleSaveProfile} disabled={loading || !companyName}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Address */}
      {currentStep === 'address' && (
        <Card>
          <CardHeader>
            <CardTitle>Ship-From Address</CardTitle>
            <CardDescription>
              Your primary warehouse or office address used on BOLs and Packing Slips
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Location Name *</Label>
              <Input placeholder="e.g., Main Warehouse" value={addrName} onChange={e => setAddrName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Street Address *</Label>
              <Input placeholder="e.g., 21177 Tower Drive N 169 W" value={addrLine} onChange={e => setAddrLine(e.target.value)} />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>City *</Label>
                <Input placeholder="e.g., Jackson" value={addrCity} onChange={e => setAddrCity(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>State *</Label>
                <Input placeholder="e.g., WI" value={addrState} onChange={e => setAddrState(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>ZIP *</Label>
                <Input placeholder="e.g., 53037" value={addrZip} onChange={e => setAddrZip(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Country</Label>
              <Input value={addrCountry} onChange={e => setAddrCountry(e.target.value)} />
            </div>

            <div className="flex justify-between pt-2">
              <Button variant="outline" onClick={() => setCurrentStep('profile')}>
                <ArrowLeft className="mr-1.5 h-4 w-4" />Back
              </Button>
              <Button onClick={handleSaveAddress} disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-2 h-4 w-4" />}
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 5: Templates */}
      {currentStep === 'templates' && (
        <Card>
          <CardHeader>
            <CardTitle>PDF Templates (Optional)</CardTitle>
            <CardDescription>
              Upload the blank BOL and Packing Slip PDFs that Reducto will fill with extracted data. You can always add or change these later.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-3">
                <Label>Bill of Lading Template</Label>
                <div
                  className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 cursor-pointer hover:border-muted-foreground/50 transition-colors"
                  onClick={() => bolInputRef.current?.click()}
                >
                  {bolFile ? (
                    <div className="text-center">
                      <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500 mb-2" />
                      <p className="text-sm font-medium">{bolFile.name}</p>
                      <Button type="button" variant="ghost" size="sm" className="mt-2"
                        onClick={e => { e.stopPropagation(); setBolFile(null) }}>Remove</Button>
                    </div>
                  ) : (
                    <div className="text-center">
                      <Upload className="mx-auto h-8 w-8 text-muted-foreground/40 mb-2" />
                      <p className="text-sm text-muted-foreground">Click to upload BOL PDF</p>
                    </div>
                  )}
                </div>
                <input ref={bolInputRef} type="file" accept=".pdf" className="hidden"
                  onChange={e => setBolFile(e.target.files?.[0] || null)} />
              </div>

              <div className="space-y-3">
                <Label>Packing Slip Template</Label>
                <div
                  className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-6 cursor-pointer hover:border-muted-foreground/50 transition-colors"
                  onClick={() => psInputRef.current?.click()}
                >
                  {psFile ? (
                    <div className="text-center">
                      <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500 mb-2" />
                      <p className="text-sm font-medium">{psFile.name}</p>
                      <Button type="button" variant="ghost" size="sm" className="mt-2"
                        onClick={e => { e.stopPropagation(); setPsFile(null) }}>Remove</Button>
                    </div>
                  ) : (
                    <div className="text-center">
                      <Upload className="mx-auto h-8 w-8 text-muted-foreground/40 mb-2" />
                      <p className="text-sm text-muted-foreground">Click to upload PS PDF</p>
                    </div>
                  )}
                </div>
                <input ref={psInputRef} type="file" accept=".pdf" className="hidden"
                  onChange={e => setPsFile(e.target.files?.[0] || null)} />
              </div>
            </div>

            <div className="flex justify-between pt-2">
              <Button variant="outline" onClick={() => setCurrentStep('address')}>
                <ArrowLeft className="mr-1.5 h-4 w-4" />Back
              </Button>
              <Button onClick={handleFinish} disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                {bolFile || psFile ? 'Upload & Finish' : 'Skip & Finish'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
