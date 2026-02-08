export type MessageRole = 'ai' | 'user';

export type ChatCard = {
    title: string;
    bullets: string[];
    cta?: string;
    action?: string;
    url?: string;
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

export const toChatCard = (value: unknown): ChatCard | undefined => {
    if (!value || typeof value !== 'object') return undefined;
    const card = value as { title?: unknown; bullets?: unknown; cta?: unknown; action?: unknown; url?: unknown };
    if (typeof card.title !== 'string' || !Array.isArray(card.bullets)) return undefined;
    return {
        title: card.title,
        bullets: card.bullets.filter((item) => typeof item === 'string') as string[],
        cta: typeof card.cta === 'string' ? card.cta : undefined,
        action: typeof card.action === 'string' ? card.action : undefined,
        url: typeof card.url === 'string' ? card.url : undefined,
    };
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
