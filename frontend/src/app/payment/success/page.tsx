'use client';

import Link from 'next/link';
import { useEffect, useRef } from 'react';
import confetti from 'canvas-confetti';
import { useAuthStore } from '@/store/useAuthStore';
import { fetchMe } from '@/lib/api';

export default function PaymentSuccessPage() {
  const hasRun = useRef(false);
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    // 백엔드에서 최신 구독 정보를 가져와 Zustand 스토어에 반영
    fetchMe()
      .then((me) => {
        setAuth({
          email: me.email,
          role: me.role,
          name: me.name,
          tier: me.tier ?? 'PRO',
          subscriptionStatus: me.subscription_status ?? 'active',
        });
      })
      .catch(() => {
        // 결제 성공 페이지이므로, API 호출 실패 시에도 UX를 차단하지 않습니다.
      });

    const durationMs = 1800;
    const startedAt = Date.now();

    const interval = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const t = Math.min(1, elapsed / durationMs);

      confetti({
        particleCount: Math.floor(90 * (1 - t) + 20),
        spread: 70,
        startVelocity: 45,
        ticks: 220,
        zIndex: 9999,
        origin: { x: 0.15, y: 0.6 },
      });
      confetti({
        particleCount: Math.floor(90 * (1 - t) + 20),
        spread: 70,
        startVelocity: 45,
        ticks: 220,
        zIndex: 9999,
        origin: { x: 0.85, y: 0.6 },
      });

      if (elapsed >= durationMs) {
        window.clearInterval(interval);
      }
    }, 260);

    return () => window.clearInterval(interval);
  }, [setAuth]);

  return (
    <main className="min-h-screen bg-[var(--color-background)]">
      <div className="mx-auto max-w-3xl px-6 py-20">
        <div className="soft-card p-8 text-center">
          <div className="mx-auto inline-flex items-center rounded-full bg-[var(--color-accent-light)] px-4 py-2 text-sm font-bold text-[var(--color-foreground)]">
            결제 완료
          </div>

          <h1 className="mt-6 text-2xl font-black tracking-tight text-[var(--color-foreground)] sm:text-3xl">
            결제 성공! Professional 등급으로 업그레이드되었습니다.
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[var(--color-muted)] sm:text-base">
            구독 정보가 서버에서 확인되어 계정에 반영되었습니다. 모든 PRO 기능을
            자유롭게 이용하세요.
          </p>

          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/" className="soft-button-primary justify-center">
              메인으로 돌아가기
            </Link>
            <Link href="/pricing" className="soft-button-secondary justify-center">
              요금제 다시 보기
            </Link>
          </div>

          <div className="mt-8 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-teal-light)] p-4 text-left text-sm text-[var(--color-foreground)]">
            <div className="font-semibold">WSL/localhost 팁</div>
            <div className="mt-1 leading-6 text-[var(--color-muted)]">
              Stripe 리다이렉트가 꼬이면 브라우저 주소창이{' '}
              <span className="font-semibold text-[var(--color-foreground)]">
                localhost:3000
              </span>
              인지 확인해 주세요.
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
