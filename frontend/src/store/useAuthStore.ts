'use client';

import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

interface AuthState {
    email: string | null;
    role: string | null;
    name: string | null;
    setAuth: (auth: { email: string | null; role: string | null; name: string | null }) => void;
    clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
    devtools(
        persist(
            (set) => ({
                email: null,
                role: null,
                name: null,
                setAuth: (auth) => set(auth),
                clearAuth: () => {
                    // Zustand persist가 사용하는 실제 키 제거
                    sessionStorage.removeItem('auth-storage');
                    set({ email: null, role: null, name: null });
                },
            }),
            {
                name: 'auth-storage',
                storage: createJSONStorage(() => sessionStorage),
            },
        ),
    ),
);
