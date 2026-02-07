'use client';

import React, { useState } from 'react';
import ChatbotPanel from './ChatbotPanel';
import { useChatbotUsage } from '@/hooks/useChatbotUsage';

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
    const [open, setOpen] = useState(false);
    const [showLeadCapture, setShowLeadCapture] = useState(false);
    const { isAuthenticated, remainingMessages } = useChatbotUsage();

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
                    {!isAuthenticated && remainingMessages > 0 && (
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

            {/* 무료 체험 한도 초과 시 팝업 */}
            {showLeadCapture && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => setShowLeadCapture(false)}
                    />
                    <div className="relative z-10 bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-slate-100 text-center animate-in fade-in zoom-in duration-300">
                        <div className="w-16 h-16 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center text-3xl mx-auto mb-6">
                            ⚠️
                        </div>
                        <h3 className="text-2xl font-black mb-4 text-slate-900 leading-tight">지식 탐색 한도 도달</h3>
                        <p className="text-slate-500 font-medium mb-8 leading-relaxed">
                            무료 사용자의 질문 한도를 모두 소모하셨습니다.
                            <br />
                            계속해서 인텔리전스를 활용하시려면 회원가입이 필요합니다.
                        </p>
                        <div className="flex flex-col gap-3">
                            <button
                                onClick={() => {
                                    setShowLeadCapture(false);
                                    window.location.href = '/signup';
                                }}
                                className="w-full bg-slate-900 text-white font-bold py-4 rounded-2xl hover:bg-slate-800 transition-all shadow-lg active:scale-[0.98]"
                            >
                                30초 만에 무료 회원가입
                            </button>
                            <button
                                onClick={() => {
                                    setShowLeadCapture(false);
                                    window.location.href = '/pricing';
                                }}
                                className="w-full bg-white text-slate-800 font-bold py-4 rounded-2xl border border-slate-200 hover:bg-slate-50 transition-all shadow-sm active:scale-[0.98]"
                            >
                                요금제 보기
                            </button>
                            <button
                                onClick={() => setShowLeadCapture(false)}
                                className="w-full text-slate-400 font-bold py-2 hover:text-slate-600 transition-all text-sm"
                            >
                                나중에 하기
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
