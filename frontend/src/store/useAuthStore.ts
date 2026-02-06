'use client';

import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

interface AuthState {
    token: string | null;
    email: string | null;
    role: string | null;
    setAuth: (auth: { token: string | null; email: string | null; role: string | null }) => void;
    clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
    devtools(
        persist(
            (set) => ({
                token: null,
                email: null,
                role: null,
                setAuth: (auth) => set(auth),
                clearAuth: () => {
                    // Zustand persist가 사용하는 실제 키 제거
                    sessionStorage.removeItem('auth-storage');
                    set({ token: null, email: null, role: null });
                },
            }),
            {
                name: 'auth-storage',
                storage: createJSONStorage(() => sessionStorage),
            },
        ),
    ),
);
