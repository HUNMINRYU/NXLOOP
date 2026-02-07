import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface ChatbotUsageState {
    remainingMessages: number;
    isAuthenticated: boolean;
    incrementUsage: () => void;
    resetUsage: () => void;
    forceExpire: () => void;
    setAuthenticated: (auth: boolean) => void;
    checkAuthStatus: () => void;
}

export const useChatbotUsage = create<ChatbotUsageState>()(
    persist(
        (set) => ({
            remainingMessages: 3,
            isAuthenticated: false,
            incrementUsage: () => {
                set((state) => ({
                    remainingMessages: Math.max(0, state.remainingMessages - 1),
                }));
            },
            resetUsage: () => set({ remainingMessages: 3 }),
            forceExpire: () => set({ remainingMessages: 0 }),
            setAuthenticated: (auth: boolean) => set({ isAuthenticated: auth }),
            checkAuthStatus: () => {
                if (typeof window !== 'undefined') {
                    const authStorage = sessionStorage.getItem('auth-storage');
                    const isAuth = !!authStorage;
                    set({ isAuthenticated: isAuth });
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

export const useChatbotStatus = () => {
    const state = useChatbotUsage();
    const hasReachedLimit = !state.isAuthenticated && state.remainingMessages <= 0;

    return {
        ...state,
        hasReachedLimit,
    };
};
