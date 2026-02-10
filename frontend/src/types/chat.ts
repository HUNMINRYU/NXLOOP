export type MessageRole = 'ai' | 'user';

/** 단일 CTA 또는 다중 선택지(생성 → 자동화/썸네일/비디오)용 액션 한 개 */
export type ChatCardAction = {
    label: string;
    action?: string;
    url?: string;
};

export type ChatCard = {
    title: string;
    bullets: string[];
    cta?: string;
    action?: string;
    url?: string;
    /** 다중 버튼일 때 사용 (생성 선택지 등). 있으면 cta/action/url 대신 이 목록으로 렌더 */
    actions?: ChatCardAction[];
};

export type Source = {
    title: string;
    url: string;
    snippet: string;
};

export type Message = {
    id: string;
    role: MessageRole;
    content: string;
    card?: ChatCard;
    sources?: Source[];
    /** 3회차 AI 답변 직후 로그인/회원가입 인라인 CTA 노출 여부 */
    showInlineCta?: boolean;
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null;
}

function isCardAction(item: unknown): item is ChatCardAction {
    if (!item || typeof item !== 'object') return false;
    const o = item as Record<string, unknown>;
    return typeof o.label === 'string' && (typeof o.action === 'string' || typeof o.url === 'string');
}

export const toChatCard = (value: unknown): ChatCard | undefined => {
    if (!value || typeof value !== 'object') return undefined;
    const card = value as {
        title?: unknown;
        bullets?: unknown;
        cta?: unknown;
        action?: unknown;
        url?: unknown;
        actions?: unknown;
    };
    if (typeof card.title !== 'string' || !Array.isArray(card.bullets)) return undefined;
    const out: ChatCard = {
        title: card.title,
        bullets: card.bullets.filter((item) => typeof item === 'string') as string[],
        cta: typeof card.cta === 'string' ? card.cta : undefined,
        action: typeof card.action === 'string' ? card.action : undefined,
        url: typeof card.url === 'string' ? card.url : undefined,
    };
    if (Array.isArray(card.actions) && card.actions.length > 0) {
        const actions = card.actions.filter(isCardAction);
        if (actions.length > 0) out.actions = actions;
    }
    return out;
};

export const toSources = (value: unknown): Source[] | undefined => {
    if (!value || !Array.isArray(value)) return undefined;

    const sources: Source[] = [];
    for (const item of value) {
        if (!isRecord(item)) continue;
        const title = item.title;
        const url = item.url;
        const snippet = item.snippet;
        if (typeof title !== 'string' || typeof url !== 'string' || typeof snippet !== 'string') continue;
        sources.push({ title, url, snippet });
    }

    return sources.length > 0 ? sources : undefined;
};
