'use client';

import { useState } from 'react';
import { Navbar } from '@/features/landing';
import { Button, Card, Input } from '@/components/ui';
import { fetchAuditLogs } from '@/lib/api';
import { DUMMY_AUDIT_LOGS } from '@/lib/dummyData';

export interface AuditLog {
  id: string | number;
  action?: string;
  actor_email?: string;
  actor_role?: string;
  created_at?: string | null;
  entity_type?: string;
  entity_id?: string | number | null;
  metadata?: string | Record<string, unknown> | null;
}

interface AdminAuditLogsClientProps {
  initialLogs: AuditLog[];
}

export default function AdminAuditLogsClient({ initialLogs }: AdminAuditLogsClientProps) {
  const [logs, setLogs] = useState<AuditLog[]>(
    initialLogs.length > 0 ? initialLogs : DUMMY_AUDIT_LOGS
  );
  const [limit, setLimit] = useState(50);
  const [error, setError] = useState('');
  const [isDummy, setIsDummy] = useState(initialLogs.length === 0);

  const loadLogs = async () => {
    setError('');
    try {
      const data = await fetchAuditLogs(limit);
      const list = data?.logs || [];
      const useDummy = list.length === 0;
      setLogs(useDummy ? DUMMY_AUDIT_LOGS : list);
      setIsDummy(useDummy);
    } catch {
      setLogs(DUMMY_AUDIT_LOGS);
      setIsDummy(true);
    }
  };

  return (
    <>
      <Navbar />
      <main className="relative min-h-screen overflow-hidden">
        {/* Light Elegant Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
        <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/[0.02] via-transparent to-purple-500/[0.02]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgb(15 23 42 / 0.08) 1px, transparent 1px),
              linear-gradient(to bottom, rgb(15 23 42 / 0.08) 1px, transparent 1px)
            `,
            backgroundSize: '80px 80px',
          }}
        />
        <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />
        <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-purple-400/[0.06] blur-[140px] rounded-full" />

        <div className="relative z-10 p-8 pt-24">
        <div className="max-w-6xl mx-auto space-y-6">
          <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
            <p className="font-display font-semibold text-indigo-600 uppercase tracking-[0.2em] text-sm mb-1">Admin</p>
            <h1 className="font-display text-2xl font-bold text-slate-900 mb-2">감사 로그</h1>
            <p className="font-body text-base text-slate-600 mb-4">변경 이력을 확인합니다.</p>

            <div className="flex gap-3 items-center mb-4">
              <Input className="w-24 bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900" type="number" min={1} max={200} value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
              <Button variant="default" onClick={loadLogs} className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">새로고침</Button>
            </div>

            {error && <p className="text-sm text-rose-600 font-medium mb-2">{error}</p>}
            {isDummy && logs.length > 0 && (
              <p className="text-xs text-slate-500 font-medium mb-2">(더미 데이터 · API 연동 후 실제 로그로 대체됩니다)</p>
            )}

            <div className="space-y-3">
              {logs.length === 0 ? (
                <p className="text-sm text-slate-600 font-medium">감사 로그가 없습니다.</p>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="border border-slate-200 rounded-2xl p-3 text-sm bg-slate-50/60 hover:bg-slate-50 transition-colors">
                    <div className="font-semibold text-slate-900">{log.action}</div>
                    <div className="text-slate-600 font-medium">
                      {log.actor_email} ({log.actor_role}) · {log.created_at || '-'}
                    </div>
                    <div className="text-slate-600 font-medium">{log.entity_type} {log.entity_id || ''}</div>
                    {log.metadata && (
                      <pre className="text-xs mt-2 bg-slate-100 text-slate-800 p-2 rounded-xl overflow-auto font-mono">
                        {typeof log.metadata === 'string'
                          ? log.metadata
                          : JSON.stringify(log.metadata, null, 2)}
                      </pre>
                    )}
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
        </div>
      </main>
    </>
  );
}

