'use client';

import React from 'react';
import { Tooltip } from '@/components/ui';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

type HeroProps = {
    demoUrl: string;
};

export default function Hero({ demoUrl }: HeroProps) {
    return (
        <section className="relative pt-32 pb-24 px-8 bg-[var(--color-background)] min-h-screen flex flex-col items-center justify-center text-center overflow-hidden">
            {/* Background Video */}
            <video
                autoPlay
                loop
                muted
                playsInline
                className="absolute inset-0 w-full h-full object-cover pointer-events-none z-0"
            >
                <source src="/videos/Video.mp4" type="video/mp4" />
            </video>

            {/* Dark Overlay for Readability - Enhanced */}
            <div className="absolute inset-0 bg-black/60 z-[1] pointer-events-none"></div>

            {/* Background Grid Pattern */}
            <div className="absolute inset-0 bg-grid opacity-20 z-[2] pointer-events-none"></div>

            <div className="relative z-10 max-w-4xl text-center">
                {/* Unified Tagline with premium glow */}
                <div className="inline-flex items-center gap-2 px-6 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 shadow-[0_0_20px_rgba(255,255,255,0.1)] mb-10 animate-fade-in-up">
                    <span className="w-2 h-2 rounded-full bg-[#0ca678] animate-pulse" />
                    <span className="text-lg md:text-xl font-bold text-white tracking-wide">
                        From planning to analysis: The seamless automation
                    </span>
                </div>

                {/* Brand title with heavy shadow and gradient */}
                <h1 className="text-6xl sm:text-8xl md:text-9xl lg:text-[10rem] font-black tracking-tighter mb-8 leading-[0.85] drop-shadow-2xl text-white px-4 animate-fade-in-up [animation-delay:200ms]">
                    NEX
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#0ca678] via-[#6366f1] to-[#0ca678] animate-gradient-x">
                        LOOP
                    </span>
                </h1>

                <p className="text-lg sm:text-2xl font-medium mb-12 max-w-2xl mx-auto px-6 text-slate-200 leading-relaxed animate-fade-in-up [animation-delay:400ms]">
                    Set your goals, then let Gemini’s intelligence bridge the gap.
                    <br className="hidden md:block" />
                    Your video is already ready.
                </p>

                <div className="flex flex-col gap-4 sm:gap-6 items-center animate-fade-in-up [animation-delay:600ms]">
                    <div className="flex flex-wrap gap-4 sm:gap-6 justify-center">
                        {/* Primary CTA - Enhanced hierarchy */}
                        <Tooltip content="Start with NEXLOOP pipeline" position="bottom">
                            <Button
                                variant="default"
                                className="text-xl font-bold px-12 py-7 rounded-full bg-teal-600 hover:bg-teal-500 hover:scale-105 transition-all duration-300 shadow-[0_0_50px_rgba(13,148,136,0.5)] border-2 border-teal-400/50 text-white"
                            >
                                Get Started
                            </Button>
                        </Tooltip>
                        {/* Secondary CTA - Ghost button */}
                        <Button
                            asChild
                            variant="outline"
                            className="text-xl font-semibold px-12 py-7 rounded-full bg-transparent text-white border-2 border-white/40 hover:bg-white/10 hover:border-white/60 backdrop-blur-sm transition-all duration-300"
                        >
                            <a href={demoUrl}>View Demo</a>
                        </Button>
                    </div>
                </div>
            </div>

            {/* Tech Badges - Unified colors */}
            <div className="relative z-10 mt-16 w-full max-w-5xl grid grid-cols-1 sm:grid-cols-3 gap-6 md:gap-8 px-2">
                <Card className="bg-white/10 backdrop-blur-md border-white/20 rotate-0 sm:rotate-[-2deg] p-6 md:p-8 min-h-[140px] text-white cursor-pointer hover:bg-white/20 hover:-translate-y-1 transition-all duration-300 group">
                    <div className="w-10 h-10 rounded-full bg-teal-500/40 border border-teal-400/30 mb-3 group-hover:scale-110 transition-transform flex items-center justify-center">
                        <span className="text-teal-300 text-sm font-bold">AI</span>
                    </div>
                    <h3 className="font-bold text-xl mb-2">Gemini 3.0</h3>
                    <p className="text-sm text-white/70">Advanced AI Analysis</p>
                </Card>
                <Card className="bg-white/10 backdrop-blur-md border-white/20 rotate-0 sm:rotate-[1deg] p-6 md:p-8 min-h-[140px] text-white cursor-pointer hover:bg-white/20 hover:-translate-y-1 transition-all duration-300 group">
                    <div className="w-10 h-10 rounded-full bg-indigo-500/40 border border-indigo-400/30 mb-3 group-hover:scale-110 transition-transform flex items-center justify-center">
                        <span className="text-indigo-300 text-sm font-bold">VEO</span>
                    </div>
                    <h3 className="font-bold text-xl mb-2">VEO 3.1</h3>
                    <p className="text-sm text-white/70">Video Generation Engine</p>
                </Card>
                <Card className="bg-white/10 backdrop-blur-md border-white/20 rotate-0 sm:rotate-[-1deg] p-6 md:p-8 min-h-[140px] text-white cursor-pointer hover:bg-white/20 hover:-translate-y-1 transition-all duration-300 group">
                    <div className="w-10 h-10 rounded-full bg-teal-500/40 border border-teal-400/30 mb-3 group-hover:scale-110 transition-transform flex items-center justify-center">
                        <span className="text-teal-300 text-sm font-bold">⚡</span>
                    </div>
                    <h3 className="font-bold text-xl mb-2 text-white">Real-time</h3>
                    <p className="text-sm text-white/70">Automated Pipeline</p>
                </Card>
            </div>
        </section>
    );
}
