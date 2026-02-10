
'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/useAuthStore';
import { fetchMe } from '@/lib/api';
import { Button } from '@/components/ui/Button';

export default function PaymentSuccessPage() {
    const router = useRouter();
    const setAuth = useAuthStore((s) => s.setAuth);
    const [status, setStatus] = useState<'syncing' | 'synced' | 'failed'>('syncing');
    const [attempt, setAttempt] = useState(0);
    const [tier, setTier] = useState<string>('FREE');

    useEffect(() => {
        let cancelled = false;

        const syncTier = async () => {
            // Stripe 리다이렉트가 webhook 처리보다 먼저 발생할 수 있어,
            // tier가 PRO/BUSINESS로 바뀔 때까지 짧게 폴링한다.
            const maxTries = 6;
            const delayMs = 2000;

            for (let i = 1; i <= maxTries; i++) {
                if (cancelled) return;
                setAttempt(i);

                try {
                    const me = await fetchMe();
                    const nextTier = me.tier ?? 'FREE';
                    setTier(nextTier);
                    setAuth({
                        email: me.email,
                        role: me.role,
                        name: me.name,
                        tier: nextTier,
                        subscriptionStatus: me.subscription_status ?? 'none',
                    });

                    if (nextTier === 'PRO' || nextTier === 'BUSINESS') {
                        setStatus('synced');
                        return;
                    }
                } catch {
                    // fetchMe 실패는 일시적일 수 있으므로 폴링을 계속한다.
                }

                await new Promise((r) => setTimeout(r, delayMs));
            }

            if (!cancelled) setStatus('failed');
        };

        void syncTier();

        return () => {
            cancelled = true;
        };
    }, [setAuth, router]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-background)] p-4 text-center">
            <div className="bg-white p-8 rounded-[var(--radius-xl)] shadow-[var(--shadow-soft-lg)] max-w-md w-full border border-[var(--color-border)]">
                <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6 text-3xl">
                    🎉
                </div>
                <h1 className="text-2xl font-bold text-[var(--color-foreground)] mb-2">
                    결제가 완료되었습니다!
                </h1>
                <p className="text-[var(--color-muted)] mb-8">
                    PRO 멤버십이 활성화되었습니다.<br />
                    이제 무제한 챗봇과 파이프라인 기능을 사용하실 수 있습니다.
                </p>
                <div className="mb-6 text-sm text-[var(--color-muted)]">
                    {status === 'syncing' && (
                        <div>
                            구독 정보 동기화 중... ({attempt}/6)<br />
                            현재 등급: <span className="font-bold text-[var(--color-foreground)]">{tier}</span>
                        </div>
                    )}
                    {status === 'synced' && (
                        <div className="text-green-700 font-semibold">
                            동기화 완료되었습니다.
                        </div>
                    )}
                    {status === 'failed' && (
                        <div className="text-red-700 font-semibold">
                            구독 정보 동기화가 지연되고 있습니다. 잠시 후 요금제 페이지에서 다시 확인해주세요.
                        </div>
                    )}
                </div>
                <Button 
                    variant="default"
                    size="lg" 
                    className="w-full"
                    onClick={() => router.push('/pricing')}
                >
                    요금제 확인하기
                </Button>
            </div>
        </div>
    );
}
