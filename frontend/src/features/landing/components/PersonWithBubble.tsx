'use client';

import React from 'react';

type PersonWithBubbleProps = {
    text: string;
    position: 'above' | 'below';
    align?: 'left' | 'right';
};

// 뇌/지능을 상징하는 역동적인 AI 아이콘 (애니메이션 효과 포함)
function AIIcon({ className }: { className?: string }) {
    return (
        <div className={`relative ${className ?? 'w-10 h-10'}`}>
            <div className="absolute inset-0 bg-[#0ca678]/20 rounded-full animate-ping opacity-75" />
            <svg
                viewBox="0 0 24 24"
                className="relative z-10 w-full h-full text-slate-900"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
            >
                <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z" />
                <path d="M12 6v6l4 2" className="animate-pulse" />
                <circle cx="12" cy="12" r="2" fill="currentColor" />
            </svg>
        </div>
    );
}

export default function PersonWithBubble({ text, position, align = 'left' }: PersonWithBubbleProps) {
    const isAbove = position === 'above';
    const isRight = align === 'right';

    return (
        <div
            className={`flex flex-col gap-3 ${isRight ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-4 duration-700`}
        >
            {isAbove ? (
                <>
                    <div className="relative rounded-2xl border-2 border-slate-100 bg-white px-5 py-4 shadow-xl w-full max-w-[240px] min-h-[100px] flex items-center group-hover:border-[#0ca678]/30 transition-colors">
                        <p className="text-[13px] font-bold text-slate-700 break-words leading-relaxed italic">
                            &quot;{text}&quot;
                        </p>
                        <div
                            className="absolute left-1/2 -translate-x-1/2 -bottom-2 w-4 h-4 bg-white border-b-2 border-r-2 border-slate-100 rotate-45"
                            aria-hidden
                        />
                    </div>
                    <AIIcon className="w-10 h-10 ml-4" />
                </>
            ) : (
                <>
                    <AIIcon className={`w-11 h-11 ${isRight ? 'mr-4' : 'ml-4'}`} />
                    <div className="relative rounded-2xl border-2 border-slate-100 bg-white px-5 py-4 shadow-xl w-full max-w-[240px] min-h-[100px] flex items-center group-hover:border-[#0ca678]/30 transition-colors">
                        <p className="text-[13px] font-bold text-slate-700 break-words leading-relaxed italic">
                            &quot;{text}&quot;
                        </p>
                        <div
                            className={`absolute left-1/2 -translate-x-1/2 -top-2 w-4 h-4 bg-white border-t-2 border-l-2 border-slate-100 rotate-45`}
                            aria-hidden
                        />
                    </div>
                </>
            )}
        </div>
    );
}
