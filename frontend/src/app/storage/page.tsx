'use client';

import React from 'react';
import Link from 'next/link';
import { Film, Images, FileText } from 'lucide-react';
import { Navbar } from '@/features/landing';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

const storageCategories = [
    {
        id: 'video-vault',
        title: 'Video Vault',
        description: 'Storage for completed short-form videos and generated creative clips.',
        icon: Film,
        color: 'from-[#0ca678] to-[#12b886]',
    },
    {
        id: 'asset-library',
        title: 'Asset Library',
        description: 'Management of generated thumbnails, multi-factor images, and source assets.',
        icon: Images,
        color: 'from-[#6366f1] to-[#818cf8]',
    },
    {
        id: 'prompt-log',
        title: 'Prompt Log',
        description: 'History and cache management of successful prompts and AI responses.',
        icon: FileText,
        color: 'from-[#f59e0b] to-[#fbbf24]',
    },
];

export default function StorageLandingPage() {
    return (
        <>
            <Navbar />
            <main className="relative min-h-screen overflow-hidden">
                {/* Layer 1: 베이스 그라디언트 */}
                <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950" />

                {/* Layer 2: 그리드 패턴 */}
                <div
                    className="absolute inset-0 opacity-[0.02]"
                    style={{
                        backgroundImage: `
                            linear-gradient(to right, white 1px, transparent 1px),
                            linear-gradient(to bottom, white 1px, transparent 1px)
                        `,
                        backgroundSize: '80px 80px',
                    }}
                />

                {/* Layer 3: 글로우 오브들 */}
                <div className="absolute top-20 left-10 w-[500px] h-[500px] bg-teal-500/10 blur-[120px] rounded-full animate-pulse" />
                <div
                    className="absolute bottom-20 right-10 w-[500px] h-[500px] bg-indigo-500/10 blur-[120px] rounded-full animate-pulse"
                    style={{ animationDelay: '1s' }}
                />

                {/* 실제 콘텐츠 */}
                <div className="relative z-10 p-8 pt-32">
                    <div className="max-w-6xl mx-auto">
                    <div className="mb-12 text-center md:text-left">
                        <h2 className="font-display text-[var(--color-primary)] font-semibold uppercase tracking-widest mb-2 opacity-80">
                            Nexus of Assets
                        </h2>
                        <h1 className="font-display text-5xl md:text-6xl font-bold mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/40">
                            Storage Center
                        </h1>
                        <p className="font-body text-xl text-[var(--color-muted)] max-w-2xl leading-relaxed font-medium">
                            Organize and manage your AI-generated marketing assets in one secure place. Connect your
                            brand data with limitless storage possibilities.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        {/* Video Vault: 2 columns + 2 rows */}
                        <Link
                            href="/storage/video-vault"
                            className="md:col-span-2 md:row-span-2 group transform transition-all duration-300 hover:-translate-y-2 animate-fade-in-up opacity-0"
                            style={{ animationDelay: '0ms', animationFillMode: 'forwards' }}
                        >
                            <Card className="h-full border-white/5 bg-white/[0.03] backdrop-blur-xl overflow-hidden relative">
                                {/* 배경 글로우 (크게) */}
                                <div className="absolute -right-20 -top-20 w-40 h-40 blur-[80px] opacity-20 bg-gradient-to-br from-[#0ca678] to-[#12b886] transition-all duration-500 group-hover:scale-150 group-hover:opacity-40" />

                                <div className="relative p-12 flex flex-col h-full justify-center">
                                    {/* 아이콘 (크게) */}
                                    <div className="w-24 h-24 rounded-3xl bg-white/5 flex items-center justify-center mb-8 ring-1 ring-white/10 group-hover:ring-white/20 transition-all relative overflow-hidden">
                                        <div className="absolute inset-0 bg-gradient-to-br from-[#0ca678] to-[#12b886] opacity-0 group-hover:opacity-20 transition-opacity blur-sm" />
                                        <Film
                                            className="relative w-12 h-12 text-white/80 group-hover:text-white group-hover:scale-110 transition-all"
                                            strokeWidth={1.5}
                                        />
                                    </div>

                                    <h3 className="font-display text-4xl font-semibold mb-4 text-white group-hover:text-[var(--color-primary)] transition-colors">
                                        Video Vault
                                    </h3>

                                    <p className="font-body text-lg text-[var(--color-muted)] font-medium mb-12 max-w-md">
                                        Storage for completed short-form videos and generated creative clips.
                                    </p>

                                    <div className="flex items-center text-sm font-black text-white uppercase tracking-widest group-hover:gap-2 transition-all mt-auto">
                                        <span>Explore</span>
                                        <span className="opacity-0 group-hover:opacity-100 transition-all">→</span>
                                    </div>
                                </div>
                            </Card>
                        </Link>

                        {/* Asset Library: 2 columns + 1 row */}
                        <Link
                            href="/storage/asset-library"
                            className="md:col-span-2 group transform transition-all duration-300 hover:-translate-y-2 animate-fade-in-up opacity-0"
                            style={{ animationDelay: '100ms', animationFillMode: 'forwards' }}
                        >
                            <Card className="h-full border-white/5 bg-white/[0.03] backdrop-blur-xl overflow-hidden relative">
                                <div className="absolute -right-12 -top-12 w-24 h-24 blur-[60px] opacity-20 bg-gradient-to-br from-[#6366f1] to-[#818cf8] transition-all duration-500 group-hover:scale-150 group-hover:opacity-40" />

                                <div className="relative p-8 flex flex-col h-full">
                                    <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-6 ring-1 ring-white/10 group-hover:ring-white/20 transition-all relative overflow-hidden">
                                        <div className="absolute inset-0 bg-gradient-to-br from-[#6366f1] to-[#818cf8] opacity-0 group-hover:opacity-20 transition-opacity blur-sm" />
                                        <Images
                                            className="relative w-8 h-8 text-white/80 group-hover:text-white group-hover:scale-110 transition-all"
                                            strokeWidth={1.5}
                                        />
                                    </div>

                                    <h3 className="font-display text-2xl font-semibold mb-3 text-white group-hover:text-[var(--color-primary)] transition-colors">
                                        Asset Library
                                    </h3>

                                    <p className="font-body text-[var(--color-muted)] font-medium mb-8 flex-grow">
                                        Management of generated thumbnails, multi-factor images, and source assets.
                                    </p>

                                    <div className="flex items-center text-sm font-black text-white uppercase tracking-widest group-hover:gap-2 transition-all">
                                        <span>Explore</span>
                                        <span className="opacity-0 group-hover:opacity-100 transition-all">→</span>
                                    </div>
                                </div>
                            </Card>
                        </Link>

                        {/* Prompt Log: 2 columns + 1 row */}
                        <Link
                            href="/storage/prompt-log"
                            className="md:col-span-2 group transform transition-all duration-300 hover:-translate-y-2 animate-fade-in-up opacity-0"
                            style={{ animationDelay: '200ms', animationFillMode: 'forwards' }}
                        >
                            <Card className="h-full border-white/5 bg-white/[0.03] backdrop-blur-xl overflow-hidden relative">
                                <div className="absolute -right-12 -top-12 w-24 h-24 blur-[60px] opacity-20 bg-gradient-to-br from-[#f59e0b] to-[#fbbf24] transition-all duration-500 group-hover:scale-150 group-hover:opacity-40" />

                                <div className="relative p-8 flex flex-col h-full">
                                    <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-6 ring-1 ring-white/10 group-hover:ring-white/20 transition-all relative overflow-hidden">
                                        <div className="absolute inset-0 bg-gradient-to-br from-[#f59e0b] to-[#fbbf24] opacity-0 group-hover:opacity-20 transition-opacity blur-sm" />
                                        <FileText
                                            className="relative w-8 h-8 text-white/80 group-hover:text-white group-hover:scale-110 transition-all"
                                            strokeWidth={1.5}
                                        />
                                    </div>

                                    <h3 className="font-display text-2xl font-semibold mb-3 text-white group-hover:text-[var(--color-primary)] transition-colors">
                                        Prompt Log
                                    </h3>

                                    <p className="font-body text-[var(--color-muted)] font-medium mb-8 flex-grow">
                                        History and cache management of successful prompts and AI responses.
                                    </p>

                                    <div className="flex items-center text-sm font-black text-white uppercase tracking-widest group-hover:gap-2 transition-all">
                                        <span>Explore</span>
                                        <span className="opacity-0 group-hover:opacity-100 transition-all">→</span>
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    </div>

                    <div className="mt-16 p-8 border border-white/5 rounded-[var(--radius-xl)] bg-white/[0.01] backdrop-blur-sm">
                        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                            <div>
                                <h4 className="font-display text-lg font-semibold mb-1 text-white">GCS (Google Cloud Storage) Linked</h4>
                                <p className="font-body text-sm text-[var(--color-muted)] font-medium">
                                    All assets are securely stored in your enterprise VPC bucket with 99.99% durability.
                                </p>
                            </div>
                            <Button asChild variant="secondary" className="font-display font-semibold px-8">
                                <Link href="/pipeline">Return to Pipeline</Link>
                            </Button>
                        </div>
                    </div>
                </div>
                </div>
            </main>
        </>
    );
}
