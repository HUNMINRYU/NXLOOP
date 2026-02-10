'use client';

import { useState } from 'react';
import { Navbar } from '@/features/landing';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { searchDiscovery } from '@/lib/api';
import { DUMMY_DISCOVERY_RESULTS } from '@/lib/dummyData';

export default function DiscoverySearchClient() {
  type DiscoveryResult = {
    title?: string;
    snippet?: string;
    url?: string;
  };

  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(5);
  const [results, setResults] = useState<DiscoveryResult[]>(DUMMY_DISCOVERY_RESULTS);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setError('');
    if (!query.trim()) {
      setError('검색어를 입력하세요.');
      return;
    }
    setLoading(true);
    try {
      const data = await searchDiscovery(query.trim(), maxResults);
      setResults((data.results && data.results.length > 0) ? data.results : DUMMY_DISCOVERY_RESULTS);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '';
      setError(message || '검색 실패');
    } finally {
      setLoading(false);
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
        <Card className="max-w-5xl mx-auto space-y-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
          <div>
            <p className="font-display font-semibold text-indigo-600 uppercase tracking-[0.2em] text-sm mb-2">Discovery Engine</p>
            <h1 className="font-display text-4xl font-bold text-slate-900 mb-2">검색 UI</h1>
            <p className="font-body text-lg font-medium text-slate-600">
              Discovery Engine 인덱스에서 직접 검색하여 근거 자료를 확인합니다.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-[1fr_auto_auto] items-center">
            <Input
              className="w-full bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900"
              placeholder="검색어를 입력하세요"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <Input
              className="w-24 bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900"
              type="number"
              min={1}
              max={10}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
            />
            <Button
              type="button"
              variant="default"
              onClick={handleSearch}
              disabled={loading}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
            >
              {loading ? '검색 중...' : '검색'}
            </Button>
          </div>

          {error && <p className="text-sm text-rose-600 font-medium">{error}</p>}

          <div className="space-y-3">
            {results.length === 0 && !loading ? (
              <p className="text-sm text-slate-600 font-medium">검색 결과가 없습니다.</p>
            ) : (
              <>
                {!loading && results === DUMMY_DISCOVERY_RESULTS && (
                  <p className="text-xs text-slate-500 font-medium">(샘플 결과 · 검색 후 실제 결과로 대체됩니다)</p>
                )}
                {results.map((item, index) => (
                <div key={`${item.title}-${index}`} className="p-4 rounded-2xl bg-slate-50/60 border border-slate-200/50 hover:bg-slate-50 hover:border-slate-200 transition-all duration-300">
                  <h3 className="text-xl font-bold text-slate-900 mb-2">{item.title || 'Untitled'}</h3>
                  <p className="text-sm font-medium text-slate-600 mb-2">{item.snippet || '요약 없음'}</p>
                  {item.url && (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-indigo-600 hover:text-indigo-700 font-semibold underline transition-colors"
                    >
                      원문 보기
                    </a>
                  )}
                </div>
              ))}
              </>
            )}
          </div>
        </Card>
        </div>
      </main>
    </>
  );
}
