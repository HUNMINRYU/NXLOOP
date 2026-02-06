import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merges tailwind classes using clsx and tailwind-merge.
 * This prevents class conflicts (e.g., matching padding-4 and padding-8).
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * 크론 표현식을 UI 값으로 역변환
 */
export function parseCron(cron: string): {
    frequency: 'daily' | 'weekly' | 'custom';
    days: number[];
    hour: number;
    minute: number;
} {
    const parts = cron.split(' ');
    if (parts.length < 5) {
        return { frequency: 'daily', days: [], hour: 16, minute: 0 };
    }

    const [min, hr, , , dow] = parts;
    const hour = parseInt(hr || '0', 10);
    const minute = parseInt(min || '0', 10);
    const dowValue = dow ?? '*';

    if (dowValue === '*') {
        return { frequency: 'daily', days: [], hour, minute };
    }

    // cron 요일(0=일,1=월,...) -> UI 요일(0=월,...,6=일)
    const days = dowValue.split(',').map((d) => {
        const cronDay = parseInt(d, 10);
        return (cronDay + 6) % 7;
    });

    const frequency = days.length === 1 ? 'weekly' : 'custom';
    return { frequency, days: days.sort((a, b) => a - b), hour, minute };
}

/**
 * 날짜를 상대 시간 문자열로 변환
 */
export function formatRelativeTime(dateStr: string | null | undefined): string {
    if (!dateStr) return '-';

    const target = new Date(dateStr);
    const now = new Date();
    const diffMs = target.getTime() - now.getTime();

    // 과거
    if (diffMs < 0) {
        return new Date(dateStr).toLocaleString('ko-KR');
    }

    const diffMin = Math.floor(diffMs / 60_000);
    const diffHr = Math.floor(diffMs / 3_600_000);
    const diffDay = Math.floor(diffMs / 86_400_000);

    if (diffMin < 1) return '곧 실행';
    if (diffMin < 60) return `${diffMin}분 후`;
    if (diffHr < 24) return `${diffHr}시간 후`;
    if (diffDay < 7) return `${diffDay}일 후`;

    return target.toLocaleString('ko-KR');
}
