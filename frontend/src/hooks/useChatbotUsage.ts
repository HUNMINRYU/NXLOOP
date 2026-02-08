import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { useAuthStore } from '@/store/useAuthStore';

interface ChatbotUsageState {
    remainingMessages: number;
    incrementUsage: () => void;
    resetUsage: () => void;
    forceExpire: () => void;
    setRemainingMessages: (n: number) => void;
    checkAuthStatus: () => void;
}

export const useChatbotUsage = create<ChatbotUsageState>()(
    persist(
        (set) => ({
            remainingMessages: 3,
            incrementUsage: () => {
                set((state) => ({
                    remainingMessages: Math.max(0, state.remainingMessages - 1),
                }));
            },
            resetUsage: () => set({ remainingMessages: 3 }),
            forceExpire: () => set({ remainingMessages: 0 }),
            setRemainingMessages: (n: number) =>
                set({ remainingMessages: Math.max(0, n) }),
            checkAuthStatus: () => {},
        }),
        {
            name: 'nexloop-chatbot-usage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({ remainingMessages: state.remainingMessages }),
        },
    ),
);

/**
 * 챗봇 한도/상태. 로그인 여부·요금제는 useAuthStore 기준.
 * - 비로그인: 무료 3회/일 후 한도 (백엔드 IP 제한)
 * - 로그인 FREE: 10회/일 한도 (백엔드 DB 집계)
 * - 로그인 PRO/BUSINESS: 무제한
 */
export const useChatbotStatus = () => {
    const usage = useChatbotUsage();
    const email = useAuthStore((s) => s.email);
    const tier = useAuthStore((s) => s.tier) ?? 'FREE';

    const isAuthenticated = typeof email === 'string' && email.length > 0;
    const hasReachedLimit =
        usage.remainingMessages <= 0 && (!isAuthenticated || tier === 'FREE');

    return {
        ...usage,
        isAuthenticated,
        hasReachedLimit,
        tier,
        remainingMessages: usage.remainingMessages,
    };
};
