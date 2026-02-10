'use client';

import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';
import { clearStoredChat } from '@/lib/chatStorage';

interface AuthState {
    email: string | null;
    role: string | null;
    name: string | null;
    tier: string;
    subscriptionStatus: string;
    setAuth: (auth: {
        email: string | null;
        role: string | null;
        name: string | null;
        tier?: string;
        subscriptionStatus?: string;
    }) => void;
    clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
    devtools(
        persist(
            (set) => ({
                email: null,
                role: null,
                name: null,
                tier: 'FREE',
                subscriptionStatus: 'none',
                setAuth: (auth) =>
                    set({
                        ...auth,
                        tier: auth.tier ?? 'FREE',
                        subscriptionStatus: auth.subscriptionStatus ?? 'none',
                    }),
                clearAuth: () => {
                    // Zustand persist가 사용하는 실제 키 제거
                    sessionStorage.removeItem('auth-storage');
                    // 로그아웃/인증 초기화 시 챗봇 대화 내역도 삭제 (Navbar·401 외 경로에서 clearAuth 호출 시에도 일관 동작)
                    clearStoredChat();
                    set({
                        email: null,
                        role: null,
                        name: null,
                        tier: 'FREE',
                        subscriptionStatus: 'none',
                    });
                },
            }),
            {
                name: 'auth-storage',
                storage: createJSONStorage(() => sessionStorage),
            },
        ),
    ),
);
