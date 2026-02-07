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
        <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
            <Card.Title className="mb-4 text-slate-900">프롬프트 로그</Card.Title>
            {isLoading ? (
                <p className="text-sm text-slate-600 font-medium">로딩 중...</p>
            ) : promptLogs.length === 0 ? (
                <p className="text-sm text-slate-600 font-medium">프롬프트 로그가 없습니다.</p>
            ) : (
                <>
                    {promptLogs === DUMMY_PROMPT_LOGS && (
                        <p className="text-xs text-slate-500 font-medium mb-2">(더미 데이터)</p>
                    )}
                    <div className="space-y-3">
                        {promptLogs.map((log, index) => (
                            <details
                                key={`${log.history_id}-${index}`}
                                className="border border-slate-200 rounded-2xl p-3 bg-slate-50/60 hover:bg-slate-50 transition-colors"
                            >
                                <summary className="cursor-pointer font-medium text-slate-900">
                                    {log.product_name || 'N/A'} · {log.executed_at || 'N/A'}
                                </summary>
                                <pre className="text-xs mt-3 bg-slate-100 text-slate-800 p-3 rounded-xl overflow-auto font-mono">
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

