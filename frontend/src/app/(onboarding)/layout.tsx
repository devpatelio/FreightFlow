import Image from 'next/image'

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto flex h-16 max-w-3xl items-center px-6">
          <div className="flex items-center gap-2">
            <Image src="/logo_black.png" alt="FreightFlow" width={32} height={32} className="rounded-lg" />
            <span className="text-lg font-semibold tracking-tight">FreightFlow</span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">
        {children}
      </main>
    </div>
  )
}
