import Link from 'next/link';

type Plan = {
  id: 'FREE' | 'PRO' | 'BUSINESS';
  name: string;
  price: string;
  description: string;
  features: string[];
  ctaLabel: string;
  href?: string;
  highlighted?: boolean;
};

const proPaymentLink = process.env.NEXT_PUBLIC_STRIPE_PRO_PAYMENT_LINK;
const businessPaymentLink = process.env.NEXT_PUBLIC_STRIPE_BUSINESS_PAYMENT_LINK;

const plans: Plan[] = [
  {
    id: 'FREE',
    name: 'Free',
    price: '₩0',
    description: '가볍게 체험하고, 워크플로우를 이해해보세요.',
    features: [
      '기본 파이프라인 체험',
      '핵심 인사이트 샘플 확인',
      '커뮤니티 지원',
    ],
    ctaLabel: '시작하기',
    href: '/signup',
  },
  {
    id: 'PRO',
    name: 'Professional',
    price: '₩29,000 / 월',
    description: '개인/소규모 팀을 위한 실전 자동화.',
    features: [
      '고급 인사이트 분석',
      '썸네일/카피 생성 강화',
      '우선 지원',
      '워크플로우 템플릿',
    ],
    ctaLabel: 'Professional로 업그레이드',
    href: proPaymentLink,
    highlighted: true,
  },
  {
    id: 'BUSINESS',
    name: 'Business',
    price: '문의',
    description: '조직 단위 운영과 확장에 최적화.',
    features: [
      '팀/권한 관리',
      '맞춤형 워크플로우',
      '전담 지원',
      'SLA/보안 옵션',
    ],
    ctaLabel: 'Business 시작하기',
    href: businessPaymentLink,
  },
];

function PricingCard({ plan }: { plan: Plan }) {
  const isExternal = Boolean(plan.href && plan.href.startsWith('http'));
  const isDisabled = !plan.href;

  const cardClassName = plan.highlighted
    ? 'soft-card relative border-2 border-blue-500 shadow-[var(--shadow-soft-lg)]'
    : 'soft-card';

  const badge = plan.highlighted ? (
    <div className="absolute -top-3 left-6 rounded-full bg-blue-600 px-3 py-1 text-xs font-bold text-white shadow-[var(--shadow-soft-sm)]">
      Recommended
    </div>
  ) : null;

  const ctaClassName = plan.highlighted
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
          {isDisabled ? (
            <button
              type="button"
              className={`${ctaClassName} cursor-not-allowed opacity-60`}
              disabled
              aria-disabled="true"
              title="결제 링크가 설정되지 않았습니다."
            >
              {plan.ctaLabel}
            </button>
          ) : isExternal ? (
            <a
              className={ctaClassName}
              href={plan.href}
              target="_blank"
              rel="noreferrer"
            >
              {plan.ctaLabel}
            </a>
          ) : (
            <Link className={ctaClassName} href={plan.href!}>
              {plan.ctaLabel}
            </Link>
          )}
          {plan.id !== 'FREE' && (
            <p className="mt-2 text-xs text-[var(--color-muted)]">
              WSL 환경에서는 결제 리다이렉트가 꼬일 수 있어요. 브라우저 주소창은{' '}
              <span className="font-semibold text-[var(--color-foreground)]">
                localhost:3000
              </span>
              으로 접속해주세요.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-[var(--color-background)]">
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[var(--color-accent-light)] via-transparent to-transparent" />
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="text-center">
            <h1 className="text-3xl font-black tracking-tight text-[var(--color-foreground)] sm:text-4xl">
              요금제
            </h1>
            <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[var(--color-muted)] sm:text-base">
              목적에 맞는 플랜을 선택하고, Nexloop의 자동화 파이프라인을 바로 시작하세요.
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
            {plans.map((plan) => (
              <PricingCard key={plan.id} plan={plan} />
            ))}
          </div>

          <div className="mx-auto mt-10 max-w-3xl rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 text-sm text-[var(--color-muted)] shadow-[var(--shadow-soft-sm)]">
            <div className="font-semibold text-[var(--color-foreground)]">
              로컬호스트 연결 주의 (WSL)
            </div>
            <div className="mt-1 leading-6">
              백엔드를 WSL에서 띄우고 Windows 브라우저로 접속할 때{' '}
              <span className="font-semibold text-[var(--color-foreground)]">
                127.0.0.1
              </span>{' '}
              연결이 꼬일 수 있습니다. Stripe 리다이렉트 URL은{' '}
              <span className="font-semibold text-[var(--color-foreground)]">
                http://localhost:3000/payment/success
              </span>
              로 설정하고, 브라우저 주소창도 반드시{' '}
              <span className="font-semibold text-[var(--color-foreground)]">
                localhost:3000
              </span>
              으로 접속해주세요.
            </div>
          </div>

          <div className="mt-10 text-center">
            <Link
              href="/"
              className="soft-button-secondary inline-flex justify-center"
            >
              홈으로
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
