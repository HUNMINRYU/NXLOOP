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
            <main className="min-h-screen bg-[var(--color-background)] p-8 pt-32">
                <div className="max-w-6xl mx-auto">
                    <div className="mb-12 text-center md:text-left">
                        <h2 className="text-[var(--color-primary)] font-black uppercase tracking-widest mb-2 opacity-80">
                            Intelligence Hub
                        </h2>
                        <h1 className="text-5xl md:text-6xl font-black mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/40">
                            Analytics Center
                        </h1>
                        <p className="text-xl text-[var(--color-muted)] max-w-2xl leading-relaxed font-bold">
                            Visualize your marketing impact. Leverage Gemini's analytical power to decode viewer
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
                                <Card className="h-full border-white/5 bg-white/[0.03] backdrop-blur-xl overflow-hidden relative">
                                    <div
                                        className={`absolute -right-12 -top-12 w-24 h-24 blur-[60px] opacity-20 bg-gradient-to-br ${category.color} transition-all duration-500 group-hover:scale-150 group-hover:opacity-40`}
                                    />

                                    <div className="relative p-8 flex flex-col h-full">
                                        <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center text-4xl mb-6 ring-1 ring-white/10 group-hover:ring-white/20 transition-all">
                                            {category.icon}
                                        </div>

                                        <h3 className="text-2xl font-black mb-3 text-white group-hover:text-[var(--color-primary)] transition-colors">
                                            {category.title}
                                        </h3>

                                        <p className="text-[var(--color-muted)] font-bold mb-8 flex-grow">
                                            {category.description}
                                        </p>

                                        <div className="flex items-center text-sm font-black text-white uppercase tracking-widest group-hover:gap-2 transition-all">
                                            <span>View Reports</span>
                                            <span className="opacity-0 group-hover:opacity-100 transition-all">→</span>
                                        </div>
                                    </div>
                                </Card>
                            </Link>
                        ))}
                    </div>

                    <div className="mt-16 p-8 border border-white/5 rounded-[var(--radius-xl)] bg-white/[0.01] backdrop-blur-sm">
                        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                            <div>
                                <h4 className="text-lg font-black mb-1">Real-time Data Sync</h4>
                                <p className="text-sm text-[var(--color-muted)] font-bold">
                                    Your pipeline results and external platform data (YouTube, Naver) are aggregated
                                    every hour.
                                </p>
                            </div>
                            <Button asChild variant="secondary" className="font-black px-8">
                                <Link href="/insights">Go to Insights Hub</Link>
                            </Button>
                        </div>
                    </div>
                </div>
            </main>
        </>
    );
}
