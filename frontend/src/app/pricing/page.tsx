'use client';

import Link from 'next/link';
import { useState } from 'react';
import { createCheckoutSession } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';

type PlanId = 'FREE' | 'PRO' | 'BUSINESS';

type Plan = {
  id: PlanId;
  name: string;
  price: string;
  period?: string;
  description: string;
  features: string[];
  ctaLabel: string;
  highlighted?: boolean;
};

const plans: Plan[] = [
  {
    id: 'FREE',
    name: 'Free',
    price: '₩0',
    description: 'Explore the basics and understand the workflow.',
    features: [
      'Pipeline execution (1/day, preview only)',
      'AI chatbot (10 messages/day)',
      'Template-based hook generation',
      'Basic comment analysis',
    ],
    ctaLabel: 'Get Started',
  },
  {
    id: 'PRO',
    name: 'Professional',
    price: '₩29,000',
    period: '/ month',
    description: 'Full automation for individuals and small teams.',
    features: [
      'Everything in Free',
      'Full pipeline results (50 runs/day)',
      'AI video generation & extension',
      'Multi-style thumbnail comparison',
      'AI Studio (draft & refine)',
      'Deep comment analysis & CTR prediction',
      'Strategy analysis & Notion export',
      'Discovery search',
      'Unlimited chatbot access',
    ],
    ctaLabel: 'Upgrade to Pro',
    highlighted: true,
  },
  {
    id: 'BUSINESS',
    name: 'Business',
    price: 'Custom',
    description: 'Usage-based pricing optimized for teams at scale.',
    features: [
      'Everything in Pro',
      'Token-based usage pricing',
      'Team & permission management',
      'Audit logs & compliance',
      'Dedicated support & SLA',
      'Custom workflows',
    ],
    ctaLabel: 'Contact Sales',
  },
];

function PricingCard({
  plan,
  currentTier,
  loading,
  onCheckout,
}: {
  plan: Plan;
  currentTier: string;
  loading: PlanId | null;
  onCheckout: (planId: PlanId) => void;
}) {
  const isLoading = loading === plan.id;
  const isAnyLoading = loading !== null;
  const isCurrent = plan.id === currentTier;

  const cardClassName = isCurrent
    ? 'soft-card relative border-2 border-green-500 shadow-[var(--shadow-soft-lg)]'
    : plan.highlighted
      ? 'soft-card relative border-2 border-blue-500 shadow-[var(--shadow-soft-lg)]'
      : 'soft-card';

  const badge = isCurrent ? (
    <div className="absolute -top-3 left-6 rounded-full bg-green-600 px-3 py-1 text-xs font-bold text-white shadow-[var(--shadow-soft-sm)]">
      Current Plan
    </div>
  ) : plan.highlighted ? (
    <div className="absolute -top-3 left-6 rounded-full bg-blue-600 px-3 py-1 text-xs font-bold text-white shadow-[var(--shadow-soft-sm)]">
      Recommended
    </div>
  ) : null;

  const ctaClassName = isCurrent
    ? 'soft-button-secondary w-full justify-center cursor-default opacity-70'
    : plan.highlighted
      ? 'soft-button-primary w-full justify-center bg-blue-600 hover:opacity-95 focus-visible:ring-blue-600'
      : 'soft-button-secondary w-full justify-center';

  return (
    <div className={cardClassName}>
      {badge}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold tracking-tight text-[var(--color-foreground)]">
              {plan.name}
            </h2>
            <p className="mt-1 text-sm text-[var(--color-muted)]">{plan.description}</p>
          </div>
          <div className="text-right">
            <div className="text-xl font-black text-[var(--color-foreground)]">
              {plan.price}
            </div>
            {plan.period && (
              <div className="text-xs text-[var(--color-muted)]">{plan.period}</div>
            )}
          </div>
        </div>

        <ul className="mt-6 space-y-2 text-sm text-[var(--color-foreground)]">
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2">
              <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-[var(--color-primary)]" />
              <span className="leading-6">{feature}</span>
            </li>
          ))}
        </ul>

        <div className="mt-8">
          {isCurrent ? (
            <div className={ctaClassName}>Current Plan</div>
          ) : plan.id === 'FREE' ? (
            <Link className={ctaClassName} href="/signup">
              {plan.ctaLabel}
            </Link>
          ) : (
            <button
              type="button"
              className={`${ctaClassName} ${isAnyLoading && !isLoading ? 'cursor-not-allowed opacity-60' : ''}`}
              disabled={isAnyLoading}
              onClick={() => onCheckout(plan.id)}
            >
              {isLoading ? 'Redirecting...' : plan.ctaLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PricingPage() {
  const tier = useAuthStore((s) => s.tier);
  const [loading, setLoading] = useState<PlanId | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCheckout = async (planId: PlanId) => {
    setLoading(planId);
    setError(null);

    try {
      const { url } = await createCheckoutSession(planId as 'PRO' | 'BUSINESS');
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create checkout session.');
      setLoading(null);
    }
  };

  return (
    <main className="min-h-screen bg-[var(--color-background)]">
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[var(--color-accent-light)] via-transparent to-transparent" />
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="text-center">
            <h1 className="text-3xl font-black tracking-tight text-[var(--color-foreground)] sm:text-4xl">
              Pricing
            </h1>
            <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[var(--color-muted)] sm:text-base">
              Choose the plan that fits your needs and start automating with Nexloop.
            </p>
          </div>

          {error && (
            <div className="mx-auto mt-6 max-w-md rounded-lg border border-red-300 bg-red-50 p-4 text-center text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
            {plans.map((plan) => (
              <PricingCard
                key={plan.id}
                plan={plan}
                currentTier={tier}
                loading={loading}
                onCheckout={handleCheckout}
              />
            ))}
          </div>

          <div className="mt-10 text-center">
            <Link
              href="/"
              className="soft-button-secondary inline-flex justify-center"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
