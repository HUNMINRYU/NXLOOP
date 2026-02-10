'use client';

import React, { useState, useEffect } from 'react';
import PersonWithBubble from './PersonWithBubble';
import { Card } from '@/components/ui/Card';

/* 패널별 서로 다른 이미지 세트 (정방형) */
const PANEL_IMAGES = {
    visibility: [
        'https://picsum.photos/400/400?seed=vis1',
        'https://picsum.photos/400/400?seed=vis2',
        'https://picsum.photos/400/400?seed=vis3',
    ],
    ctr: [
        'https://picsum.photos/400/400?seed=ctr1',
        'https://picsum.photos/400/400?seed=ctr2',
        'https://picsum.photos/400/400?seed=ctr3',
    ],
    sentiment: [
        'https://picsum.photos/400/400?seed=sen1',
        'https://picsum.photos/400/400?seed=sen2',
        'https://picsum.photos/400/400?seed=sen3',
    ],
};

const features = [
    {
        title: 'Smart Visibility',
        color: 'bg-emerald-50/40',
        borderColor: 'border-emerald-200/50',
        titleColor: 'text-emerald-950',
        speech: 'Optimal reach unlocked. Your content is now positioned exactly where it needs to be to capture maximum attention.',
        align: 'left' as const,
        images: PANEL_IMAGES.visibility,
    },
    {
        title: 'CTR Booster',
        color: 'bg-indigo-50/40',
        borderColor: 'border-indigo-200/50',
        titleColor: 'text-indigo-950',
        speech: 'Engagement primed. These visuals are designed to stop the scroll and drive significantly higher click-through rates.',
        align: 'left' as const,
        images: PANEL_IMAGES.ctr,
    },
    {
        title: 'Audience Insight',
        color: 'bg-purple-50/40',
        borderColor: 'border-purple-200/50',
        titleColor: 'text-purple-950',
        speech: "Audience connection established. We're deploying a data-backed story that resonates deeply to fuel your growth.",
        align: 'right' as const,
        images: PANEL_IMAGES.sentiment,
    },
];

function PanelSlider({ images }: { images: string[] }) {
    const [index, setIndex] = useState(0);

    useEffect(() => {
        const id = setInterval(() => setIndex((i) => (i + 1) % images.length), 4000);
        return () => clearInterval(id);
    }, [images.length]);

    return (
        <Card className="rounded-3xl overflow-hidden bg-white border-4 border-white shadow-2xl aspect-square w-full relative group ring-1 ring-slate-100">
            {/* AI 스캔 라인 효과 */}
            <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden">
                <div className="w-full h-[2px] bg-gradient-to-r from-transparent via-primary/50 to-transparent absolute top-0 animate-[scan_3s_linear_infinite]" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.1)_100%)] opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
            </div>

            <div
                className="flex h-full transition-transform duration-1000 cubic-bezier(0.4, 0, 0.2, 1)"
                style={{ transform: `translateX(-${index * 100}%)` }}
            >
                {images.map((src, i) => (
                    <div key={i} className="min-w-full aspect-square relative flex-shrink-0">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                            src={src}
                            alt=""
                            className="absolute inset-0 w-full h-full object-cover group-hover:scale-110 transition-transform duration-[4000ms] brightness-95 group-hover:brightness-105"
                        />
                    </div>
                ))}
            </div>

            {/* 분석 중임을 나타내는 미세 필터 */}
            <div className="absolute inset-0 bg-primary/5 mix-blend-overlay opacity-0 group-hover:opacity-20 transition-opacity" />

            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 p-1.5 bg-black/20 backdrop-blur-md rounded-full border border-white/20">
                {images.map((_, i) => (
                    <button
                        key={i}
                        onClick={() => setIndex(i)}
                        className={`w-2 h-2 rounded-full transition-all duration-500 ${i === index ? 'bg-white w-6' : 'bg-white/40 hover:bg-white/60'}`}
                        aria-label={`Slide ${i + 1}`}
                    />
                ))}
            </div>

            <style jsx>{`
                @keyframes scan {
                    0% {
                        top: -10%;
                    }
                    100% {
                        top: 110%;
                    }
                }
            `}</style>
        </Card>
    );
}

function FlowArrow() {
    return (
        <div className="flex items-center justify-center text-slate-300 flex-shrink-0 animate-pulse" aria-hidden>
            <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                className="md:hidden"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            >
                <path d="M12 5v14M6 13l6 6 6-6" />
            </svg>
            <svg
                width="40"
                height="32"
                viewBox="0 0 28 24"
                fill="none"
                className="hidden md:block"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            >
                <path d="M4 12h20M16 6l6 6-6 6" />
            </svg>
        </div>
    );
}

export default function Features() {
    return (
        <section
            className="py-24 md:py-32 px-6 md:px-12 bg-white border-t border-[var(--color-border)] relative overflow-hidden"
            id="pipeline"
        >
            <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-[var(--color-background)] to-transparent opacity-50" />

            <div className="relative max-w-7xl mx-auto">
                <div className="text-center mb-16 md:mb-24">
                    <h2 className="text-4xl md:text-6xl font-black mb-6 tracking-tighter">
                        Core{' '}
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#0ca678] to-[#6366f1]">
                            Pipeline
                        </span>
                    </h2>
                    <div className="w-24 h-1.5 bg-gradient-to-r from-[#0ca678] to-[#6366f1] mx-auto rounded-full" />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto_1fr] gap-6 md:gap-4 items-center">
                    {features.map((feature, panelIndex) => (
                        <React.Fragment key={panelIndex}>
                            <Card
                                className={`${feature.color} ${feature.borderColor} rounded-[var(--radius-xl)] border p-4 md:p-6 flex flex-col gap-6 md:min-h-[600px] shadow-sm hover:shadow-xl transition-all duration-500 hover:-translate-y-2 group cursor-pointer`}
                            >
                                <h3
                                    className={`text-xl md:text-2xl font-black ${feature.titleColor} text-center tracking-tight`}
                                >
                                    {feature.title}
                                </h3>
                                <div className="flex-1 flex flex-col justify-center">
                                    <div className="w-full max-w-[280px] mx-auto">
                                        <PanelSlider images={feature.images} />
                                    </div>
                                </div>
                                <div className="flex justify-center min-h-[140px]">
                                    <PersonWithBubble text={feature.speech} position="below" align={feature.align} />
                                </div>
                            </Card>
                            {panelIndex < features.length - 1 && <FlowArrow />}
                        </React.Fragment>
                    ))}
                </div>
            </div>
        </section>
    );
}
