'use client';

import React, { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import ChatbotPanel from './ChatbotPanel';
import { useChatbotStatus } from '@/hooks/useChatbotUsage';

// 유백색 말풍선 아이콘 (세련된 스타일)
function ChatbotIcon() {
    return (
        <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-white w-7 h-7 md:w-9 md:h-9"
        >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
    );
}

export default function ChatbotWidget() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);
    const [showLeadCapture, setShowLeadCapture] = useState(false);
    const { isAuthenticated, remainingMessages, tier } = useChatbotStatus();

    // 분석결과·다른 페이지 등 URL 이동 시 챗봇 창 무조건 닫기
    useEffect(() => {
        setOpen(false);
    }, [pathname]);

    const handleLimitReached = () => {
        setShowLeadCapture(true);
    };

    return (
        <>
            {/* 전역 챗봇 위젯: 글자 영역 전체가 Hover Trigger가 됨 */}
            <div className="fixed bottom-10 right-10 z-[150] group pointer-events-auto cursor-pointer">
                {/* 1. AI Assistant 텍스트 힌트 (기본 노출 상태) */}
                {!open && (
                    <div className="relative flex flex-col items-end gap-1.5 transition-opacity duration-300 group-hover:opacity-0 pointer-events-auto">
                        <span className="text-[11px] font-black text-slate-500 uppercase tracking-[0.25em] drop-shadow-sm">
                            AI Assistant
                        </span>
                        <div className="w-12 h-[2px] bg-slate-400 rounded-full" />
                    </div>
                )}

                {/* 2. 챗봇 버튼 (텍스트 호버 시 나타남) */}
                <button
                    type="button"
                    onClick={() => setOpen(true)}
                    className={`absolute bottom-0 right-0 w-14 h-14 md:w-16 md:h-16 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl shadow-2xl transition-all duration-500 ease-out flex items-center justify-center border-2 border-white/20 z-20 transform 
            ${open ? 'opacity-0 scale-75 pointer-events-none' : 'opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 hover:scale-110 active:scale-95'}
          `}
                    aria-label="AI 챗봇 열기"
                >
                    <ChatbotIcon />

                    {/* iOS 레드 배지 (#ef4444) */}
                    {((!isAuthenticated || tier === 'FREE') && remainingMessages > 0 && remainingMessages <= 10) && (
                        <span className="absolute -top-2 -right-2 min-w-[22px] h-[22px] bg-[#ef4444] text-white text-[11px] font-black flex items-center justify-center rounded-full shadow-lg border-2 border-slate-900 z-30">
                            {remainingMessages}
                        </span>
                    )}

                    {/* 내부 광택 효과 */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
                </button>
            </div>

            {/* 챗봇 대화 패널 */}
            <ChatbotPanel isOpen={open} onClose={() => setOpen(false)} onLimitReached={handleLimitReached} />

            {/* 무료 체험 한도 초과 시 모달 + 배경 흐림 (Dimmed) */}
            {showLeadCapture && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-md"
                        onClick={() => setShowLeadCapture(false)}
                        aria-hidden
                    />
                    <div
                        className="relative z-10 bg-white rounded-[var(--radius-xl)] p-8 max-w-md w-full shadow-[var(--shadow-soft-lg)] border border-[var(--color-border)] text-center animate-in fade-in zoom-in duration-300"
                        role="dialog"
                        aria-modal
                        aria-labelledby="lead-capture-title"
                        aria-describedby="lead-capture-desc"
                    >
                        <div className="w-14 h-14 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center text-2xl mx-auto mb-5" aria-hidden>
                            🔐
                        </div>
                        <h3 id="lead-capture-title" className="text-xl font-bold mb-2 text-[var(--color-foreground)] leading-tight">
                            로그인이 필요한 서비스입니다
                        </h3>
                        <p id="lead-capture-desc" className="text-sm text-[var(--color-muted)] mb-6 leading-relaxed">
                            챗봇을 계속 이용하시려면 로그인해 주세요. 계정이 없으시면 가입 후 이용해 주세요.
                        </p>
                        <div className="flex flex-col gap-2.5">
                            <button
                                onClick={() => {
                                    setShowLeadCapture(false);
                                    setOpen(false);
                                    window.location.href = '/login';
                                }}
                                className="w-full bg-[var(--color-primary)] text-[var(--color-primary-foreground)] font-semibold py-3 rounded-[var(--radius-md)] hover:opacity-90 transition-opacity shadow-[var(--shadow-soft-sm)]"
                            >
                                로그인하고 계속하기
                            </button>
                            <button
                                onClick={() => {
                                    setShowLeadCapture(false);
                                    setOpen(false);
                                    window.location.href = '/signup';
                                }}
                                className="w-full bg-white text-[var(--color-foreground)] font-medium py-3 rounded-[var(--radius-md)] border border-[var(--color-border)] hover:bg-[var(--color-secondary)] transition-colors"
                            >
                                회원가입하기
                            </button>
                            <button
                                onClick={() => {
                                    setShowLeadCapture(false);
                                    setOpen(false);
                                }}
                                className="w-full text-[var(--color-muted)] font-medium py-2 hover:text-[var(--color-foreground)] transition-colors text-sm"
                            >
                                나중에 할게요
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
