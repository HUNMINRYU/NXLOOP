/**
 * 챗봇 대화 내역 localStorage 유틸.
 * 로그인/회원가입·새로고침 후에도 채팅 유지.
 *
 * - 로그아웃 시: clearStoredChat() 호출로 비움 (Navbar, 401 리다이렉트 시).
 * - 서버 재시작: 클라이언트에서 감지 불가. 백엔드 세션만 메모리에서 사라지고,
 *   화면에 보이는 과거 메시지는 localStorage 복원분이라 그대로 남음.
 *   새 메시지를 보내면 그 시점부터 백엔드 컨텍스트는 비어 있는 상태로 동작.
 */

import type { Message } from '@/types/chat';

// Key will be dynamic based on user ID
const BASE_KEY = 'nexloop_chat';

function getKey(userId?: string) {
    if (!userId) return `${BASE_KEY}_guest`;
    return `${BASE_KEY}_${userId}`;
}

export function loadStoredChat(userId?: string): { messages: Message[]; sessionId: string } | null {
    if (typeof window === 'undefined') return null;
    try {
        const key = getKey(userId);
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        const data = JSON.parse(raw) as unknown;
        if (!data || typeof data !== 'object') return null;
        const obj = data as { messages?: unknown; sessionId?: unknown };
        const messages = Array.isArray(obj.messages) ? (obj.messages as Message[]) : null;
        const sessionId = typeof obj.sessionId === 'string' ? obj.sessionId : '';
        if (!messages || messages.length === 0) return null;
        return { messages, sessionId };
    } catch {
        return null;
    }
}

export function saveStoredChat(messages: Message[], sessionId: string, userId?: string): void {
    if (typeof window === 'undefined') return;
    try {
        const key = getKey(userId);
        localStorage.setItem(key, JSON.stringify({ messages, sessionId }));
        
        // userId가 있으면 guest 데이터는 삭제할 수도 있음 (병합 전략에 따라)
        // 여기서는 격리만 함
    } catch {
        // quota or disabled localStorage
    }
}

/** 로그아웃 시 호출하여 저장된 채팅 내역 삭제 (특정 유저 또는 전체) */
export function clearStoredChat(userId?: string): void {
    if (typeof window === 'undefined') return;
    try {
        if (userId) {
            localStorage.removeItem(getKey(userId));
        } else {
            // userId가 없으면 guest 키 삭제
            localStorage.removeItem(getKey());
            
            // 또는 모든 nexloop_chat 관련 키 삭제 (안전하게)
            Object.keys(localStorage).forEach(k => {
                if (k.startsWith(BASE_KEY)) localStorage.removeItem(k);
            });
        }
    } catch {
        // ignore
    }
}
