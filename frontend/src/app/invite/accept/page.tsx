'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Image from 'next/image'
import { createClient } from '@/lib/supabase'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'
import Link from 'next/link'

export default function InviteAcceptPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const invitationId = searchParams.get('invitation_id')

  const [status, setStatus] = useState<'loading' | 'unauthenticated' | 'accepting' | 'error' | 'done'>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!invitationId) {
      setError('Invalid invite link — no invitation ID found.')
      setStatus('error')
      return
    }

    async function tryAccept() {
      const supabase = createClient()
      const { data: { user } } = await supabase.auth.getUser()

      if (!user) {
        setStatus('unauthenticated')
        return
      }

      setStatus('accepting')
      try {
        await api.post(`/api/organizations/invitations/${invitationId}/accept`, {})
        setStatus('done')
        setTimeout(() => router.push('/'), 1500)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to accept invitation')
        setStatus('error')
      }
    }

    tryAccept()
  }, [invitationId, router])

  const loginUrl = `/login?redirect=/invite/accept?invitation_id=${invitationId}`
  const signupUrl = `/signup?redirect=/invite/accept?invitation_id=${invitationId}`

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <Image src="/logo_black.png" alt="FreightFlow" width={48} height={48} className="mx-auto mb-4 rounded-xl" />
          <CardTitle className="text-2xl">You&apos;ve been invited</CardTitle>
          <CardDescription>Accept your invitation to join the organization</CardDescription>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          {status === 'loading' && (
            <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
          )}

          {status === 'unauthenticated' && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">Sign in or create an account to accept this invitation.</p>
              <div className="flex flex-col gap-2">
                <Button asChild>
                  <Link href={loginUrl}>Sign in to accept</Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link href={signupUrl}>Create an account</Link>
                </Button>
              </div>
            </div>
          )}

          {status === 'accepting' && (
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Accepting invitation...
            </div>
          )}

          {status === 'done' && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
              You&apos;ve joined the organization! Redirecting...
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-3">
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
              <Link href="/" className="text-sm text-primary hover:underline">
                Go to dashboard
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
