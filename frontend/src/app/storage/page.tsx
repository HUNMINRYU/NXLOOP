'use client';

import React from 'react';
import Link from 'next/link';
import { Navbar } from '@/features/landing';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

const storageCategories = [
    {
        id: 'video-vault',
        title: 'Video Vault',
        description: 'Storage for completed short-form videos and generated creative clips.',
        icon: '🎬',
        color: 'from-[#0ca678] to-[#12b886]',
    },
    {
        id: 'asset-library',
        title: 'Asset Library',
        description: 'Management of generated thumbnails, multi-factor images, and source assets.',
        icon: '🖼️',
        color: 'from-[#6366f1] to-[#818cf8]',
    },
    {
        id: 'prompt-log',
        title: 'Prompt Log',
        description: 'History and cache management of successful prompts and AI responses.',
        icon: '📝',
        color: 'from-[#f59e0b] to-[#fbbf24]',
    },
];

export default function StorageLandingPage() {
    return (
        <>
            <Navbar />
            <main className="min-h-screen bg-[var(--color-background)] p-8 pt-32">
                <div className="max-w-6xl mx-auto">
                    <div className="mb-12 text-center md:text-left">
                        <h2 className="text-[var(--color-primary)] font-black uppercase tracking-widest mb-2 opacity-80">
                            Nexus of Assets
                        </h2>
                        <h1 className="text-5xl md:text-6xl font-black mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/40">
                            Storage Center
                        </h1>
                        <p className="text-xl text-[var(--color-muted)] max-w-2xl leading-relaxed font-bold">
                            Organize and manage your AI-generated marketing assets in one secure place. Connect your
                            brand data with limitless storage possibilities.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {storageCategories.map((category) => (
                            <Link
                                key={category.id}
                                href={`/storage/${category.id}`}
                                className="group transform transition-all duration-300 hover:-translate-y-2"
                            >
                                <Card className="h-full border-white/5 bg-white/[0.03] backdrop-blur-xl overflow-hidden relative">
                                    {/* Background Glow */}
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
                                            <span>Explore</span>
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
                                <h4 className="text-lg font-black mb-1">GCS (Google Cloud Storage) Linked</h4>
                                <p className="text-sm text-[var(--color-muted)] font-bold">
                                    All assets are securely stored in your enterprise VPC bucket with 99.99% durability.
                                </p>
                            </div>
                            <Button asChild variant="secondary" className="font-black px-8">
                                <Link href="/pipeline">Return to Pipeline</Link>
                            </Button>
                        </div>
                    </div>
                </div>
            </main>
        </>
    );
}
