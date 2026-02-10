'use client';

import { useEffect, useMemo, useState } from 'react';
import {
    adminApproveCtrRankerCandidate,
    adminImportCtrRankerRun,
    adminListCtrRankerCandidates,
    adminListCtrRankerRuns,
    CTRRankerCandidate,
    CTRRankerRun,
    fetchProducts,
} from '@/lib/api';
import { Button, Card } from '@/components/ui';

function isoToday(): string {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

function pickTopByRank(candidates: CTRRankerCandidate[], kind: 'before' | 'after', k = 5) {
    const rankKey = kind === 'before' ? 'baseline_rank' : 'after_rank';
    return candidates
        .filter((c) => typeof c[rankKey] === 'number' && (c[rankKey] as number) <= k)
        .sort((a, b) => (a[rankKey] as number) - (b[rankKey] as number));
}

export default function CTRRankerClient() {
    const [products, setProducts] = useState<string[]>([]);
    const [productName, setProductName] = useState<string>('');
    const [reportDate, setReportDate] = useState<string>(isoToday());

    const [runs, setRuns] = useState<CTRRankerRun[]>([]);
    const [selectedRunId, setSelectedRunId] = useState<string>('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [approvedCandidateId, setApprovedCandidateId] = useState<number | null>(null);
    const [candidates, setCandidates] = useState<CTRRankerCandidate[]>([]);
    const [summary, setSummary] = useState<{
        top1_changed: boolean;
        entered_count: number;
        dropped_count: number;
        top1_before_title?: string | null;
        top1_after_title?: string | null;
    } | null>(null);

    const metrics = useMemo(() => {
        const run = runs.find((r) => r.id === selectedRunId);
        return run?.metrics ?? {};
    }, [runs, selectedRunId]);

    const ndcg = useMemo(() => {
        // summary.csv에서 들어온 키를 우선 사용 (예: "ndcg@5")
        const key = Object.keys(metrics).find((k) => k.toLowerCase().includes('ndcg')) || '';
        if (!key) return null;
        const v = metrics[key];
        if (!v) return null;
        const delta = v.after - v.before;
        return { key, before: v.before, after: v.after, delta };
    }, [metrics]);

    const beforeTop5 = useMemo(() => pickTopByRank(candidates, 'before', 5), [candidates]);
    const afterTop5 = useMemo(() => pickTopByRank(candidates, 'after', 5), [candidates]);

    useEffect(() => {
        fetchProducts()
            .then((res) => {
                const list = res.products || [];
                setProducts(list);
                if (!productName && list.length > 0 && typeof list[0] === 'string') setProductName(list[0]);
            })
            .catch(() => {
                // 제품 목록은 UX용: 실패해도 입력으로 대체 가능
                setProducts([]);
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (!productName) return;
        setLoading(true);
        setError(null);
        adminListCtrRankerRuns(productName)
            .then((res) => {
                setRuns(res.runs || []);
                const latest = res.runs?.[0]?.id;
                if (latest) setSelectedRunId(latest);
            })
            .catch((e) => setError(String(e?.message || e)))
            .finally(() => setLoading(false));
    }, [productName]);

    useEffect(() => {
        if (!selectedRunId) return;
        setLoading(true);
        setError(null);
        adminListCtrRankerCandidates(selectedRunId)
            .then((res) => {
                setApprovedCandidateId(res.approved_candidate_id ?? null);
                setCandidates(res.candidates || []);
                setSummary(res.summary || null);
            })
            .catch((e) => setError(String(e?.message || e)))
            .finally(() => setLoading(false));
    }, [selectedRunId]);

    async function onImport() {
        if (!productName) return;
        setLoading(true);
        setError(null);
        try {
            await adminImportCtrRankerRun({ product_name: productName, report_date: reportDate });
            const res = await adminListCtrRankerRuns(productName);
            setRuns(res.runs || []);
            const latest = res.runs?.[0]?.id;
            if (latest) setSelectedRunId(latest);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setLoading(false);
        }
    }

    async function onApprove(candidateId: number) {
        if (!selectedRunId) return;
        setLoading(true);
        setError(null);
        try {
            const res = await adminApproveCtrRankerCandidate(selectedRunId, { candidate_id: candidateId });
            setApprovedCandidateId(res.approval.candidate_id);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setLoading(false);
        }
    }

    const top5Help = (
        <p className="text-sm text-slate-500">
            Score는 스케일이 달라서 직접 비교하지 않고, Top5 구성 변화와 proxy_score를 기준으로 판단합니다.
        </p>
    );

    return (
        <div className="grid gap-6">
            <Card className="p-5 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-sm">
                <div className="flex flex-wrap items-end gap-3">
                    <div className="min-w-[220px]">
                        <label className="block text-xs font-semibold text-slate-600 mb-1">제품</label>
                        {products.length > 0 ? (
                            <select
                                value={productName}
                                onChange={(e) => setProductName(e.target.value)}
                                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                            >
                                {products.map((p) => (
                                    <option key={p} value={p}>
                                        {p}
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <input
                                value={productName}
                                onChange={(e) => setProductName(e.target.value)}
                                placeholder="제품명 입력"
                                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                            />
                        )}
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-600 mb-1">리포트 날짜</label>
                        <input
                            type="date"
                            value={reportDate}
                            onChange={(e) => setReportDate(e.target.value)}
                            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                        />
                    </div>

                    <Button
                        onClick={onImport}
                        disabled={loading || !productName}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
                    >
                        {loading ? '처리 중...' : 'Import (로컬 outputs)'}
                    </Button>

                    <div className="ml-auto min-w-[260px]">
                        <label className="block text-xs font-semibold text-slate-600 mb-1">Run 선택</label>
                        <select
                            value={selectedRunId}
                            onChange={(e) => setSelectedRunId(e.target.value)}
                            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                            disabled={runs.length === 0}
                        >
                            {runs.length === 0 ? <option value="">run 없음</option> : null}
                            {runs.map((r) => (
                                <option key={r.id} value={r.id}>
                                    {r.report_date} ({r.mode})
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {error ? <p className="mt-3 text-sm text-red-600 font-medium">{error}</p> : null}
            </Card>

            <Card className="p-5 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-sm">
                <h2 className="font-display text-xl font-bold text-slate-900 mb-3">요약</h2>
                <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-xs font-semibold text-slate-500">Top1 변경</p>
                        <p className="mt-1 text-sm text-slate-900">
                            {summary ? (summary.top1_changed ? '바뀜' : '유지') : '-'}
                        </p>
                        <p className="mt-2 text-xs text-slate-500 line-clamp-2">
                            before: {summary?.top1_before_title || '-'}
                        </p>
                        <p className="text-xs text-slate-500 line-clamp-2">
                            after: {summary?.top1_after_title || '-'}
                        </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-xs font-semibold text-slate-500">Entered / Dropped</p>
                        <p className="mt-1 text-sm text-slate-900">
                            {summary ? `${summary.entered_count} / ${summary.dropped_count}` : '-'}
                        </p>
                        <p className="mt-2 text-xs text-slate-500">Top5 기준 후보 교체량</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                        <p className="text-xs font-semibold text-slate-500">{ndcg ? ndcg.key : 'NDCG'}</p>
                        <p className="mt-1 text-sm text-slate-900">
                            {ndcg ? `${ndcg.before.toFixed(4)} → ${ndcg.after.toFixed(4)}` : '-'}
                        </p>
                        <p className="mt-2 text-xs text-slate-500">
                            {ndcg ? `Δ ${ndcg.delta >= 0 ? '+' : ''}${ndcg.delta.toFixed(4)}` : 'summary.csv 없으면 -'}
                        </p>
                    </div>
                </div>
            </Card>

            <div className="grid gap-6 lg:grid-cols-2">
                <Card className="p-5 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-sm">
                    <div className="flex items-center justify-between">
                        <h2 className="font-display text-xl font-bold text-slate-900">Before Top5</h2>
                    </div>
                    {top5Help}
                    <div className="mt-3 overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-left text-slate-500">
                                    <th className="py-2 pr-3">#</th>
                                    <th className="py-2 pr-3">title</th>
                                    <th className="py-2 pr-3">proxy</th>
                                </tr>
                            </thead>
                            <tbody>
                                {beforeTop5.map((c) => (
                                    <tr key={c.id} className="border-t border-slate-100">
                                        <td className="py-2 pr-3 font-semibold text-slate-700">{c.baseline_rank}</td>
                                        <td className="py-2 pr-3 text-slate-900">{c.title}</td>
                                        <td className="py-2 pr-3 text-slate-600">{c.proxy_score?.toFixed?.(4) ?? '-'}</td>
                                    </tr>
                                ))}
                                {beforeTop5.length === 0 ? (
                                    <tr>
                                        <td className="py-3 text-slate-500" colSpan={3}>
                                            데이터 없음
                                        </td>
                                    </tr>
                                ) : null}
                            </tbody>
                        </table>
                    </div>
                </Card>

                <Card className="p-5 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-sm">
                    <div className="flex items-center justify-between">
                        <h2 className="font-display text-xl font-bold text-slate-900">After Top5</h2>
                        <p className="text-xs text-slate-500">승인 1개만 유지</p>
                    </div>
                    {top5Help}
                    <div className="mt-3 overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-left text-slate-500">
                                    <th className="py-2 pr-3">#</th>
                                    <th className="py-2 pr-3">title</th>
                                    <th className="py-2 pr-3">proxy</th>
                                    <th className="py-2 pr-3">approve</th>
                                </tr>
                            </thead>
                            <tbody>
                                {afterTop5.map((c) => {
                                    const isApproved = approvedCandidateId === c.id;
                                    return (
                                        <tr key={c.id} className="border-t border-slate-100">
                                            <td className="py-2 pr-3 font-semibold text-slate-700">{c.after_rank}</td>
                                            <td className="py-2 pr-3 text-slate-900">{c.title}</td>
                                            <td className="py-2 pr-3 text-slate-600">{c.proxy_score?.toFixed?.(4) ?? '-'}</td>
                                            <td className="py-2 pr-3">
                                                <Button
                                                    onClick={() => onApprove(c.id)}
                                                    disabled={loading}
                                                    variant={isApproved ? 'secondary' : 'default'}
                                                    className={
                                                        isApproved
                                                            ? 'bg-slate-900 hover:bg-slate-800 text-white font-semibold'
                                                            : 'bg-indigo-600 hover:bg-indigo-700 text-white font-semibold'
                                                    }
                                                >
                                                    {isApproved ? '승인됨' : '승인'}
                                                </Button>
                                            </td>
                                        </tr>
                                    );
                                })}
                                {afterTop5.length === 0 ? (
                                    <tr>
                                        <td className="py-3 text-slate-500" colSpan={4}>
                                            데이터 없음
                                        </td>
                                    </tr>
                                ) : null}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </div>

            <Card className="p-5 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-sm">
                <h2 className="font-display text-xl font-bold text-slate-900 mb-2">현재 승인</h2>
                <p className="text-sm text-slate-600">
                    승인된 candidate_id: <span className="font-semibold text-slate-900">{approvedCandidateId ?? '-'}</span>
                </p>
                <p className="mt-2 text-xs text-slate-500">
                    승인 이후에는 이 값을 downstream(F12 스튜디오/콘텐츠 생성)에서 “대표안”으로 사용하면 됩니다.
                </p>
            </Card>
        </div>
    );
}
