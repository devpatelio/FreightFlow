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
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
              FF
            </div>
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
