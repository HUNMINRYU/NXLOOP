'use client';

import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

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
