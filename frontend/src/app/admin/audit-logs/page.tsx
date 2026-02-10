'use client';

import { useState, useEffect } from 'react';
import AdminAuditLogsClient, { type AuditLog } from '@/components/AdminAuditLogsClient';
// API 함수를 클라이언트 컴포넌트 내부나 훅에서 동적으로 처리하도록 페이지 레벨 임포트 제거
import { fetchAuditLogs } from '@/lib/api';

export default function AdminAuditLogsPage() {
    const [initialLogs, setInitialLogs] = useState<AuditLog[]>([]);

    useEffect(() => {
        const loadLogs = async () => {
            try {
                const data = await fetchAuditLogs(50);
                setInitialLogs(data?.logs || []);
            } catch {
                console.error('[Client] Failed to fetch audit logs.');
            }
        };
        loadLogs();
    }, []);

    return <AdminAuditLogsClient initialLogs={initialLogs} />;
}
