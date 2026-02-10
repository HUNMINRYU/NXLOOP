'use client';

import { useCallback, useEffect, useState } from 'react';
import { Navbar } from '@/features/landing';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import ChatbotPanel from '@/components/ChatbotPanel';
import {
    fetchInsightFailures,
    fetchInsightMetrics,
    getChatRemaining,
    ingestNaverInsights,
    ingestYoutubeInsights,
    searchInsights,
} from '@/lib/api';
import type {
    InsightDoc,
    InsightFailureEvent,
    InsightMetricsResponse,
} from '@/types/insights';
import { useAuthStore } from '@/store/useAuthStore';

export default function InsightsDashboardClient() {
    // --- States ---
    const [metricsDays, setMetricsDays] = useState(7);
    const [metrics, setMetrics] = useState<InsightMetricsResponse | null>(null);
    const [metricsLoading, setMetricsLoading] = useState(false);

    const [failures, setFailures] = useState<InsightFailureEvent[]>([]);
    const [failureLoading, setFailureLoading] = useState(false);

    const [searchQuery, setSearchQuery] = useState('');
    const [results, setResults] = useState<InsightDoc[]>([]);
    const [searching, setSearching] = useState(false);

    const [naverQuery, setNaverQuery] = useState('');
    const [naverLoading, setNaverLoading] = useState(false);
    const [youtubeQuery, setYoutubeQuery] = useState('');
    const [youtubeLoading, setYoutubeLoading] = useState(false);

    // --- Usage (server truth) ---
    const tier = useAuthStore((s) => s.tier) ?? 'FREE';
    const subscriptionStatus = useAuthStore((s) => s.subscriptionStatus) ?? 'none';
    const [chatUsage, setChatUsage] = useState<{
        remaining: number | null;
        resets_at?: string;
        limit_per_day?: number;
    } | null>(null);
    const [chatUsageLoading, setChatUsageLoading] = useState(false);

    // --- Real Chatbot State ---
    const [isChatOpen, setIsChatOpen] = useState(false);

    // --- Effects ---
    const loadDashboardData = useCallback(async () => {
        setMetricsLoading(true);
        setFailureLoading(true);
        setChatUsageLoading(true);
        try {
            const [m, f] = await Promise.all([
                fetchInsightMetrics(metricsDays),
                fetchInsightFailures({ days: metricsDays, limit: 5 }),
            ]);
            setMetrics(m);
            setFailures(f.items);
            try {
                const usage = await getChatRemaining();
                setChatUsage(usage);
            } catch (err) {
                console.error('Failed to load chatbot usage', err);
                setChatUsage(null);
            }
        } catch (err) {
            console.error('Failed to load dashboard data', err);
        } finally {
            setMetricsLoading(false);
            setFailureLoading(false);
            setChatUsageLoading(false);
        }
    }, [metricsDays]);

    useEffect(() => {
        void loadDashboardData();
    }, [loadDashboardData]);

    // --- Actions ---
    const handleSearch = async () => {
        if (!searchQuery.trim()) return;
        setSearching(true);
        try {
            const data = await searchInsights({ query: searchQuery });
            setResults(data.results);
        } catch (err) {
            console.error(err);
        } finally {
            setSearching(false);
        }
    };

    const handleForceIngestNaver = async () => {
        const query = window.prompt('네이버 수집 키워드를 입력하세요.', naverQuery) ?? '';
        const trimmed = query.trim();
        if (!trimmed) return;

        setNaverQuery(trimmed);
        setNaverLoading(true);
        try {
            await ingestNaverInsights({
                query: trimmed,
                max_results: 20,
                include_products: true,
                include_blogs: true,
                include_news: true,
            });
            await loadDashboardData();
        } catch (err) {
            console.error(err);
        } finally {
            setNaverLoading(false);
        }
    };

    const handleForceIngestYoutube = async () => {
        const query = window.prompt('유튜브 수집 키워드를 입력하세요.', youtubeQuery) ?? '';
        const trimmed = query.trim();
        if (!trimmed) return;

        setYoutubeQuery(trimmed);
        setYoutubeLoading(true);
        try {
            await ingestYoutubeInsights({
                query: trimmed,
                max_results: 20,
                include_comments: true,
            });
            await loadDashboardData();
        } catch (err) {
            console.error(err);
        } finally {
            setYoutubeLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen overflow-hidden pb-12">
            {/* Light Elegant Background */}
            <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
            <div className="absolute inset-0 bg-gradient-to-tr from-teal-500/[0.02] via-transparent to-indigo-500/[0.02]" />
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
            <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-teal-400/[0.06] blur-[140px] rounded-full" />
            <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />

            <Navbar />

            <main className="relative z-10 max-w-[1400px] mx-auto px-6 pt-24 space-y-6">
                {/* Top Action Bar: 스크린샷처럼 필터와 액션 버튼 배치 */}
                <div className="flex flex-wrap items-center justify-between gap-4 bg-white/80 backdrop-blur-xl p-4 rounded-xl border border-slate-200/60 shadow-lg shadow-slate-200/50">
                    <div className="flex items-center gap-3">
                        <select
                            className="bg-slate-50 border-none text-sm font-bold p-2 rounded-lg outline-none cursor-pointer"
                            value={metricsDays}
                            onChange={(e) => setMetricsDays(Number(e.target.value))}
                        >
                            <option value={7}>지난 7일간</option>
                            <option value={30}>지난 30일간</option>
                        </select>
                        <select className="bg-slate-50 border-none text-sm font-bold p-2 rounded-lg outline-none cursor-pointer">
                            <option>전략 대시보드 모드</option>
                            <option>시스템 로그 모드</option>
                        </select>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            className="rounded-lg h-10 border-slate-200 text-slate-600 font-bold"
                            onClick={() => setIsChatOpen(true)}
                        >
                            AI 챗봇
                        </Button>
                        <Button variant="outline" className="rounded-lg h-10 border-slate-200 text-slate-600 font-bold">
                            + 필터 레이아웃
                        </Button>
                        <Button className="rounded-lg h-10 bg-[#0ca678] hover:bg-[#099268] text-white font-bold px-6 shadow-lg shadow-emerald-100">
                            + 새 파이프라인 만들기
                        </Button>
                    </div>
                </div>

                {/* Search Bar 섹션 */}
                <div className="relative group">
                    <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2"
                                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                            />
                        </svg>
                    </div>
                    <input
                        className="w-full bg-white border border-slate-200 rounded-xl py-4 pl-12 pr-4 outline-none focus:ring-2 focus:ring-[#0ca678]/20 focus:border-[#0ca678] transition-all shadow-sm text-slate-600 font-medium"
                        placeholder={searching ? '검색 중...' : '지식 베이스, 채널명, 또는 캠페인 상태로 검색...'}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        disabled={searching}
                    />
                </div>

                {/* Top Row: KPI 카드 섹션 */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                    <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50 flex flex-col justify-between h-32 relative overflow-hidden">
                        <div>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">챗봇 사용량</p>
                            <div className="flex items-baseline gap-2 mt-1">
                                <h3 className="text-2xl font-black text-slate-900">
                                    {chatUsageLoading
                                        ? '...'
                                        : chatUsage?.remaining === null
                                            ? '∞'
                                            : typeof chatUsage?.remaining === 'number'
                                                ? chatUsage.remaining
                                                : '-'}
                                </h3>
                                <span className="text-xs font-bold text-slate-500">
                                    {tier}
                                    {subscriptionStatus !== 'none' ? ` · ${subscriptionStatus}` : ''}
                                </span>
                            </div>
                        </div>
                        <div className="mt-2 text-xs font-semibold text-slate-500">
                            {chatUsage?.remaining === null
                                ? '무제한'
                                : chatUsage?.resets_at
                                    ? `리필: ${new Date(chatUsage.resets_at).toLocaleString()}`
                                    : ''}
                        </div>
                    </Card>

                    <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50 flex flex-col justify-between h-32 relative overflow-hidden">
                        <div>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">인사이트 수집량</p>
                            <div className="flex items-baseline gap-2 mt-1">
                                <h3 className="text-2xl font-black text-slate-900">
                                    {metricsLoading ? '...' : metrics?.total || 0}
                                </h3>
                                <span className="text-sm font-bold text-emerald-500">↑ 28.9%</span>
                            </div>
                        </div>
                        <div className="mt-2 h-8 w-full bg-emerald-50 rounded flex items-end p-1 gap-1">
                            {[40, 70, 45, 90, 65, 80, 55].map((h, i) => (
                                <div key={i} className="flex-1 bg-emerald-400 rounded-sm" style={{ height: `${h}%` }} />
                            ))}
                        </div>
                    </Card>

                    <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50 flex flex-col justify-between h-32 relative overflow-hidden">
                        <div>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                                지식 정확도 (Avg)
                            </p>
                            <div className="flex items-baseline gap-2 mt-1">
                                <h3 className="text-2xl font-black text-slate-900">94.2%</h3>
                                <span className="text-sm font-bold text-indigo-500">↑ 5.4%</span>
                            </div>
                        </div>
                        <div className="mt-2 h-8 w-full bg-indigo-50 rounded flex items-end p-1 gap-1">
                            {[30, 50, 75, 60, 85, 45, 95].map((h, i) => (
                                <div key={i} className="flex-1 bg-indigo-400 rounded-sm" style={{ height: `${h}%` }} />
                            ))}
                        </div>
                    </Card>

	                    <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50 flex flex-col justify-between h-32 group hover:bg-[#0ca678] transition-colors cursor-pointer">
	                        <div>
	                            <p className="text-xs font-bold text-slate-400 group-hover:text-white/70 uppercase tracking-wider">
	                                수집 에러 알림
	                            </p>
	                            <h3 className="text-2xl font-black text-slate-900 group-hover:text-white mt-1">
	                                {failureLoading ? '...' : `${failures.length}건`}
	                            </h3>
	                        </div>
                        <div className="text-xs font-bold text-slate-400 group-hover:text-white/70 flex items-center gap-1">
                            상태 체크 완료{' '}
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                    </Card>

                    <div className="space-y-3">
                        <div className="bg-white p-3 rounded-xl border border-l-4 border-l-amber-500 shadow-sm flex items-center justify-between">
                            <div>
                                <p className="text-[10px] font-bold text-amber-600">CPC 높음 경고</p>
                                <p className="text-sm font-black text-slate-800">유튜브 트렌드</p>
                            </div>
                            <span className="bg-slate-50 text-slate-400 px-2 py-1 rounded text-[10px] font-bold">
                                12건 {'>'}
                            </span>
                        </div>
                        <div className="bg-white p-3 rounded-xl border border-l-4 border-l-rose-500 shadow-sm flex items-center justify-between">
                            <div>
                                <p className="text-[10px] font-bold text-rose-600">데이터 누락 발생</p>
                                <p className="text-sm font-black text-slate-800">네이버 쇼핑몰</p>
                            </div>
                            <span className="bg-slate-50 text-slate-400 px-2 py-1 rounded text-[10px] font-bold">
                                5건 {'>'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Middle Row: 시각화 차트 및 목표 달성률 */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* 채널별 데이터 분포 (Bubble Chart Style placeholder) */}
                    <Card className="lg:col-span-2 p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50 space-y-4">
                        <div className="flex items-center justify-between border-b border-slate-50 pb-4">
                            <h4 className="font-black text-slate-800 flex items-center gap-2">
                                <span className="w-2 h-6 bg-[#0ca678] rounded-full" />
                                채널별 마케팅 전략 분포
                            </h4>
                            <div className="flex gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
                                <span>결과 대비 정확도 (A/B)</span>
                            </div>
                        </div>
                        <div className="h-[300px] relative bg-slate-50/50 rounded-2xl border border-dashed border-slate-200 flex items-center justify-center overflow-hidden">
                            {/* 버블 차트 시각화 모사 */}
                            <div className="absolute top-1/4 left-1/4 w-32 h-32 bg-blue-500/20 border border-blue-500/50 rounded-full flex items-center justify-center animate-pulse">
                                <span className="text-[10px] font-bold text-blue-600">네이버 블로그</span>
                            </div>
                            <div className="absolute bottom-1/3 right-1/4 w-24 h-24 bg-indigo-500/20 border border-indigo-500/50 rounded-full flex items-center justify-center">
                                <span className="text-[10px] font-bold text-indigo-600">유튜브 숏츠</span>
                            </div>
                            <div className="absolute top-1/2 right-1/3 w-16 h-16 bg-emerald-500/20 border border-emerald-500/50 rounded-full flex items-center justify-center">
                                <span className="text-[10px] font-bold text-emerald-600">인스타그램</span>
                            </div>
                            {/* Grid Lines */}
                            <div className="absolute inset-0 grid grid-cols-4 grid-rows-4 opacity-30">
                                {Array.from({ length: 16 }).map((_, i) => (
                                    <div key={i} className="border-[0.5px] border-slate-300" />
                                ))}
                            </div>
                        </div>
                    </Card>

                    {/* 목표 달성률 리스트 */}
                    <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50 space-y-6">
                        <div className="flex items-center gap-2 pb-2 border-b border-slate-50">
                            <span className="text-xl">🎯</span>
                            <h4 className="font-black text-slate-800">이번 주 전략 달성도</h4>
                        </div>
                        <div className="space-y-5">
                            {[
                                {
                                    label: '데이터 수집량',
                                    current: 170768,
                                    target: 1324390,
                                    color: 'bg-emerald-500',
                                    percent: 12.9,
                                },
                                {
                                    label: 'AI 분석 완료율',
                                    current: 204870,
                                    target: 900000,
                                    color: 'bg-blue-500',
                                    percent: 22.8,
                                },
                                {
                                    label: '콘텐츠 생성 성공',
                                    current: 833,
                                    target: 675,
                                    color: 'bg-indigo-500',
                                    percent: 123.3,
                                    exceed: true,
                                },
                                {
                                    label: '전략 일치도(ROAS)',
                                    current: 131.4,
                                    target: 134,
                                    color: 'bg-slate-900',
                                    percent: 98.1,
                                },
                            ].map((goal, i) => (
                                <div key={i} className="space-y-1.5">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-bold text-slate-500 uppercase tracking-tighter">
                                            {goal.label}
                                        </span>
                                        <span className="text-sm font-black text-slate-900">{goal.percent}%</span>
                                    </div>
                                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full ${goal.color} transition-all duration-1000 shadow-sm`}
                                            style={{ width: `${Math.min(goal.percent, 100)}%` }}
                                        />
                                    </div>
                                    <div className="flex justify-between text-[10px] font-bold text-slate-400">
                                        <span>{goal.current.toLocaleString()}</span>
                                        <span>목표 {goal.target.toLocaleString()}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>

                {/* Bottom Section: 최근 인사이트 수집 테이블 */}
                <Card className="p-0 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50 overflow-hidden">
                    <div className="p-6 border-b border-slate-50 flex items-center justify-between bg-white">
                        <h4 className="font-black text-slate-800 flex items-center gap-2">
                            <span className="w-2 h-6 bg-[#6366f1] rounded-full" />
                            실시간 지식 수집 및 분석 내역
                        </h4>
	                        <div className="flex gap-2">
	                            <Button
	                                onClick={handleForceIngestNaver}
	                                variant="outline"
	                                className="text-xs font-bold h-8 border-slate-100"
	                                disabled={naverLoading}
	                            >
	                                {naverLoading ? '수집 중...' : '네이버 강제 수집'}
	                            </Button>
	                            <Button
	                                onClick={handleForceIngestYoutube}
	                                variant="outline"
	                                className="text-xs font-bold h-8 border-slate-100"
	                                disabled={youtubeLoading}
	                            >
	                                {youtubeLoading ? '수집 중...' : '유튜브 강제 수집'}
	                            </Button>
	                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-slate-50/80 text-[11px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-100">
                                <tr>
                                    <th className="px-6 py-4">
                                        채널 {'>'} 마케팅 캠페인 {'>'} 키워드
                                    </th>
                                    <th className="px-6 py-4 text-center">수집 상태</th>
                                    <th className="px-6 py-4 text-right">정확도 점수</th>
                                    <th className="px-6 py-4 text-right">수집 일시</th>
                                    <th className="px-6 py-4">액션</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {results.length > 0 ? (
                                    results.map((res, i) => (
                                        <tr key={i} className="hover:bg-slate-50/50 transition-colors group">
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-lg shadow-inner">
                                                        {res.source === 'youtube' ? '📺' : '🟢'}
                                                    </div>
                                                    <div>
                                                        <p className="text-xs font-black text-slate-400 uppercase leading-none mb-1">
                                                            {res.source}
                                                        </p>
                                                        <p className="text-sm font-bold text-slate-900 group-hover:text-[#0ca678] transition-colors">
                                                            {res.title}
                                                        </p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                <span className="px-2 py-1 rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-bold border border-emerald-100">
                                                    수집완료
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex flex-col items-end">
                                                    <span className="text-sm font-black text-slate-900">89.4점</span>
                                                    <div className="w-16 h-1 bg-slate-100 rounded-full mt-1 overflow-hidden">
                                                        <div className="w-[89%] h-full bg-[#0ca678]" />
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-right text-xs font-bold text-slate-400">
                                                {new Date().toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4">
                                                <button className="text-slate-300 hover:text-slate-900 transition-colors">
                                                    <svg
                                                        className="w-5 h-5"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path
                                                            strokeLinecap="round"
                                                            strokeLinejoin="round"
                                                            strokeWidth="2"
                                                            d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                                                        />
                                                    </svg>
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-20 text-center">
                                            <div className="flex flex-col items-center gap-3 opacity-20">
                                                <div className="text-6xl">📁</div>
                                                <p className="font-black text-lg">최근 수집 내역이 없습니다.</p>
                                                <p className="text-sm font-medium">
                                                    검색 또는 강적 수집을 통해 지식을 보충하세요.
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </main>

            <ChatbotPanel isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
        </div>
    );
}
