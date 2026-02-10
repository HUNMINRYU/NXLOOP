import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { useAuthStore } from '@/store/useAuthStore';
import { getChatRemaining } from '@/lib/api';
import { useEffect } from 'react';

interface ChatbotUsageState {
    remainingMessages: number;
    incrementUsage: () => void;
    resetUsage: () => void;
    forceExpire: () => void;
    setRemainingMessages: (n: number) => void;
    checkAuthStatus: () => void;
    syncWithServer: () => Promise<void>;
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
            checkAuthStatus: () => {}, // Deprecated or handled by auth store
            syncWithServer: async () => {
                try {
                    // Auth/tier 변화 직후에는 캐시된 값(게스트 3회 등)이 잠깐 보여 UX를 망칠 수 있어
                    // 의도적으로 forceRefresh로 서버 truth를 받아온다.
                    const data = await getChatRemaining({ forceRefresh: true });
                    if (typeof data.remaining === 'number') {
                        set({ remainingMessages: data.remaining });
                    } else if (data.remaining === null) {
                        set({ remainingMessages: 999 }); // Unlimited
                    }
                } catch (error) {
                    console.error('Failed to sync chatbot usage:', error);
                }
            },
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
    const syncWithServer = useChatbotUsage((s) => s.syncWithServer);
    const email = useAuthStore((s) => s.email);
    const tier = useAuthStore((s) => s.tier) ?? 'FREE';

    const isAuthenticated = typeof email === 'string' && email.length > 0;
    const hasReachedLimit =
        usage.remainingMessages <= 0 && (!isAuthenticated || tier === 'FREE');

    // Auto-sync on mount and auth change.
    // Polling(setInterval)은 중복 mount 시 호출 폭증 + 백엔드 로그 스팸을 유발하므로 사용하지 않는다.
    useEffect(() => {
        syncWithServer();

        const onFocus = () => syncWithServer();
        const onVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                syncWithServer();
            }
        };

        window.addEventListener('focus', onFocus);
        document.addEventListener('visibilitychange', onVisibilityChange);
        return () => {
            window.removeEventListener('focus', onFocus);
            document.removeEventListener('visibilitychange', onVisibilityChange);
        };
    }, [email, tier, syncWithServer]); // Re-sync when user changes

    return {
        ...usage,
        isAuthenticated,
        hasReachedLimit,
        tier,
        remainingMessages: usage.remainingMessages,
    };
};
