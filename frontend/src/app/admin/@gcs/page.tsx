'use client';

import { useState } from 'react';
import { Button, Card, Input } from '@/components/ui';
import { fetchGcsMetadata } from '@/lib/api';
import { asGcsPath } from '@/types/common';

export default function GcsSlot() {
  const [gcsPath, setGcsPath] = useState('');
  const [prefix, setPrefix] = useState('');
  const [limit, setLimit] = useState(30);
  const [metadataItems, setMetadataItems] = useState<Array<{
    name?: string;
    size?: number | string;
    updated?: string;
    content_type?: string;
    signed_url?: string;
  }>>([]);
  const [metadataError, setMetadataError] = useState('');

  const handleFetchMetadata = async () => {
    setMetadataError('');
    setMetadataItems([]);
    try {
      const data = await fetchGcsMetadata({
        gcs_path: gcsPath ? asGcsPath(gcsPath) : undefined,
        prefix: prefix || undefined,
        limit,
      });
      setMetadataItems(data.items || []);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '';
      setMetadataError(message || '메타데이터 조회 실패');
    }
  };

  return (
    <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
      <Card.Title className="mb-4 text-slate-900">GCS 메타데이터</Card.Title>
      <div className="grid gap-3 md:grid-cols-2 mb-4">
        <Input
          placeholder="gs://bucket/path 또는 object path"
          value={gcsPath}
          onChange={(e) => setGcsPath(e.target.value)}
          className="bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900"
        />
        <Input
          placeholder="prefix (선택)"
          value={prefix}
          onChange={(e) => setPrefix(e.target.value)}
          className="bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900"
        />
      </div>
      <div className="flex items-center gap-3 mb-4">
        <Input
          className="w-24 bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900"
          type="number"
          min={1}
          max={200}
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
        />
        <Button variant="secondary" onClick={handleFetchMetadata} className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">메타데이터 조회</Button>
        {metadataError && <span className="text-sm text-rose-600 font-medium">{metadataError}</span>}
      </div>
      {metadataItems.length > 0 ? (
        <div className="space-y-3">
          {metadataItems.map((item, index) => (
            <div key={`${item.name}-${index}`} className="border border-slate-200 rounded-2xl p-3 text-sm bg-slate-50/60 hover:bg-slate-50 transition-colors">
              <div className="font-semibold text-slate-900">{item.name}</div>
              <div className="text-slate-600 font-medium">
                Size: {item.size ?? '-'} · Updated: {item.updated ?? '-'} · Type: {item.content_type ?? '-'}
              </div>
              {item.signed_url && (
                <a href={item.signed_url} className="text-indigo-600 hover:text-indigo-700 font-semibold underline transition-colors" target="_blank" rel="noreferrer">
                  Signed URL 열기
                </a>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-600 font-medium">표시할 메타데이터가 없습니다.</p>
      )}
    </Card>
  );
}

