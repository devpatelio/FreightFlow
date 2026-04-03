'use client'

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { api } from '@/lib/api'

interface OrgContextValue {
  orgId: string | null
  role: string | null
  organization: {
    id: string
    name: string
    slug: string
    onboarding_completed_at: string | null
  } | null
  loading: boolean
  refresh: () => Promise<void>
}

const OrgContext = createContext<OrgContextValue>({
  orgId: null,
  role: null,
  organization: null,
  loading: true,
  refresh: async () => {},
})

export function useOrg() {
  return useContext(OrgContext)
}

export function OrgProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [state, setState] = useState<Omit<OrgContextValue, 'refresh'>>({
    orgId: null,
    role: null,
    organization: null,
    loading: true,
  })

  async function loadOrg() {
    try {
      const data = await api.get<{
        org_id: string | null
        role: string | null
        organization: OrgContextValue['organization']
      }>('/api/organizations/me')

      setState({
        orgId: data.org_id,
        role: data.role,
        organization: data.organization,
        loading: false,
      })

      if (!data.org_id || !data.organization?.onboarding_completed_at) {
        if (!pathname.startsWith('/onboarding')) {
          router.replace('/onboarding')
        }
      }
    } catch {
      setState(prev => ({ ...prev, loading: false }))
      if (!pathname.startsWith('/onboarding')) {
        router.replace('/onboarding')
      }
    }
  }

  useEffect(() => {
    loadOrg()
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <OrgContext.Provider value={{ ...state, refresh: loadOrg }}>
      {children}
    </OrgContext.Provider>
  )
}
