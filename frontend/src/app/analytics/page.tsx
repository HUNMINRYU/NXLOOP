'use client';

import React from 'react';
import Link from 'next/link';
import { Navbar } from '@/features/landing';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

const analyticsCategories = [
    {
        id: 'performance',
        title: 'Performance',
        description: 'Track click-through rates (CTR), bounce rates, and engagement metrics for your videos.',
        icon: '📊',
        color: 'from-[#0ca678] to-[#12b886]',
    },
    {
        id: 'ai-insights',
        title: 'AI Insights',
        description: 'Deep-dive analysis and automated improvement plans powered by Gemini 3.0.',
        icon: '🧠',
        color: 'from-[#6366f1] to-[#818cf8]',
    },
    {
        id: 'audience',
        title: 'Audience',
        description: 'Understand viewer demographics, response trends, and sentiment analysis reports.',
        icon: '👥',
        color: 'from-[#f59e0b] to-[#fbbf24]',
    },
];

export default function AnalyticsLandingPage() {
    return (
        <>
            <Navbar />
            <main className="relative min-h-screen overflow-hidden">
                {/* Layer 1: Light Elegant Base */}
                <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />

                {/* Layer 2: Subtle Colored Wash (Analytics: indigo emphasis) */}
                <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/[0.02] via-transparent to-purple-500/[0.02]" />

                {/* Layer 3: Refined Grid Pattern */}
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

                {/* Layer 4: Ethereal Glow Orbs (Data-driven theme) */}
                <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />
                <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-purple-400/[0.06] blur-[140px] rounded-full" />

                {/* Layer 5: Accent Shimmer */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-r from-indigo-500/[0.03] to-purple-500/[0.03] blur-[100px] rounded-full" />

                {/* 콘텐츠 */}
                <div className="relative z-10 p-8 pt-32">
                    <div className="max-w-6xl mx-auto">
                    <div className="mb-12 text-center md:text-left">
                        <h2 className="font-display text-indigo-600 font-semibold uppercase tracking-[0.2em] mb-3 text-sm">
                            Intelligence Hub
                        </h2>
                        <h1 className="font-display text-5xl md:text-7xl font-bold mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 leading-[1.1]">
                            Analytics Center
                        </h1>
                        <p className="font-body text-xl text-slate-600 max-w-2xl leading-relaxed font-medium">
                            Visualize your marketing impact. Leverage Gemini&apos;s analytical power to decode viewer
                            behavior and optimize your content strategy.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {analyticsCategories.map((category) => (
                            <Link
                                key={category.id}
                                href={`/analytics/${category.id}`}
                                className="group transform transition-all duration-300 hover:-translate-y-2"
                            >
                                <Card className="h-full border-slate-200/60 bg-white/80 backdrop-blur-xl overflow-hidden relative shadow-lg shadow-slate-200/50 hover:shadow-xl hover:shadow-slate-300/50 transition-all duration-500">
                                    <div
                                        className={`absolute -right-12 -top-12 w-24 h-24 blur-[60px] opacity-[0.08] bg-gradient-to-br ${category.color} transition-all duration-500 group-hover:scale-150 group-hover:opacity-[0.15]`}
                                    />

                                    <div className="relative p-8 flex flex-col h-full">
                                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center text-4xl mb-6 ring-1 ring-slate-200/50 group-hover:ring-slate-300/70 transition-all shadow-sm">
                                            {category.icon}
                                        </div>

                                        <h3 className="font-display text-2xl font-bold mb-3 text-slate-900 group-hover:text-indigo-700 transition-colors">
                                            {category.title}
                                        </h3>

                                        <p className="font-body text-slate-600 font-medium mb-8 flex-grow leading-relaxed">
                                            {category.description}
                                        </p>

                                        <div className="flex items-center text-sm font-black text-slate-700 uppercase tracking-[0.15em] group-hover:gap-2 group-hover:text-indigo-700 transition-all">
                                            <span>View Reports</span>
                                            <span className="opacity-0 group-hover:opacity-100 transition-all">→</span>
                                        </div>
                                    </div>
                                </Card>
                            </Link>
                        ))}
                    </div>

                    <div className="mt-16 p-8 border border-slate-200/60 rounded-3xl bg-white/60 backdrop-blur-sm shadow-lg shadow-slate-200/50">
                        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                            <div>
                                <h4 className="font-display text-lg font-bold mb-2 text-slate-900">Real-time Data Sync</h4>
                                <p className="font-body text-sm text-slate-600 font-medium leading-relaxed">
                                    Your pipeline results and external platform data (YouTube, Naver) are aggregated
                                    every hour.
                                </p>
                            </div>
                            <Button asChild variant="secondary" className="font-display font-semibold px-8 bg-slate-900 hover:bg-slate-800 text-white">
                                <Link href="/insights">Go to Insights Hub</Link>
                            </Button>
                        </div>
                    </div>
                </div>
                </div>
            </main>
        </>
    );
}
