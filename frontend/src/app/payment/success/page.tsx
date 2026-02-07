'use client';

import Link from 'next/link';
import { useEffect, useRef } from 'react';
import confetti from 'canvas-confetti';

export default function PaymentSuccessPage() {
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    try {
      localStorage.setItem('user_tier', 'PRO');
    } catch {
      // 데모 UX용이므로 저장 실패 시에도 진행합니다.
    }

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
  }, []);

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
            데모 환경에서는 로컬 저장소에 등급을 기록해두었습니다. 다음 화면에서도 업그레이드
            상태를 유지할 수 있어요.
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

