'use client';

import Link from 'next/link';
import { Navbar } from '@/features/landing';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import usePipelineHistory from '@/hooks/usePipelineHistory';
import { GcsPath, asTaskId } from '@/types/common';
import { clearCache, deriveGcsPathFromUrl, fetchCacheStats, fetchPipelineResult, refreshUrl } from '@/lib/api';
import { DUMMY_PROMPT_LOGS } from '@/lib/dummyData';
import { useEffect, useMemo, useState } from 'react';
import type { PipelineResult } from '@/types/api';
import type { GeneratedThumbnail } from '@/types/domain';

type SortOption = 'newest' | 'oldest' | 'name';

const slugs: Record<string, { title: string; subtitle: string }> = {
    'video-vault': { title: 'Video Vault', subtitle: 'Storage for completed short-form videos' },
    'asset-library': { title: 'Asset Library', subtitle: 'Storage for generated thumbnails and image sources' },
    'prompt-log': { title: 'Prompt Log', subtitle: 'Management of successful prompt history' },
};

type StorageSlugClientProps = {
    slug: string;
};

type MediaItem = { url: string; gcsPath: GcsPath | null; retries: number };

export default function StorageSlugClient({ slug }: StorageSlugClientProps) {
    const item = slugs[slug];
    const { tasks, error, isLoading, isDummy } = usePipelineHistory();
    const [results, setResults] = useState<Record<string, PipelineResult>>({});
    const [selectedProduct, setSelectedProduct] = useState<string>('all');
    const [cacheStats, setCacheStats] = useState<{
        total_entries?: number;
        active_entries?: number;
        expired_entries?: number;
    } | null>(null);
    const [cacheMessage, setCacheMessage] = useState('');
    const [videoItems, setVideoItems] = useState<MediaItem[]>([]);
    const [thumbnailItems, setThumbnailItems] = useState<MediaItem[]>([]);

    // 페이지네이션
    const ITEMS_PER_PAGE = 5;
    const [currentPage, setCurrentPage] = useState(1);

    // 정렬
    const [sortBy, setSortBy] = useState<SortOption>('newest');

    // 검색
    const [searchQuery, setSearchQuery] = useState('');

    // Unique products for dropdown
    const productList = useMemo(() => {
        const ps = new Set<string>();
        tasks.forEach((t) => {
            if (t.product) ps.add(t.product);
        });
        return Array.from(ps).sort();
    }, [tasks]);

    // Filter tasks based on selected product
    const filteredTasks = useMemo(() => {
        if (selectedProduct === 'all') return tasks;
        return tasks.filter((t) => t.product === selectedProduct);
    }, [tasks, selectedProduct]);

    // Step 1: 정렬 + 검색 적용
    const processedTasks = useMemo(() => {
        let result = [...filteredTasks]; // 기존 상품 필터 유지

        // 검색 적용
        if (searchQuery.trim()) {
            result = result.filter(
                (t) =>
                    t.product?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    String(t.task_id).includes(searchQuery),
            );
        }

        // 정렬 적용
        result.sort((a, b) => {
            if (sortBy === 'newest') {
                // executed_at 필드로 정렬. 없으면 task_id 기준
                const timeA = a.executed_at ? new Date(a.executed_at).getTime() : 0;
                const timeB = b.executed_at ? new Date(b.executed_at).getTime() : 0;
                return timeB - timeA;
            }
            if (sortBy === 'oldest') {
                const timeA = a.executed_at ? new Date(a.executed_at).getTime() : 0;
                const timeB = b.executed_at ? new Date(b.executed_at).getTime() : 0;
                return timeA - timeB;
            }
            // name 정렬
            return (a.product || '').localeCompare(b.product || '');
        });

        return result;
    }, [filteredTasks, searchQuery, sortBy]);

    // Step 2: 페이지네이션 적용
    const paginatedTasks = useMemo(() => {
        const start = (currentPage - 1) * ITEMS_PER_PAGE;
        return processedTasks.slice(start, start + ITEMS_PER_PAGE);
    }, [processedTasks, currentPage]);

    // Step 3: 총 페이지 수 계산
    const totalPages = Math.ceil(processedTasks.length / ITEMS_PER_PAGE);

    useEffect(() => {
        if (!slug || tasks.length === 0) {
            return;
        }
        const taskIds = tasks
            .map((task) => (task.task_id ? asTaskId(String(task.task_id)) : null))
            .filter((taskId): taskId is ReturnType<typeof asTaskId> => Boolean(taskId));

        Promise.all(
            taskIds.map((taskId) =>
                fetchPipelineResult(taskId)
                    .then((data) => ({ taskId, data }))
                    .catch(() => null),
            ),
        ).then((items) => {
            const mapped: Record<string, PipelineResult> = {};
            items.forEach((entry) => {
                if (!entry) return;
                mapped[entry.taskId] = entry.data;
            });
            setResults(mapped);
        });
    }, [slug, tasks]);

    useEffect(() => {
        if (slug === 'prompt-log') {
            fetchCacheStats()
                .then((data) => setCacheStats(data.stats))
                .catch(() => setCacheStats(null));
        }
    }, [slug]);

    const videoUrls = useMemo(() => {
        if (slug !== 'video-vault') return [];
        return paginatedTasks
            .map((task) => results[String(task.task_id)]?.result?.generated_content?.video_url)
            .filter((url): url is string => Boolean(url));
    }, [results, slug, paginatedTasks]);

    const thumbnailUrls = useMemo(() => {
        if (slug !== 'asset-library') return [];
        const items: string[] = [];
        paginatedTasks.forEach((task) => {
            const content = results[String(task.task_id)]?.result?.generated_content;
            if (content?.thumbnail_url) items.push(content.thumbnail_url);
            if (Array.isArray(content?.multi_thumbnails)) {
                content.multi_thumbnails.forEach((thumb: GeneratedThumbnail) => {
                    const url = thumb.url || thumb.thumbnail_url || thumb.image_url;
                    if (url) items.push(url);
                });
            }
        });
        return items;
    }, [results, slug, paginatedTasks]);

    useEffect(() => {
        if (slug === 'video-vault') {
            queueMicrotask(() =>
                setVideoItems(
                    videoUrls.map((url) => ({
                        url,
                        gcsPath: deriveGcsPathFromUrl(url),
                        retries: 0,
                    })),
                ),
            );
        }
    }, [videoUrls, slug]);

    useEffect(() => {
        if (slug === 'asset-library') {
            queueMicrotask(() =>
                setThumbnailItems(
                    thumbnailUrls.map((url) => ({
                        url,
                        gcsPath: deriveGcsPathFromUrl(url),
                        retries: 0,
                    })),
                ),
            );
        }
    }, [thumbnailUrls, slug]);

    const handleRefreshMedia = async (kind: 'video' | 'thumb', index: number, gcsPath: GcsPath | null) => {
        if (!gcsPath) return;
        try {
            const result = await refreshUrl(gcsPath);
            if (kind === 'video') {
                setVideoItems((prev) =>
                    prev.map((item, idx) =>
                        idx === index ? { ...item, url: result.url, retries: item.retries + 1 } : item,
                    ),
                );
            } else {
                setThumbnailItems((prev) =>
                    prev.map((item, idx) =>
                        idx === index ? { ...item, url: result.url, retries: item.retries + 1 } : item,
                    ),
                );
            }
        } catch {
            /* silent */
        }
    };

    const handleCacheClear = async () => {
        setCacheMessage('');
        try {
            const result = await clearCache();
            setCacheMessage(`캐시 ${result.cleared}개 삭제`);
            const updated = await fetchCacheStats();
            setCacheStats(updated.stats);
        } catch {
            setCacheMessage('캐시 삭제 실패');
        }
    };

    if (!item) {
        return (
            <>
                <Navbar />
                <main className="relative min-h-screen overflow-hidden flex flex-col items-center justify-center">
                    {/* Layer 1: Light Elegant Base */}
                    <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />

                    {/* Layer 2: Subtle Colored Wash */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-slate-500/[0.02] via-transparent to-slate-500/[0.02]" />

                    {/* Layer 3: Refined Grid Pattern */}
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

                    {/* Layer 4: Subtle Glow */}
                    <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-slate-400/[0.04] blur-[140px] rounded-full" />

                    <div className="relative z-10 p-8 pt-24">
                        <Card className="max-w-2xl w-full text-center border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
                            <h1 className="text-4xl font-bold mb-4 text-slate-900">Not Found</h1>
                            <p className="text-slate-600 mb-6">The page you&apos;re looking for doesn&apos;t exist.</p>
                            <Button asChild variant="secondary" className="bg-slate-900 hover:bg-slate-800 text-white">
                                <Link href="/">Back to Home</Link>
                            </Button>
                        </Card>
                    </div>
                </main>
            </>
        );
    }

    return (
        <>
            <Navbar />
            <main className="relative min-h-screen overflow-hidden">
                {/* Layer 1: Light Elegant Base */}
                <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />

                {/* Layer 2: Subtle Colored Wash (slug-specific) */}
                {slug === 'video-vault' && (
                    <div className="absolute inset-0 bg-gradient-to-tr from-teal-500/[0.02] via-transparent to-indigo-500/[0.02]" />
                )}
                {slug === 'asset-library' && (
                    <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/[0.02] via-transparent to-amber-500/[0.02]" />
                )}
                {slug === 'prompt-log' && (
                    <div className="absolute inset-0 bg-gradient-to-tr from-amber-500/[0.02] via-transparent to-teal-500/[0.02]" />
                )}

                {/* Layer 3: Refined Grid Pattern */}
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

                {/* Layer 4: Ethereal Glow Orbs (slug별 색상) */}
                {slug === 'video-vault' && (
                    <>
                        <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-teal-400/[0.06] blur-[140px] rounded-full" />
                        <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />
                    </>
                )}
                {slug === 'asset-library' && (
                    <>
                        <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />
                        <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-amber-400/[0.06] blur-[140px] rounded-full" />
                    </>
                )}
                {slug === 'prompt-log' && (
                    <>
                        <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-amber-400/[0.06] blur-[140px] rounded-full" />
                        <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-teal-400/[0.06] blur-[140px] rounded-full" />
                    </>
                )}

                {/* Layer 5: Accent Shimmer (slug-specific) */}
                {slug === 'video-vault' && (
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-r from-teal-500/[0.03] to-indigo-500/[0.03] blur-[100px] rounded-full" />
                )}
                {slug === 'asset-library' && (
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-r from-indigo-500/[0.03] to-amber-500/[0.03] blur-[100px] rounded-full" />
                )}
                {slug === 'prompt-log' && (
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-r from-amber-500/[0.03] to-teal-500/[0.03] blur-[100px] rounded-full" />
                )}

                {/* 콘텐츠 */}
                <div className="relative z-10 p-8 pt-32">
                    <div className="max-w-6xl mx-auto">
                    {/* Header Section */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
                        <div>
                            <h2 className="font-display text-teal-600 font-semibold uppercase tracking-[0.2em] mb-3 text-sm">
                                Storage / {slug.replace('-', ' ')}
                            </h2>
                            <h1 className="font-display text-5xl md:text-6xl font-bold mb-4 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-slate-800 to-slate-600 leading-[1.1]">
                                {item.title}
                            </h1>
                            <p className="font-body text-xl text-slate-600 font-medium leading-relaxed">
                                {item.subtitle}
                            </p>
                        </div>

                        {/* Filter Section */}
                        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/60 p-2 rounded-2xl flex items-center gap-4 shadow-sm">
                            <span className="text-xs font-black uppercase tracking-[0.15em] ml-4 text-slate-500">
                                Filter by Product
                            </span>
                            <select
                                value={selectedProduct}
                                onChange={(e) => setSelectedProduct(e.target.value)}
                                className="bg-white border border-slate-200 text-sm font-bold p-3 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 min-w-[200px] cursor-pointer text-slate-900"
                            >
                                <option value="all">All Products</option>
                                {productList.map((p) => (
                                    <option key={p} value={p}>
                                        {p}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* 정렬/검색 컨트롤 */}
                    <div className="mt-6 flex flex-col md:flex-row gap-4">
                        {/* 정렬 드롭다운 */}
                        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/60 p-2 rounded-2xl flex items-center gap-4 flex-1 shadow-sm">
                            <span className="text-xs font-black uppercase tracking-[0.15em] ml-4 text-slate-500">
                                정렬
                            </span>
                            <select
                                value={sortBy}
                                onChange={(e) => {
                                    setSortBy(e.target.value as SortOption);
                                    setCurrentPage(1);
                                }}
                                className="bg-white border border-slate-200 text-sm font-bold p-3 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 flex-1 cursor-pointer text-slate-900"
                            >
                                <option value="newest">최신순</option>
                                <option value="oldest">오래된순</option>
                                <option value="name">상품명순</option>
                            </select>
                        </div>

                        {/* 검색 입력 */}
                        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/60 p-2 rounded-2xl flex items-center gap-4 flex-1 shadow-sm">
                            <span className="text-xs font-black uppercase tracking-[0.15em] ml-4 text-slate-500">
                                검색
                            </span>
                            <input
                                type="search"
                                placeholder="상품명 또는 Task ID..."
                                value={searchQuery}
                                onChange={(e) => {
                                    setSearchQuery(e.target.value);
                                    setCurrentPage(1);
                                }}
                                className="bg-white border border-slate-200 text-sm font-bold p-3 rounded-xl outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 flex-1 text-slate-900 placeholder:text-slate-400"
                            />
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="flex flex-col items-center py-20">
                            <div className="w-12 h-12 rounded-full border-4 border-teal-500 border-t-transparent animate-spin mb-4" />
                            <p className="text-sm font-bold text-slate-600">데이터를 불러오는 중입니다...</p>
                        </div>
                    ) : error ? (
                        <Card className="p-8 border-rose-200/60 bg-rose-50 text-center shadow-lg shadow-rose-200/50">
                            <p className="text-sm font-bold text-rose-700">{error}</p>
                        </Card>
                    ) : (
                        <div className="space-y-12">
                            {slug === 'video-vault' && (
                                <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                                    {videoItems.length === 0 ? (
                                        <div className="col-span-full py-32 text-center border-2 border-dashed border-slate-200/60 rounded-3xl bg-white/40">
                                            <p className="text-slate-500 font-bold">
                                                표시할 비디오가 없습니다.
                                            </p>
                                        </div>
                                    ) : (
                                        videoItems.map((item, idx) => (
                                            <div key={`${item.url}-${idx}`} className="group relative">
                                                <Card className="p-0 overflow-hidden border-slate-200/60 bg-white/80 backdrop-blur-xl transition-all duration-500 hover:scale-[1.02] hover:shadow-xl hover:shadow-slate-300/50 shadow-lg shadow-slate-200/50">
                                                    <div className="aspect-[9/16] bg-slate-900 flex items-center justify-center relative">
                                                        <video
                                                            src={item.url}
                                                            controls
                                                            className="w-full h-full object-contain"
                                                            onError={() => {
                                                                if (item.retries < 2)
                                                                    handleRefreshMedia('video', idx, item.gcsPath);
                                                            }}
                                                        />
                                                    </div>
                                                    <div className="p-4 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
                                                        <span className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-500">
                                                            {item.gcsPath?.split('/').pop() || 'Video Asset'}
                                                        </span>
                                                        <a
                                                            href={item.url}
                                                            download
                                                            className="text-xs font-black text-teal-600 hover:text-teal-700 hover:underline transition-colors"
                                                        >
                                                            DOWNLOAD
                                                        </a>
                                                    </div>
                                                </Card>
                                            </div>
                                        ))
                                    )}
                                </div>
                            )}

                            {slug === 'asset-library' && (
                                <div className="grid gap-6 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                                    {thumbnailItems.length === 0 ? (
                                        <div className="col-span-full py-32 text-center border-2 border-dashed border-slate-200/60 rounded-3xl bg-white/40">
                                            <p className="text-slate-500 font-bold">
                                                표시할 썸네일이 없습니다.
                                            </p>
                                        </div>
                                    ) : (
	                                        thumbnailItems.map((item, idx) => (
	                                            <div key={`${item.url}-${idx}`} className="group relative">
	                                                <Card className="p-0 overflow-hidden border-slate-200/60 bg-white/80 backdrop-blur-xl transition-all hover:scale-[1.05] hover:shadow-xl hover:shadow-slate-300/50 shadow-lg shadow-slate-200/50">
	                                                    {/* eslint-disable-next-line @next/next/no-img-element -- 외부/동적 URL(서명 URL 포함)이라 next/image 최적화 적용이 어렵습니다. */}
	                                                    <img
	                                                        src={item.url}
	                                                        alt={`thumb-${idx}`}
	                                                        className="w-full aspect-[9/16] object-cover"
	                                                        onError={() => {
	                                                            if (item.retries < 2)
                                                                handleRefreshMedia('thumb', idx, item.gcsPath);
                                                        }}
                                                    />
                                                    <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-slate-900/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <a
                                                            href={item.url}
                                                            download
                                                            className="text-[10px] font-black text-white hover:text-teal-300 block text-center uppercase tracking-[0.15em] transition-colors"
                                                        >
                                                            Download Asset
                                                        </a>
                                                    </div>
                                                </Card>
                                            </div>
                                        ))
                                    )}
                                </div>
                            )}

                            {slug === 'prompt-log' && (
                                <div className="space-y-6">
                                    {/* Cache Control Card */}
                                    <Card className="border-slate-200/60 bg-gradient-to-br from-white to-slate-50 p-8 shadow-lg shadow-slate-200/50">
                                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
                                            <div>
                                                <h4 className="text-2xl font-bold mb-2 text-slate-900">Cache Performance</h4>
                                                <p className="text-slate-600 font-medium mb-6 leading-relaxed">
                                                    Manage AI inference history and optimize database performance.
                                                </p>

                                                <div className="flex gap-8">
                                                    <div className="text-center">
                                                        <p className="text-3xl font-bold text-slate-900">
                                                            {cacheStats?.total_entries ?? '-'}
                                                        </p>
                                                        <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-500">
                                                            Total
                                                        </p>
                                                    </div>
                                                    <div className="text-center">
                                                        <p className="text-3xl font-bold text-emerald-600">
                                                            {cacheStats?.active_entries ?? '-'}
                                                        </p>
                                                        <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-500">
                                                            Active
                                                        </p>
                                                    </div>
                                                    <div className="text-center">
                                                        <p className="text-3xl font-bold text-rose-600">
                                                            {cacheStats?.expired_entries ?? '-'}
                                                        </p>
                                                        <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-500">
                                                            Expired
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex flex-col items-center gap-3">
                                                <Button
                                                    type="button"
                                                    variant="secondary"
                                                    className="px-10 py-6 font-black tracking-[0.15em] bg-slate-900 hover:bg-slate-800 text-white"
                                                    onClick={handleCacheClear}
                                                >
                                                    INITIALIZE CACHE
                                                </Button>
                                                {cacheMessage && (
                                                    <p className="text-xs font-bold text-emerald-600">{cacheMessage}</p>
                                                )}
                                            </div>
                                        </div>
                                    </Card>

                                    <div className="grid gap-6">
                                        {paginatedTasks.length === 0 ? (
                                            <div className="text-center py-20 border-2 border-dashed border-slate-200/60 rounded-3xl bg-white/40">
                                                <p className="text-slate-500 font-bold">
                                                    표시할 프롬프트 이력이 없습니다.
                                                </p>
                                            </div>
                                        ) : (
                                            paginatedTasks.map((task, idx) => {
                                                const promptLog =
                                                    results[task.task_id]?.result?.prompt_log ??
                                                    (isDummy
                                                        ? DUMMY_PROMPT_LOGS[idx % DUMMY_PROMPT_LOGS.length]?.prompt_log
                                                        : null);

                                                return (
                                                    <Card
                                                        key={task.task_id}
                                                        className="border-slate-200/60 bg-white/80 backdrop-blur-xl hover:shadow-lg hover:shadow-slate-300/50 transition-all p-6 shadow-md shadow-slate-200/50"
                                                    >
                                                        <div className="flex items-start justify-between mb-6">
                                                            <div className="space-y-1">
                                                                <div className="flex items-center gap-3">
                                                                    <span className="w-2 h-2 rounded-full bg-teal-500 shadow-[0_0_10px_rgba(20,184,166,0.5)]" />
                                                                    <h5 className="text-lg font-bold tracking-tight text-slate-900">
                                                                        {task.product}
                                                                    </h5>
                                                                </div>
                                                                <p className="text-xs font-bold text-slate-500">
                                                                    ID: {task.task_id}
                                                                </p>
                                                            </div>
                                                            <span
                                                                className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.1em] ${task.status === 'success' ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/50' : 'bg-rose-50 text-rose-700 ring-1 ring-rose-200/50'}`}
                                                            >
                                                                {task.status}
                                                            </span>
                                                        </div>

                                                        {promptLog && (
                                                            <details className="group border border-slate-200/60 rounded-2xl overflow-hidden bg-white/50">
                                                                <summary className="p-4 bg-slate-50/50 cursor-pointer font-black text-[10px] uppercase tracking-[0.15em] group-open:bg-slate-100/50 transition-colors flex justify-between items-center text-slate-700">
                                                                    <span>View Detailed Prompt Log</span>
                                                                    <span className="group-open:rotate-180 transition-transform">
                                                                        ↓
                                                                    </span>
                                                                </summary>
                                                                <div className="p-6 bg-slate-900/95">
                                                                    <pre className="text-xs text-slate-300 font-mono leading-relaxed overflow-x-auto">
                                                                        {JSON.stringify(promptLog, null, 2)}
                                                                    </pre>
                                                                </div>
                                                            </details>
                                                        )}
                                                    </Card>
                                                );
                                            })
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* 페이지네이션 (에셋이 있을 때만 표시) */}
                    {processedTasks.length > ITEMS_PER_PAGE && (
                        <div className="mt-12 mb-8 flex items-center justify-center gap-4">
                            <Button
                                variant="secondary"
                                disabled={currentPage === 1}
                                onClick={() => setCurrentPage((p) => p - 1)}
                                className="font-black px-6 bg-white/80 border-slate-200/60 text-slate-900 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                ← 이전
                            </Button>

                            <div className="flex items-center gap-2">
                                <span className="text-sm font-bold text-slate-700">
                                    {currentPage} / {totalPages}
                                </span>
                                <span className="text-xs text-slate-500">
                                    ({processedTasks.length}개 중{' '}
                                    {Math.min(currentPage * ITEMS_PER_PAGE, processedTasks.length)}개 표시)
                                </span>
                            </div>

                            <Button
                                variant="secondary"
                                disabled={currentPage >= totalPages}
                                onClick={() => setCurrentPage((p) => p + 1)}
                                className="font-black px-6 bg-white/80 border-slate-200/60 text-slate-900 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                다음 →
                            </Button>
                        </div>
                    )}

                    <div className="mt-20 pt-8 border-t border-slate-200/60 flex justify-center">
                        <Button
                            asChild
                            variant="ghost"
                            className="font-black gap-2 hover:bg-slate-100/50 transition-all px-10 py-6 text-slate-700 hover:text-slate-900"
                        >
                            <Link href="/storage">← RETURN TO STORAGE HUB</Link>
                        </Button>
                    </div>
                </div>
                </div>
            </main>
        </>
    );
}
