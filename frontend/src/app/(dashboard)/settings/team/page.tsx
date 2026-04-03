'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { UserPlus, Trash2, Mail, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useOrg } from '@/lib/org-context'
import type { UserProfile } from '@/lib/types'

interface Member {
  id: string
  user_id: string
  role: string
  created_at: string
}

interface Invitation {
  id: string
  email: string
  role: string
  created_at: string
}

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-amber-100 text-amber-800 border-amber-200',
  admin: 'bg-blue-100 text-blue-800 border-blue-200',
  member: 'bg-gray-100 text-gray-800 border-gray-200',
}

function initials(profile: UserProfile | undefined): string {
  if (!profile?.display_name) return '?'
  return profile.display_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

export default function TeamPage() {
  const { role: myRole } = useOrg()
  const [members, setMembers] = useState<Member[]>([])
  const [profiles, setProfiles] = useState<Record<string, UserProfile>>({})
  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [loading, setLoading] = useState(true)

  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteOpen, setInviteOpen] = useState(false)

  const isOwner = myRole === 'owner'
  const isAdmin = myRole === 'admin' || isOwner

  useEffect(() => { loadAll() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadAll() {
    setLoading(true)
    try {
      const [m, i] = await Promise.all([
        api.get<Member[]>('/api/organizations/members'),
        api.get<Invitation[]>('/api/organizations/invitations'),
      ])
      setMembers(m)
      setInvitations(i)

      const userIds = m.map(member => member.user_id)
      if (userIds.length > 0) {
        const resolved = await api.post<Record<string, UserProfile>>('/api/profile/resolve', { user_ids: userIds })
        setProfiles(resolved)
      }
    } catch (err) {
      console.error('Failed to load team data', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleInvite() {
    if (!inviteEmail) return
    setInviteLoading(true)
    try {
      await api.post('/api/organizations/invitations', { email: inviteEmail, role: inviteRole })
      setInviteEmail('')
      setInviteRole('member')
      setInviteOpen(false)
      loadAll()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to send invitation')
    } finally {
      setInviteLoading(false)
    }
  }

  async function handleRevokeInvite(id: string) {
    if (!confirm('Revoke this invitation?')) return
    await api.delete(`/api/organizations/invitations/${id}`)
    setInvitations(prev => prev.filter(inv => inv.id !== id))
  }

  async function handleChangeRole(memberId: string, newRole: string) {
    try {
      await api.patch(`/api/organizations/members/${memberId}`, { role: newRole })
      setMembers(prev => prev.map(m => m.id === memberId ? { ...m, role: newRole } : m))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to change role')
    }
  }

  async function handleRemoveMember(memberId: string) {
    if (!confirm('Remove this member from the organization?')) return
    try {
      await api.delete(`/api/organizations/members/${memberId}`)
      setMembers(prev => prev.filter(m => m.id !== memberId))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to remove member')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Team</h1>
          <p className="text-muted-foreground">Manage members and invitations for your organization</p>
        </div>
        {isAdmin && (
          <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
            <DialogTrigger className="inline-flex">
              <Button><UserPlus className="mr-2 h-4 w-4" />Invite Member</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Invite a team member</DialogTitle>
                <DialogDescription>
                  Send an invitation by email. They will be able to accept it during signup or from their dashboard.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <div className="space-y-2">
                  <Label>Email Address</Label>
                  <Input placeholder="colleague@company.com" type="email" value={inviteEmail}
                    onChange={e => setInviteEmail(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Role</Label>
                  <Select value={inviteRole} onValueChange={(v) => v && setInviteRole(v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">Member</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                      {isOwner && <SelectItem value="owner">Owner</SelectItem>}
                    </SelectContent>
                  </Select>
                </div>
                <Button className="w-full" onClick={handleInvite} disabled={inviteLoading || !inviteEmail}>
                  {inviteLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Mail className="mr-2 h-4 w-4" />}
                  Send Invitation
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Members */}
      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>{members.length} member{members.length !== 1 ? 's' : ''}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Joined</TableHead>
                  {isOwner && <TableHead className="w-[100px]">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map(m => {
                  const profile = profiles[m.user_id]
                  return (
                    <TableRow key={m.id}>
                      <TableCell>
                        <div className="flex items-center gap-2.5">
                          <Avatar className="h-7 w-7">
                            <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                              {initials(profile)}
                            </AvatarFallback>
                          </Avatar>
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate">
                              {profile?.display_name || 'No name set'}
                            </p>
                            <p className="text-xs text-muted-foreground font-mono truncate">
                              {m.user_id.slice(0, 8)}...
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {isOwner ? (
                          <Select value={m.role} onValueChange={v => v && handleChangeRole(m.id, v)}>
                            <SelectTrigger className="h-7 w-28">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="member">member</SelectItem>
                              <SelectItem value="admin">admin</SelectItem>
                              <SelectItem value="owner">owner</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge variant="outline" className={ROLE_COLORS[m.role] || ''}>
                            {m.role}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(m.created_at).toLocaleDateString()}
                      </TableCell>
                      {isOwner && (
                        <TableCell>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                            onClick={() => handleRemoveMember(m.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pending invitations */}
      {isAdmin && invitations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Pending Invitations</CardTitle>
            <CardDescription>{invitations.length} pending</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Sent</TableHead>
                  <TableHead className="w-[80px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {invitations.map(inv => (
                  <TableRow key={inv.id}>
                    <TableCell>{inv.email}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={ROLE_COLORS[inv.role] || ''}>
                        {inv.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(inv.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                        onClick={() => handleRevokeInvite(inv.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
