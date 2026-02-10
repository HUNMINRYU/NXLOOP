'use client';

import React from 'react';
import Link from 'next/link';
import { Film, Images, FileText } from 'lucide-react';
import { Navbar } from '@/features/landing';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function StorageLandingPage() {
    return (
        <>
            <Navbar />
            <main className="relative min-h-screen overflow-hidden">
                {/* Layer 1: Light Elegant Base */}
                <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />

                {/* Layer 2: Subtle Colored Wash */}
                <div className="absolute inset-0 bg-gradient-to-tr from-teal-500/[0.02] via-transparent to-indigo-500/[0.02]" />

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

                {/* Layer 4: Ethereal Glow Orbs */}
                <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-teal-400/[0.06] blur-[140px] rounded-full" />
                <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />

                {/* Layer 5: Accent Shimmer */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-r from-teal-500/[0.03] to-indigo-500/[0.03] blur-[100px] rounded-full" />

                {/* 실제 콘텐츠 */}
                <div className="relative z-10 p-8 pt-32">
                    <div className="max-w-6xl mx-auto">
                    <div className="mb-12 text-center md:text-left">
                        <h2 className="font-display text-teal-600 font-semibold uppercase tracking-[0.2em] mb-3 text-sm">
                            Nexus of Assets
                        </h2>
                        <h1 className="font-display text-5xl md:text-7xl font-bold mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 leading-[1.1]">
                            Storage Center
                        </h1>
                        <p className="font-body text-xl text-slate-600 max-w-2xl leading-relaxed font-medium">
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
                            <Card className="h-full border-slate-200/60 bg-white/80 backdrop-blur-xl overflow-hidden relative shadow-lg shadow-slate-200/50 hover:shadow-xl hover:shadow-slate-300/50 transition-all duration-500">
                                {/* 배경 글로우 (크게) */}
                                <div className="absolute -right-20 -top-20 w-40 h-40 blur-[80px] opacity-[0.08] bg-gradient-to-br from-[#0ca678] to-[#12b886] transition-all duration-500 group-hover:scale-150 group-hover:opacity-[0.15]" />

                                <div className="relative p-12 flex flex-col h-full justify-center">
                                    {/* 아이콘 (크게) */}
                                    <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-teal-50 to-teal-100 flex items-center justify-center mb-8 ring-1 ring-teal-200/50 group-hover:ring-teal-300/70 transition-all relative overflow-hidden shadow-sm">
                                        <div className="absolute inset-0 bg-gradient-to-br from-[#0ca678] to-[#12b886] opacity-0 group-hover:opacity-10 transition-opacity" />
                                        <Film
                                            className="relative w-12 h-12 text-teal-600 group-hover:text-teal-700 group-hover:scale-110 transition-all"
                                            strokeWidth={1.5}
                                        />
                                    </div>

                                    <h3 className="font-display text-4xl font-bold mb-4 text-slate-900 group-hover:text-teal-700 transition-colors">
                                        Video Vault
                                    </h3>

                                    <p className="font-body text-lg text-slate-600 font-medium mb-12 max-w-md leading-relaxed">
                                        Storage for completed short-form videos and generated creative clips.
                                    </p>

                                    <div className="flex items-center text-sm font-black text-slate-700 uppercase tracking-[0.15em] group-hover:gap-2 group-hover:text-teal-700 transition-all mt-auto">
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
                            <Card className="h-full border-slate-200/60 bg-white/80 backdrop-blur-xl overflow-hidden relative shadow-lg shadow-slate-200/50 hover:shadow-xl hover:shadow-slate-300/50 transition-all duration-500">
                                <div className="absolute -right-12 -top-12 w-24 h-24 blur-[60px] opacity-[0.08] bg-gradient-to-br from-[#6366f1] to-[#818cf8] transition-all duration-500 group-hover:scale-150 group-hover:opacity-[0.15]" />

                                <div className="relative p-8 flex flex-col h-full">
                                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-50 to-indigo-100 flex items-center justify-center mb-6 ring-1 ring-indigo-200/50 group-hover:ring-indigo-300/70 transition-all relative overflow-hidden shadow-sm">
                                        <div className="absolute inset-0 bg-gradient-to-br from-[#6366f1] to-[#818cf8] opacity-0 group-hover:opacity-10 transition-opacity" />
                                        <Images
                                            className="relative w-8 h-8 text-indigo-600 group-hover:text-indigo-700 group-hover:scale-110 transition-all"
                                            strokeWidth={1.5}
                                        />
                                    </div>

                                    <h3 className="font-display text-2xl font-bold mb-3 text-slate-900 group-hover:text-indigo-700 transition-colors">
                                        Asset Library
                                    </h3>

                                    <p className="font-body text-slate-600 font-medium mb-8 flex-grow leading-relaxed">
                                        Management of generated thumbnails, multi-factor images, and source assets.
                                    </p>

                                    <div className="flex items-center text-sm font-black text-slate-700 uppercase tracking-[0.15em] group-hover:gap-2 group-hover:text-indigo-700 transition-all">
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
                            <Card className="h-full border-slate-200/60 bg-white/80 backdrop-blur-xl overflow-hidden relative shadow-lg shadow-slate-200/50 hover:shadow-xl hover:shadow-slate-300/50 transition-all duration-500">
                                <div className="absolute -right-12 -top-12 w-24 h-24 blur-[60px] opacity-[0.08] bg-gradient-to-br from-[#f59e0b] to-[#fbbf24] transition-all duration-500 group-hover:scale-150 group-hover:opacity-[0.15]" />

                                <div className="relative p-8 flex flex-col h-full">
                                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-50 to-amber-100 flex items-center justify-center mb-6 ring-1 ring-amber-200/50 group-hover:ring-amber-300/70 transition-all relative overflow-hidden shadow-sm">
                                        <div className="absolute inset-0 bg-gradient-to-br from-[#f59e0b] to-[#fbbf24] opacity-0 group-hover:opacity-10 transition-opacity" />
                                        <FileText
                                            className="relative w-8 h-8 text-amber-600 group-hover:text-amber-700 group-hover:scale-110 transition-all"
                                            strokeWidth={1.5}
                                        />
                                    </div>

                                    <h3 className="font-display text-2xl font-bold mb-3 text-slate-900 group-hover:text-amber-700 transition-colors">
                                        Prompt Log
                                    </h3>

                                    <p className="font-body text-slate-600 font-medium mb-8 flex-grow leading-relaxed">
                                        History and cache management of successful prompts and AI responses.
                                    </p>

                                    <div className="flex items-center text-sm font-black text-slate-700 uppercase tracking-[0.15em] group-hover:gap-2 group-hover:text-amber-700 transition-all">
                                        <span>Explore</span>
                                        <span className="opacity-0 group-hover:opacity-100 transition-all">→</span>
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    </div>

                    <div className="mt-16 p-8 border border-slate-200/60 rounded-3xl bg-white/60 backdrop-blur-sm shadow-lg shadow-slate-200/50">
                        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                            <div>
                                <h4 className="font-display text-lg font-bold mb-2 text-slate-900">GCS (Google Cloud Storage) Linked</h4>
                                <p className="font-body text-sm text-slate-600 font-medium leading-relaxed">
                                    All assets are securely stored in your enterprise VPC bucket with 99.99% durability.
                                </p>
                            </div>
                            <Button asChild variant="secondary" className="font-display font-semibold px-8 bg-slate-900 hover:bg-slate-800 text-white">
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
