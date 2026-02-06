'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui';
import { fetchPromptLogs } from '@/lib/api';
import { DUMMY_PROMPT_LOGS } from '@/lib/dummyData';

export default function PromptsSlot() {
    const [promptLogs, setPromptLogs] = useState<Array<{
        history_id?: string;
        product_name?: string;
        executed_at?: string;
        prompt_log?: Record<string, unknown>;
    }>>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const loadLogs = async () => {
            try {
                const data = await fetchPromptLogs(20);
                const logs = data?.logs || [];
                setPromptLogs(logs.length > 0 ? logs : DUMMY_PROMPT_LOGS);
            } catch {
                setPromptLogs(DUMMY_PROMPT_LOGS);
            } finally {
                setIsLoading(false);
            }
        };
        loadLogs();
    }, []);

    return (
        <Card className="p-6">
            <Card.Title className="mb-4">프롬프트 로그</Card.Title>
            {isLoading ? (
                <p className="text-sm text-[var(--color-muted)]">로딩 중...</p>
            ) : promptLogs.length === 0 ? (
                <p className="text-sm text-[var(--color-muted)]">프롬프트 로그가 없습니다.</p>
            ) : (
                <>
                    {promptLogs === DUMMY_PROMPT_LOGS && (
                        <p className="text-xs text-[var(--color-muted)] mb-2">(더미 데이터)</p>
                    )}
                    <div className="space-y-3">
                        {promptLogs.map((log, index) => (
                            <details
                                key={`${log.history_id}-${index}`}
                                className="border border-[var(--color-border)] rounded-[var(--radius-md)] p-3"
                            >
                                <summary className="cursor-pointer font-medium text-[var(--color-foreground)]">
                                    {log.product_name || 'N/A'} · {log.executed_at || 'N/A'}
                                </summary>
                                <pre className="text-xs mt-3 bg-[var(--color-secondary)] p-3 rounded-[var(--radius-sm)] overflow-auto">
                                    {JSON.stringify(log.prompt_log, null, 2)}
                                </pre>
                            </details>
                        ))}
                    </div>
                </>
            )}
        </Card>
    );
}

