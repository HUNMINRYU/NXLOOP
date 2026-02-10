'use client';

import Link from 'next/link';
import { Navbar } from '@/features/landing';
import { Button } from '@/components/ui';
import { useAnalytics } from '@/features/pipeline/hooks/useAnalytics';
import { PerformanceSection, AiInsightsSection } from '@/features/pipeline/components/AnalyticsSections';

const slugs: Record<string, { title: string; subtitle: string }> = {
  performance: { title: 'Performance', subtitle: 'Click-through rate (CTR) and bounce rate data' },
  'ai-insights': { title: 'AI Insights', subtitle: 'Feedback and improvement plans for each video' },
  audience: { title: 'Audience', subtitle: 'Viewer response and trend analysis report' },
};

type AnalyticsSlugClientProps = {
  slug: string;
};

export default function AnalyticsSlugClient({ slug }: AnalyticsSlugClientProps) {
  const item = slugs[slug];
  const analytics = useAnalytics(slug);

  if (!item) {
    return (
      <>
        <Navbar />
        <main className="relative min-h-screen overflow-hidden flex flex-col items-center justify-center">
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

          <div className="relative z-10 p-8">
            <div className="max-w-2xl text-center p-8 border border-slate-200/60 bg-white/80 backdrop-blur-xl rounded-3xl shadow-lg shadow-slate-200/50">
              <h1 className="text-4xl font-bold text-slate-900">Not Found</h1>
              <p className="mt-2 text-slate-600">The page you&apos;re looking for doesn&apos;t exist.</p>
              <Button asChild className="mt-8 bg-slate-900 hover:bg-slate-800 text-white">
                <Link href="/">Back Home</Link>
              </Button>
            </div>
          </div>
        </main>
      </>
    );
  }

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
        <div className="max-w-5xl mx-auto space-y-8">
          <header>
            <p className="font-display font-semibold text-indigo-600 uppercase tracking-[0.2em] text-sm">Analytics</p>
            <h1 className="font-display text-4xl md:text-5xl font-bold text-slate-900 mt-2">{item.title}</h1>
            <p className="font-body text-lg text-slate-600 mt-2">{item.subtitle}</p>
          </header>

          {analytics.isLoading && <p className="text-sm text-slate-600 font-medium">로딩 중...</p>}
          {analytics.error && <p className="text-sm text-rose-600 font-medium">{analytics.error}</p>}

          {slug === 'performance' && <PerformanceSection {...analytics} />}
          {slug === 'ai-insights' && <AiInsightsSection {...analytics} />}

          <div className="mt-8">
            <Button asChild variant="secondary" className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">
              <Link href="/">Back to Home</Link>
            </Button>
          </div>
        </div>
        </div>
      </main>
    </>
  );
}
