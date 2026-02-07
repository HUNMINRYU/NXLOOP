'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { sendChatMessage } from '@/lib/api';
import { useChatbotStatus } from '@/hooks/useChatbotUsage';
import { Message, ChatCard, toChatCard, toSources, Source } from '@/types/chat';

const WELCOME: Message = {
    id: 'welcome',
    role: 'ai',
    content: '반가워요! NEXLOOP AI입니다. 궁금한 트렌드나 분석하고 싶은 데이터가 있으신가요?',
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null;
}

function getErrorMessage(err: unknown): string {
    if (err instanceof Error) return err.message;
    if (typeof err === 'string') return err;
    if (isRecord(err) && typeof err.message === 'string') return err.message;
    return '';
}

function ChatBubble({ msg, onCta }: { msg: Message; onCta?: (card: ChatCard) => void }) {
    const isAi = msg.role === 'ai';

    const renderSources = (sources: Source[]) => (
        <details className="mt-3 group">
            <summary className="cursor-pointer text-xs font-semibold text-[var(--color-muted)] hover:text-[var(--color-foreground)] transition-colors list-none flex items-center gap-1">
                <span className="transition-transform group-open:rotate-90">▶</span> 📚 참조 문서 ({sources.length})
            </summary>
            <div className="mt-2 space-y-2 pl-2 border-l-2 border-[var(--color-border)]">
                {sources.map((source, idx) => (
                    <div key={idx} className="text-xs">
                        <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-500 hover:underline font-medium block truncate"
                            title={source.title}
                        >
                            {source.title || source.url}
                        </a>
                        {source.snippet && (
                            <p className="text-[var(--color-muted)] mt-0.5 line-clamp-2 leading-relaxed">
                                {source.snippet}
                            </p>
                        )}
                    </div>
                ))}
            </div>
        </details>
    );

    if (msg.card) {
        const card = msg.card;
        const canAct = Boolean(onCta && (msg.card.action || msg.card.url));
        return (
            <Card className="w-full max-w-[90%] rounded-[var(--radius-lg)] p-4 text-left">
                <div className="font-bold text-[var(--color-foreground)] flex items-center gap-2 mb-2">
                    <span>💡</span> {card.title}
                </div>
                <p className="text-sm font-semibold text-[var(--color-muted)] mb-2 whitespace-pre-wrap">
                    {msg.content}
                </p>
                <ul className="list-disc list-inside text-sm font-medium text-[var(--color-muted)] space-y-1 mb-3">
                    {card.bullets.map((b, i) => (
                        <li key={i}>{b}</li>
                    ))}
                </ul>
                {card.cta && (
                    <Button
                        type="button"
                        variant="default"
                        onClick={() => (onCta ? onCta(card) : undefined)}
                        disabled={!canAct}
                        className="text-sm px-4 py-2"
                    >
                        ◆ {card.cta}
                    </Button>
                )}
                {msg.sources && msg.sources.length > 0 && renderSources(msg.sources)}
            </Card>
        );
    }
    return (
        <div className={`flex ${isAi ? 'justify-start' : 'justify-end'} w-full`}>
            <div
                className={`max-w-[85%] rounded-[var(--radius-lg)] border border-[var(--color-border)] px-4 py-3 ${
                    isAi ? 'bg-[var(--color-primary)]/10 text-left' : 'bg-[var(--color-primary)]/10 text-right'
                }`}
            >
                <p className="text-sm font-medium text-[var(--color-foreground)] break-words whitespace-pre-wrap">
                    {msg.content}
                </p>
                {isAi && msg.sources && msg.sources.length > 0 && renderSources(msg.sources)}
            </div>
        </div>
    );
}

const LoadingSkeleton = ({ status }: { status: string }) => (
    <div className="flex justify-start w-full animate-pulse">
        <div className="max-w-[85%] rounded-[var(--radius-lg)] border border-[var(--color-border)] px-4 py-3 bg-[var(--color-surface)] text-left space-y-2">
            <div className="flex items-center gap-2 mb-2">
                <span className="text-lg animate-bounce">🤖</span>
                <span className="text-xs font-semibold text-[var(--color-primary)]">{status}</span>
            </div>
            <div className="h-3 bg-[var(--color-border)] rounded w-3/4"></div>
            <div className="h-3 bg-[var(--color-border)] rounded w-1/2"></div>
            <div className="h-3 bg-[var(--color-border)] rounded w-5/6"></div>
        </div>
    </div>
);

type ChatbotPanelProps = {
    onClose: () => void;
    isOpen: boolean;
    onLimitReached?: () => void;
};

export default function ChatbotPanel({ onClose, isOpen, onLimitReached }: ChatbotPanelProps) {
    const router = useRouter();
    const [messages, setMessages] = useState<Message[]>([WELCOME]);
    const [input, setInput] = useState('');
    const [sessionId, setSessionId] = useState<string>('');
    const [isSending, setIsSending] = useState(false);
    const [loadingStatus, setLoadingStatus] = useState('요청을 분석하고 있습니다...');
    const listRef = useRef<HTMLDivElement>(null);
    const { hasReachedLimit, incrementUsage, isAuthenticated, remainingMessages, checkAuthStatus, forceExpire } =
        useChatbotStatus();

    useEffect(() => {
        checkAuthStatus();
        if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
    }, [messages, checkAuthStatus, isSending, loadingStatus]); // Scroll on status change too

    // Sequential Loading Status Effect
    useEffect(() => {
        if (!isSending) return;

        const steps = ['🔍 관련 문서를 검색하고 있습니다...', '🧠 답변을 생성하고 있습니다...', '✍️ 거의 다 됐어요!'];

        let stepIndex = 0;
        setLoadingStatus(steps[0] ?? '요청을 분석하고 있습니다...');

        const interval = setInterval(() => {
            stepIndex = (stepIndex + 1) % steps.length;
            setLoadingStatus(steps[stepIndex] ?? '답변을 생성하고 있습니다...');
        }, 2000); // Change message every 2 seconds

        return () => clearInterval(interval);
    }, [isSending]);
    // ... (중략) ...

    const handleCta = (card: ChatCard) => {
        if (card.action) {
            if (card.action.startsWith('/')) {
                router.push(card.action);
                return;
            }
            window.location.href = card.action;
            return;
        }
        if (card.url) {
            window.open(card.url, '_blank', 'noopener,noreferrer');
        }
    };

    const send = async () => {
        const text = input.trim();
        if (!text || isSending) return;

        // Check if non-authenticated user has reached limit
        if (hasReachedLimit) {
            if (onLimitReached) {
                onLimitReached();
            }
            return;
        }

        setInput('');
        const userMsg: Message = { id: `u-${Date.now()}`, role: 'user', content: text };
        setMessages((prev) => [...prev, userMsg]);
        setIsSending(true);

        try {
            const data = await sendChatMessage({ message: text, session_id: sessionId || '' });
            if (data?.session_id && typeof data.session_id === 'string') {
                setSessionId(data.session_id);
            }

            const aiReply: Message = {
                id: `a-${Date.now()}`,
                role: 'ai',
                content: data?.message || '응답을 생성하지 못했습니다.',
                card: toChatCard(data?.card),
                sources: toSources(data?.sources),
            };
            setMessages((prev) => [...prev, aiReply]);

            // Increment usage count for non-authenticated users after successful response
            if (!isAuthenticated) {
                incrementUsage();
            }
        } catch (err: unknown) {
            console.error('Chat error:', err);

            // Handle Rate Limit (429) specifically
            const message = getErrorMessage(err);
            const isRateLimit =
                message.toLowerCase().includes('too many requests') ||
                message.toLowerCase().includes('rate limit') ||
                message.includes('429');

            if (isRateLimit) {
                forceExpire();
                if (onLimitReached) onLimitReached();

                const aiReply: Message = {
                    id: `a-${Date.now()}`,
                    role: 'ai',
                    content: '무료 사용량이 초과되었습니다. 로그인 후 계속 이용해주세요.',
                };
                setMessages((prev) => [...prev, aiReply]);
            } else {
                const aiReply: Message = {
                    id: `a-${Date.now()}`,
                    role: 'ai',
                    content: '현재 응답을 가져올 수 없습니다. 잠시 후 다시 시도해 주세요.',
                };
                setMessages((prev) => [...prev, aiReply]);
            }
        } finally {
            setIsSending(false);
        }
    };

    if (!isOpen) return null;

    return (
        <>
            <div className="fixed inset-0 bg-black/40 z-[70] md:block" onClick={onClose} aria-hidden />
            <div
                className="fixed z-[71] bg-[var(--color-surface)] border border-[var(--color-border)] shadow-[var(--shadow-soft-lg)] flex flex-col
          right-0 top-20 bottom-4 md:top-24 md:bottom-6 w-full max-w-full md:max-w-[380px] md:right-4 rounded-[var(--radius-xl)]
          transition-transform duration-300 ease-out translate-x-0"
                role="dialog"
                aria-modal
                aria-label="AI 챗봇"
            >
                <header className="flex items-center justify-between border-b border-[var(--color-border)] p-4 bg-[var(--color-foreground)] text-[var(--color-primary-foreground)] shrink-0">
                    <div className="flex flex-col">
                        <h2 className="text-lg font-bold flex items-center gap-2">
                            AI 챗봇
                            {!isAuthenticated && remainingMessages > 0 && (
                                <span className="bg-red-500 text-white text-[10px] font-extrabold px-1.5 py-0.5 rounded-full min-w-[1.2em] text-center leading-none">
                                    {remainingMessages}
                                </span>
                            )}
                        </h2>
                        {!isAuthenticated && (
                            <p className="text-xs opacity-80 mt-1">
                                {remainingMessages > 0 ? `무료 질문 ${remainingMessages}회 남음` : '무료 체험 종료'}
                            </p>
                        )}
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="w-10 h-10 rounded-[var(--radius-sm)] border border-[var(--color-border)] font-bold hover:bg-[var(--color-surface)] hover:text-[var(--color-foreground)] transition-colors flex items-center justify-center"
                        aria-label="닫기"
                    >
                        ×
                    </button>
                </header>

                <div ref={listRef} className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 bg-white">
                    {messages.map((msg) => (
                        <ChatBubble key={msg.id} msg={msg} onCta={handleCta} />
                    ))}
                    {isSending && messages.length > 0 && messages.at(-1)?.role === 'user' && (
                        <LoadingSkeleton status={loadingStatus} />
                    )}
                </div>

                <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-surface)] shrink-0 relative">
                    {hasReachedLimit && (
                        <div className="absolute inset-0 bg-[var(--color-surface)]/90 backdrop-blur-sm z-10 flex flex-col items-center justify-center text-center p-4 rounded-b-[var(--radius-xl)]">
                            <p className="text-sm font-bold mb-2 text-[var(--color-foreground)]">
                                무료 체험분이 소진되었습니다.
                                <br />
                                로그인하여 계속하세요.
                            </p>
                            <div className="flex flex-col gap-2 w-full max-w-[200px]">
                                <Button onClick={() => router.push('/login')} className="w-full">
                                    로그인하러 가기
                                </Button>
                                <Button
                                    onClick={() => router.push('/signup')}
                                    variant="outline"
                                    className="w-full bg-transparent border-[var(--color-border)] text-[var(--color-foreground)] hover:bg-[var(--color-surface)]"
                                >
                                    회원가입하러 가기
                                </Button>
                            </div>
                        </div>
                    )}
                    <div className="flex gap-2 items-center">
                        <button
                            type="button"
                            className="w-10 h-10 rounded-[var(--radius-md)] border border-[var(--color-border)] flex items-center justify-center shrink-0 hover:bg-[var(--color-secondary)] transition-colors"
                            aria-label="첨부"
                            disabled={hasReachedLimit}
                        >
                            <svg
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="17 8 12 3 7 8" />
                                <line x1="12" y1="3" x2="12" y2="15" />
                            </svg>
                        </button>
                        <Input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && !hasReachedLimit && send()}
                            placeholder={hasReachedLimit ? '로그인이 필요합니다.' : '메시지를 입력하세요...'}
                            className="flex-1 min-w-0"
                            disabled={hasReachedLimit}
                        />
                        <Button
                            type="button"
                            variant="default"
                            onClick={send}
                            disabled={isSending || hasReachedLimit}
                            className="w-10 h-10 shrink-0 p-0"
                            aria-label="전송"
                        >
                            <svg
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                            >
                                <line x1="22" y1="2" x2="11" y2="13" />
                                <polygon points="22 2 15 22 11 13 2 9 22 2" />
                            </svg>
                        </Button>
                    </div>
                </div>
            </div>
        </>
    );
}
