'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@/components/ui';
import { exportNotionAction } from '@/app/actions/admin';

export default function NotionSlot() {
  const [taskId, setTaskId] = useState('');
  const [historyId, setHistoryId] = useState('');
  const [parentPageId, setParentPageId] = useState('');
  const [notionUrl, setNotionUrl] = useState('');
  const [notionError, setNotionError] = useState('');
  const [isPending, setIsPending] = useState(false);

  const handleNotionExport = async () => {
    setNotionError('');
    setNotionUrl('');
    setIsPending(true);
    const result = await exportNotionAction({
      task_id: taskId || undefined,
      history_id: historyId || undefined,
      parent_page_id: parentPageId || undefined,
    });
    
    if (result.success) {
      setNotionUrl(result.url || '');
    } else {
      setNotionError(result.error || 'Notion 내보내기 실패');
    }
    setIsPending(false);
  };

  return (
    <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
      <Card.Title className="mb-4 text-slate-900">Notion 내보내기</Card.Title>
      <div className="grid gap-3 md:grid-cols-2 mb-4">
        <Input placeholder="task_id (선택)" value={taskId} onChange={(e) => setTaskId(e.target.value)} className="bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900" />
        <Input placeholder="history_id (선택)" value={historyId} onChange={(e) => setHistoryId(e.target.value)} className="bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900" />
        <Input className="md:col-span-2 bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900" placeholder="parent_page_id (선택)" value={parentPageId} onChange={(e) => setParentPageId(e.target.value)} />
      </div>
      <Button
        variant="default"
        onClick={handleNotionExport}
        disabled={isPending}
        className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
      >
        {isPending ? '내보내는 중...' : 'Notion 내보내기 실행'}
      </Button>
      {notionUrl && (
        <a href={notionUrl} target="_blank" rel="noreferrer" className="block font-medium text-indigo-600 hover:text-indigo-700 underline mt-2 transition-colors">Notion 링크 열기</a>
      )}
      {notionError && <p className="text-sm text-rose-600 font-medium mt-2">{notionError}</p>}
    </Card>
  );
}

