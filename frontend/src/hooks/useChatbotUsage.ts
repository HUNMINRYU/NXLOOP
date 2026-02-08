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
 * - 비로그인: 무료 3회 후 한도 (백엔드 IP 제한과 동일)
 * - 로그인: 요금제에 따라 이용 (백엔드는 로그인 시 무제한)
 */
export const useChatbotStatus = () => {
    const usage = useChatbotUsage();
    const email = useAuthStore((s) => s.email);
    const tier = useAuthStore((s) => s.tier) ?? 'FREE';

    const isAuthenticated = typeof email === 'string' && email.length > 0;
    const hasReachedLimit = !isAuthenticated && usage.remainingMessages <= 0;

    return {
        ...usage,
        isAuthenticated,
        hasReachedLimit,
        tier,
        remainingMessages: usage.remainingMessages,
    };
};
