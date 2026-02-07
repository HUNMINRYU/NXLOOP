'use client';

import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';

export default function VideoMessageSection() {
    return (
        <section className="relative py-24 md:py-32 px-6 md:px-12 border-t border-slate-200/60 bg-white overflow-hidden">
            <div
                className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-indigo-500/10 blur-[120px]"
                aria-hidden
            />
            <div
                className="absolute -bottom-32 -left-32 w-96 h-96 rounded-full bg-teal-500/10 blur-[120px]"
                aria-hidden
            />

            <div className="relative max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 md:gap-20 items-center">
                {/* Left: Video / Visual Container - 9:16 portrait */}
                <div className="relative transform hover:rotate-1 transition-transform duration-700">
                    <Card className="rounded-3xl overflow-hidden bg-white/80 backdrop-blur-xl border-2 border-slate-200/60 p-5 md:p-8 shadow-2xl shadow-slate-200/50 w-full max-w-[360px] mx-auto lg:mx-0">
                        <div className="flex items-center gap-2 mb-6">
                            <Link href="/" className="font-display text-2xl font-bold tracking-tight">
                                NEX
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-indigo-600">
                                    LOOP
                                </span>
                            </Link>
                        </div>
                        {/* Video / Graphic Area - 9:16 portrait (stable image) */}
                        <div className="relative aspect-[9/16] w-full rounded-2xl overflow-hidden bg-slate-100 border-2 border-slate-200 shadow-inner">
                            <img
                                src="https://picsum.photos/360/640?seed=intro"
                                alt="Introducing NEXLOOP"
                                className="absolute inset-0 w-full h-full object-cover transition-transform duration-1000 hover:scale-110"
                            />
                            <div className="absolute inset-0 opacity-[0.4] group-hover:opacity-[0.3] mix-blend-overlay transition-opacity pointer-events-none">
                                <img
                                    src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExYnFwZzB3eXNqZzB3eXNqZzB3eXNqZzB3eXNqZzB3eXNqZzB3eCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o7TKMGpxP5OqP80vK/giphy.gif"
                                    alt="overlay-grain"
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <div className="absolute bottom-6 right-6 w-16 h-16 rounded-full bg-teal-600/90 backdrop-blur-md border-2 border-teal-400/50 flex items-center justify-center text-white font-black text-xs tracking-widest shadow-lg hover:scale-110 transition-transform cursor-pointer">
                                PLAY
                            </div>
                        </div>
                    </Card>
                </div>

                {/* Right: Message - light elegant style */}
                <div className="relative">
                    <Card className="rounded-3xl bg-gradient-to-br from-white/90 to-white/70 border-2 border-slate-200/60 backdrop-blur-xl p-8 md:p-16 flex flex-col justify-center min-h-[400px] shadow-2xl shadow-slate-200/50 overflow-hidden group">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-teal-500/10 to-transparent blur-3xl opacity-50 group-hover:opacity-100 transition-opacity duration-1000" />

                        <h2 className="relative font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold leading-tight mb-6 md:mb-8 tracking-tight text-slate-900">
                            Our
                            <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-indigo-600">
                                Pipeline
                            </span>
                            <br />
                            <span className="inline-block mt-2 relative">
                                Automation That Never Sleeps
                                <div className="absolute -bottom-2 left-0 w-full h-2 bg-teal-600 rounded-full transform scale-x-105" />
                            </span>
                        </h2>
                        <p className="relative font-body text-lg md:text-2xl font-medium text-slate-600 max-w-lg leading-relaxed">
                            Set your goals. Let Gemini&apos;s machine intelligence bridge the gap between concept and
                            creation.
                        </p>
                    </Card>
                </div>
            </div>
        </section>
    );
}
