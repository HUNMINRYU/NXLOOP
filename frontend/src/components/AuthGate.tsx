import React, { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { fetchMe } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';

// 공개 경로: 로그인 없이 접근 가능한 페이지들
// 가격 확인 및 결제 성공 페이지는 마케팅/결제 플로우 상 공개가 자연스럽습니다.
const PUBLIC_PATHS = new Set(['/login', '/signup', '/', '/pricing', '/payment/success']);
const ADMIN_PATH_PREFIX = '/admin';

export default function AuthGate({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [ready, setReady] = useState(false);
    const { setAuth } = useAuthStore();

    useEffect(() => {
        // pathname이 없는 초기 시점 방어
        if (!pathname) return;

        const run = async () => {
            // 1) 공개 경로는 즉시 허용
            if (PUBLIC_PATHS.has(pathname)) {
                setReady(true);
                return;
            }

            // 2) 서버 세션 확인(/auth/me)
            try {
                const me = await fetchMe();
                setAuth({ email: me.email, role: me.role, name: me.name });

                // 3) 권한 체크(Admin)
                if (pathname.startsWith(ADMIN_PATH_PREFIX) && me.role !== 'admin') {
                    setReady(false);
                    router.replace('/');
                    return;
                }

                setReady(true);
            } catch {
                setReady(false);
                router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
            }
        };

        void run();
    }, [pathname, router, setAuth]);

    // 준비되지 않았고 공개 경로도 아니라면 렌더링 차단 (NULL 반환)
    // 단, SSR 불일치 방지를 위해 useEffect 이후 ready가 true일 때 렌더링
    // 혹은, 공개 경로는 즉시 렌더링 허용
    if (!ready && !PUBLIC_PATHS.has(pathname || '')) {
        return null;
    }

    return <>{children}</>;
}

// useAuth Hook - 이제 Zustand 스토어를 직접 사용하거나,
// 기존 컴포넌트 호환성을 위해 여기서 래핑해서 내보낼 수 있음.
export function useAuth() {
    return useAuthStore();
}
