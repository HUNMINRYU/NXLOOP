import { Navbar } from '@/features/landing';

export default function AdminLayout({
  children,
  cache,
  gcs,
  prompts,
  notion,
}: {
  children: React.ReactNode;
  cache: React.ReactNode;
  gcs: React.ReactNode;
  prompts: React.ReactNode;
  notion: React.ReactNode;
}) {
  return (
    <>
      <Navbar />
      <main className="relative min-h-screen overflow-hidden">
        {/* Light Elegant Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
        <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/[0.02] via-transparent to-purple-500/[0.02]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgb(15 23 42 / 0.08) 1px, transparent 1px),
              linear-gradient(to bottom, rgb(15 23 42 / 0.08) 1px, transparent 1px)
            `,
            backgroundSize: '80px 80px',
          }}
        />
        <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />
        <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-purple-400/[0.06] blur-[140px] rounded-full" />

        <div className="relative z-10 p-8 pt-24">
        <div className="max-w-6xl mx-auto space-y-8">
          {children}
          <div className="grid gap-8">
            {cache}
            {gcs}
            {prompts}
            {notion}
          </div>
        </div>
        </div>
      </main>
    </>
  );
}
