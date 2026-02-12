'use client';

import Link from 'next/link';
import { Navbar } from '@/features/landing';
import { Card, Button } from '@/components/ui';
import usePipeline from '@/hooks/usePipeline';
import { useAuth } from '@/components/AuthGate';
import { useThumbnailStudio } from '@/features/pipeline/hooks/useThumbnailStudio';
import { useVideoStudio } from '@/features/pipeline/hooks/useVideoStudio';
import { usePipelineApproval } from '@/features/pipeline/hooks/usePipelineApproval';
import { ThumbnailStudioSection } from '@/features/pipeline/components/ThumbnailStudioSection';
import { VideoStudioSection } from '@/features/pipeline/components/VideoStudioSection';
import { PipelineControlSection } from '@/features/pipeline/components/PipelineControlSection';
import { SnsContentSection } from '@/features/pipeline/components/SnsContentSection';
import { DUMMY_THUMBNAILS, DUMMY_VIDEO_URLS } from '@/lib/dummyData';
import { HookStrategy, ThumbnailStyle, VideoPresets } from '@/types/api';
import { fetchPipelineResult, generateVideoFromSelectedThumbnail, predictCtr, selectPipelineOutput } from '@/lib/api';
import { useEffect, useMemo, useState } from 'react';
import { usePipelineStore } from '@/store/usePipelineStore';
import { asTaskId, type TaskId } from '@/types/common';

type UnknownRecord = Record<string, unknown>;

function isRecord(v: unknown): v is UnknownRecord {
    return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function asString(v: unknown): string | undefined {
    return typeof v === 'string' ? v : undefined;
}

const slugs: Record<string, { title: string; subtitle: string }> = {
    'data-source': { title: 'Data Source', subtitle: 'Trend and information collection' },
    'ai-prompt': { title: 'AI Prompt', subtitle: 'Gemini-based prompt generation and optimization' },
    create: { title: 'Create', subtitle: 'AI thumbnail and short-form video automatic generation' },
    distribution: { title: 'Distribution', subtitle: 'Platform-specific optimized distribution' },
    thumbnail: { title: 'Thumbnail Studio', subtitle: '스타일 비교 (훅 테스트 포함, 9종)' },
    video: { title: 'Video Studio', subtitle: 'AI video generation with prompt presets' },
};

type PipelineSlugClientProps = {
    slug: string;
    initialData?: {
        styles?: ThumbnailStyle[];
        hookStrategies?: HookStrategy[];
        videoPresets?: VideoPresets;
    };
};

type DemoStage = {
    id: string;
    at: string;
    title: string;
    summary: string;
    ctaLabel?: string;
    ctaHref?: string;
};

const DEMO_STAGES: DemoStage[] = [
    {
        id: 'landing-problem',
        at: '00:00-00:25',
        title: '랜딩/로그인: 문제 제기와 포지셔닝',
        summary: 'AI Slop 문제를 제시하고, 검증형 AI 플랫폼 포지션으로 진입합니다.',
        ctaLabel: '랜딩 확인',
        ctaHref: '/',
    },
    {
        id: 'collect-filter',
        at: '00:25-00:55',
        title: '1차 관문: YouTube·Naver 수집 + 필터링',
        summary: '실시간 데이터 수집 후 스팸·중복·저품질 후보를 자동 제거합니다.',
    },
    {
        id: 'signal-extract',
        at: '00:55-01:10',
        title: '신호 추출: 감정·반응강도·구매의도',
        summary: 'Gemini 분석을 통해 텍스트를 마케팅 의사결정 신호로 변환합니다.',
    },
    {
        id: 'score-refine',
        at: '01:10-01:25',
        title: '2차 관문: 점수화·정제',
        summary: '행동 예측 점수 기반으로 유사 후보를 제거하고 상위 후보를 남깁니다.',
    },
    {
        id: 'result-output',
        at: '01:25-01:40',
        title: '결과: 전략 + 썸네일 + 비디오',
        summary: '바로 활용 가능한 전략, CTR 예측 썸네일, 비디오를 동시에 제공합니다.',
    },
    {
        id: 'admin-governance',
        at: '01:40-02:05',
        title: '관리자: 이력·스케줄·통제',
        summary: '실행 이력 추적과 자동 스케줄 제어로 운영 가능한 시스템을 완성합니다.',
        ctaLabel: '관리자 이동',
        ctaHref: '/admin',
    },
];

export default function PipelineSlugClient({ slug, initialData }: PipelineSlugClientProps) {
    const item = slugs[slug];
    const { role } = useAuth();
    const pipeline = usePipeline();

    const thumbStudio = useThumbnailStudio({
        selectedProduct: pipeline.selectedProduct,
        initialStyles: initialData?.styles,
        initialHookStrategies: initialData?.hookStrategies,
    });

    const videoStudio = useVideoStudio({
        selectedProduct: pipeline.selectedProduct,
        initialVideoPresets: initialData?.videoPresets,
    });

    const approval = usePipelineApproval({
        taskId: pipeline.taskId || pipeline.pipelineResult?.task_id || '',
        role: role || '',
        initialApprovalStatus: pipeline.pipelineResult?.result?.approval_status,
    });

    type SelectedOutputItem = { url?: string } & UnknownRecord;
    type SelectedOutputs = { thumbnail?: SelectedOutputItem; video?: SelectedOutputItem } & UnknownRecord;

    const taskId: TaskId = asTaskId(String(pipeline.taskId || pipeline.pipelineResult?.task_id || ''));
    const selectedOutputs = useMemo<SelectedOutputs | undefined>(() => {
        const result = pipeline.pipelineResult?.result as unknown;
        if (!isRecord(result)) return undefined;
        const so = result['selected_outputs'];
        if (!isRecord(so)) return undefined;
        return so as SelectedOutputs;
    }, [pipeline.pipelineResult]);

    const [thumbScores, setThumbScores] = useState<
        Record<string, { predictedCtr?: number; totalScore?: number; grade?: string }>
    >({});
    const [selectedThumbUrl, setSelectedThumbUrl] = useState<string | null>(null);
    const [selectedVideoUrl, setSelectedVideoUrl] = useState<string | null>(null);
    const [i2vStatus, setI2vStatus] = useState<{ loading: boolean; error: string }>({ loading: false, error: '' });
    const [distRefresh, setDistRefresh] = useState<{ loading: boolean; error: string }>({ loading: false, error: '' });

    type ThumbCandidate = { url: string; hookText?: string; style?: string };

    const thumbCandidates = useMemo<ThumbCandidate[]>(() => {
        const out: ThumbCandidate[] = [];
        const content = pipeline.pipelineResult?.result?.generated_content as unknown;
        if (!isRecord(content)) return out;

        const multi = content['multi_thumbnails'];
        if (Array.isArray(multi)) {
            for (const it of multi) {
                if (!isRecord(it)) continue;
                const url =
                    asString(it['url']) || asString(it['thumbnail_url']) || asString(it['image_url']);
                if (!url) continue;
                out.push({ url, hookText: asString(it['hook_text']), style: asString(it['style']) });
            }
        }
        const single = asString(content['thumbnail_url']);
        if (single) {
            out.unshift({ url: single, hookText: undefined, style: undefined });
        }
        // URL 중복 제거
        const seen = new Set<string>();
        return out.filter((x) => {
            if (seen.has(x.url)) return false;
            seen.add(x.url);
            return true;
        });
    }, [pipeline.pipelineResult]);

    const rankedThumbCandidates = useMemo<ThumbCandidate[]>(() => {
        // 점수 기반 정렬이 가능한 경우: 점수(CTR/score) 내림차순
        // 불가능한 경우(권한/상태 등): 파일명(=URL 마지막 경로) 기준으로 고정 정렬해 화면이 흔들리지 않게 한다.
        const toScore = (url: string): number | null => {
            const s = thumbScores[url]?.predictedCtr ?? thumbScores[url]?.totalScore;
            return typeof s === 'number' && Number.isFinite(s) ? s : null;
        };
        const toName = (url: string): string => {
            try {
                const u = new URL(url);
                const parts = (u.pathname || '').split('/').filter(Boolean);
                return decodeURIComponent(parts.at(-1) || url);
            } catch {
                const parts = (url || '').split('/').filter(Boolean);
                return parts.at(-1) || url;
            }
        };

        const items = thumbCandidates.map((c, idx) => ({ ...c, _idx: idx }));
        items.sort((a, b) => {
            const sa = toScore(a.url);
            const sb = toScore(b.url);
            const aHas = sa != null;
            const bHas = sb != null;

            if (aHas !== bHas) return aHas ? -1 : 1;
            if (aHas && bHas && sa !== sb) return (sb as number) - (sa as number);

            const na = toName(a.url);
            const nb = toName(b.url);
            const nameCmp = na.localeCompare(nb);
            if (nameCmp !== 0) return nameCmp;

            return a._idx - b._idx;
        });
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        return items.map(({ _idx: _unused, ...rest }) => rest);
    }, [thumbCandidates, thumbScores]);

    const displayThumbCandidates = useMemo<ThumbCandidate[]>(() => {
        if (rankedThumbCandidates.length) return rankedThumbCandidates;
        if (pipeline.thumbnails.length) {
            return pipeline.thumbnails.map((url) => ({ url, hookText: undefined, style: undefined }));
        }
        return DUMMY_THUMBNAILS.map((url) => ({ url, hookText: undefined, style: undefined }));
    }, [rankedThumbCandidates, pipeline.thumbnails]);

    useEffect(() => {
        const thumb = selectedOutputs?.thumbnail?.url;
        const video = selectedOutputs?.video?.url;
        setSelectedThumbUrl(typeof thumb === 'string' ? thumb : null);
        setSelectedVideoUrl(typeof video === 'string' ? video : null);
    }, [pipeline.pipelineResult?.task_id, selectedOutputs?.thumbnail?.url, selectedOutputs?.video?.url]);

    const isCtrRankingReady = useMemo(() => {
        if (!taskId) return false;
        if (thumbCandidates.length === 0) return false;
        if (pipeline.pipelineResult?.task_id !== taskId) return false;
        if (pipeline.pipelineResult?.status !== 'success') return false;
        return true;
    }, [taskId, thumbCandidates.length, pipeline.pipelineResult?.task_id, pipeline.pipelineResult?.status]);

    const activeDemoStageIndex = useMemo(() => {
        if (!pipeline.isRunning) {
            if (pipeline.pipelineResult?.status === 'success') return 4;
            return 0;
        }
        const p = pipeline.pipelineStatus?.progress?.percentage ?? 0;
        if (p < 20) return 1;
        if (p < 45) return 2;
        if (p < 70) return 3;
        return 4;
    }, [pipeline.isRunning, pipeline.pipelineResult?.status, pipeline.pipelineStatus?.progress?.percentage]);

    useEffect(() => {
        if (!isCtrRankingReady) return;

        const toNum = (v: unknown): number | undefined => {
            if (typeof v === 'number' && Number.isFinite(v)) return v;
            if (typeof v === 'string') {
                const n = Number(v);
                return Number.isFinite(n) ? n : undefined;
            }
            return undefined;
        };

        let cancelled = false;
        (async () => {
            try {
                const hooks = thumbCandidates.map((c) => c.hookText).filter(Boolean) as string[];
                const settled = await Promise.allSettled(
                    thumbCandidates.map(async (c) => {
                        const title = c.hookText || pipeline.selectedProduct || 'thumbnail';
                        const desc = c.style ? `thumbnail style: ${c.style}` : '';
                        const competitorTitles = hooks.filter((h) => h !== c.hookText).slice(0, 5);
                        const res = await predictCtr({
                            task_id: taskId,
                            title,
                            thumbnail_description: desc,
                            competitor_titles: competitorTitles,
                        });
                        const prediction = (res as { prediction?: unknown } | null)?.prediction;
                        const p = isRecord(prediction) ? prediction : {};
                        return {
                            url: c.url,
                            predictedCtr: toNum(p['predicted_ctr']),
                            totalScore: toNum(p['total_score']),
                            grade: asString(p['grade']),
                        };
                    }),
                );
                if (cancelled) return;
                const map: Record<string, { predictedCtr?: number; totalScore?: number; grade?: string }> = {};
                let non404FailureCount = 0;
                settled.forEach((r) => {
                    if (r.status === 'fulfilled') {
                        map[r.value.url] = {
                            predictedCtr: r.value.predictedCtr,
                            totalScore: r.value.totalScore,
                            grade: r.value.grade,
                        };
                        return;
                    }
                    const reason = r.reason as unknown;
                    const status =
                        typeof reason === 'object' &&
                        reason !== null &&
                        'status' in reason &&
                        typeof (reason as { status?: unknown }).status === 'number'
                            ? (reason as { status: number }).status
                            : typeof reason === 'object' &&
                                reason !== null &&
                                'message' in reason &&
                                typeof (reason as { message?: unknown }).message === 'string' &&
                                /\b404\b/.test((reason as { message: string }).message)
                              ? 404
                              : null;
                    if (status !== 404 && status !== 401 && status !== 403) non404FailureCount += 1;
                });
                setThumbScores(map);
                if (non404FailureCount > 0 && Object.keys(map).length === 0) {
                    console.warn('[pipeline-ui] failed to fetch CTR ranking; keep fallback ordering');
                }
            } catch (error: unknown) {
                if (cancelled) return;
                const status =
                    typeof error === 'object' &&
                    error !== null &&
                    'status' in error &&
                    typeof (error as { status?: unknown }).status === 'number'
                        ? (error as { status: number }).status
                        : typeof error === 'object' &&
                            error !== null &&
                            'message' in error &&
                            typeof (error as { message?: unknown }).message === 'string' &&
                            /\b404\b/.test((error as { message: string }).message)
                          ? 404
                          : null;
                if (status === 404 || status === 401 || status === 403) return;
                // 결과 미준비(404)는 조용히 폴백, 그 외 오류도 UI에는 노출하지 않고 로그만 남긴다.
                console.warn('[pipeline-ui] CTR ranking request failed', error);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [isCtrRankingReady, taskId, thumbCandidates, pipeline.selectedProduct]);

    if (!item) {
        return (
            <>
                <Navbar />
                <main className="relative min-h-screen overflow-hidden flex flex-col items-center justify-center">
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

                    <div className="relative z-10 p-8">
                        <Card className="max-w-2xl w-full text-center p-8 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
                            <h1 className="text-4xl font-bold text-slate-900">Not Found</h1>
                            <p className="mt-2 text-slate-600">The page you&apos;re looking for doesn&apos;t exist.</p>
                            <Button asChild className="mt-8 bg-slate-900 hover:bg-slate-800 text-white">
                                <Link href="/">Back Home</Link>
                            </Button>
                        </Card>
                    </div>
                </main>
            </>
        );
    }

    // Common Layout for non-studio slugs
    if (slug !== 'create' && slug !== 'thumbnail' && slug !== 'video') {
        if (slug === 'distribution') {
            const selectedThumb = selectedOutputs?.thumbnail;
            const selectedVideo = selectedOutputs?.video;
            return (
                <>
                    <Navbar />
                    <main className="relative min-h-screen overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
                        <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/[0.02] via-transparent to-purple-500/[0.02]" />
                        <div className="relative z-10 p-8 pt-24">
                            <Card className="max-w-3xl mx-auto p-8 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
                                <h1 className="font-display text-3xl font-bold text-slate-900">Distribution</h1>
                                <p className="mt-2 text-slate-600">Create에서 채택한 대표 산출물을 기준으로 다음 단계를 진행합니다.</p>
                                <div className="mt-6 grid gap-6 md:grid-cols-2">
                                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                                        <p className="text-xs font-semibold text-slate-500">선택된 썸네일</p>
                                        {selectedThumb?.url ? (
                                            // eslint-disable-next-line @next/next/no-img-element
                                            <img src={selectedThumb.url} alt="selected thumbnail" className="mt-3 w-full aspect-[9/16] object-cover rounded-lg" />
                                        ) : (
                                            <p className="mt-3 text-sm text-slate-500">선택된 썸네일이 없습니다.</p>
                                        )}
                                    </div>
                                    <div className="rounded-xl border border-slate-200 bg-white p-4">
                                        <p className="text-xs font-semibold text-slate-500">선택된 비디오</p>
                                        {selectedVideo?.url ? (
                                            <video src={selectedVideo.url} controls className="mt-3 w-full rounded-lg" />
                                        ) : (
                                            <p className="mt-3 text-sm text-slate-500">선택된 비디오가 없습니다.</p>
                                        )}
                                    </div>
                                </div>

                                <div className="mt-6 flex gap-3">
                                    <Button
                                        onClick={async () => {
                                            if (!taskId) return;
                                            setDistRefresh({ loading: true, error: '' });
                                            try {
                                                const refreshed = await fetchPipelineResult(taskId);
                                                usePipelineStore.getState().setExecutionState({ result: refreshed });
                                            } catch (e: unknown) {
                                                const msg = e instanceof Error ? e.message : '결과를 새로고침하지 못했습니다.';
                                                console.warn('[pipeline-ui] distribution refresh failed', msg);
                                                setDistRefresh({ loading: false, error: msg });
                                                return;
                                            } finally {
                                                setDistRefresh((s) => ({ ...s, loading: false }));
                                            }
                                        }}
                                        disabled={!taskId || distRefresh.loading}
                                        variant="secondary"
                                        className="bg-white text-slate-900 border border-slate-200 hover:bg-slate-50 font-semibold disabled:opacity-60"
                                    >
                                        {distRefresh.loading ? '새로고침 중...' : '결과 새로고침'}
                                    </Button>
                                    <Button asChild className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">
                                        <Link href="/pipeline/create">Create로 돌아가기</Link>
                                    </Button>
                                </div>
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

                    <div className="relative z-10 p-8 pt-24">
                        <Card className="max-w-2xl mx-auto text-center p-8 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
                            <h1 className="text-3xl font-bold text-slate-900">{item.title}</h1>
                            <p className="mt-2 text-slate-600">{item.subtitle}</p>
                            <Button asChild variant="secondary" className="mt-8 bg-slate-900 hover:bg-slate-800 text-white">
                                <Link href="/">Back Home</Link>
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
                    <div className="max-w-5xl mx-auto space-y-8">
                        <header>
                            <p className="font-display font-semibold text-indigo-600 uppercase tracking-[0.2em] text-sm">Pipeline</p>
                            <h1 className="font-display text-4xl md:text-5xl font-bold text-slate-900 mt-2">{item.title}</h1>
                            <p className="font-body text-lg text-slate-600 mt-2">{item.subtitle}</p>
                        </header>

                        {slug === 'create' && (
                            <Card className="p-6 border-slate-200/60 bg-white/90 backdrop-blur-xl shadow-lg shadow-slate-200/50">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <h2 className="text-xl font-bold text-slate-900">Nexloop 시연 플로우</h2>
                                    <div className="flex gap-2">
                                        <Button asChild variant="secondary" className="bg-white text-slate-900 border border-slate-200 hover:bg-slate-50 font-semibold">
                                            <Link href="/login">로그인</Link>
                                        </Button>
                                        <Button asChild className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">
                                            <Link href="/pipeline/distribution">결과 검증</Link>
                                        </Button>
                                    </div>
                                </div>
                                <div className="mt-5 grid gap-3 md:grid-cols-2">
                                    {DEMO_STAGES.map((stage, index) => {
                                        const isActive = index === activeDemoStageIndex;
                                        const isDone = index < activeDemoStageIndex || (!pipeline.isRunning && pipeline.pipelineResult?.status === 'success' && index <= 4);
                                        return (
                                            <div
                                                key={stage.id}
                                                className={`rounded-xl border p-4 transition ${
                                                    isActive
                                                        ? 'border-indigo-300 bg-indigo-50/70'
                                                        : isDone
                                                          ? 'border-emerald-200 bg-emerald-50/70'
                                                          : 'border-slate-200 bg-white'
                                                }`}
                                            >
                                                <p className="text-xs font-semibold tracking-wide text-slate-500">{stage.at}</p>
                                                <p className="mt-1 text-sm font-bold text-slate-900">{stage.title}</p>
                                                <p className="mt-1 text-sm text-slate-600">{stage.summary}</p>
                                                {stage.ctaHref && stage.ctaLabel ? (
                                                    <Button asChild variant="secondary" className="mt-3 bg-white text-slate-900 border border-slate-200 hover:bg-slate-50 font-semibold">
                                                        <Link href={stage.ctaHref}>{stage.ctaLabel}</Link>
                                                    </Button>
                                                ) : null}
                                            </div>
                                        );
                                    })}
                                </div>
                            </Card>
                        )}

                    {slug === 'thumbnail' && (
                        <ThumbnailStudioSection
                            {...thumbStudio}
                            products={pipeline.products}
                            selectedProduct={pipeline.selectedProduct}
                            setSelectedProduct={pipeline.setSelectedProduct}
                        />
                    )}

                    {slug === 'video' && (
                        <VideoStudioSection
                            {...videoStudio}
                            products={pipeline.products}
                            selectedProduct={pipeline.selectedProduct}
                            setSelectedProduct={pipeline.setSelectedProduct}
                        />
                    )}

                    {(slug === 'create' || (slug !== 'thumbnail' && slug !== 'video')) && (
                        <PipelineControlSection
                            {...pipeline}
                            {...approval}
                            progressPercent={pipeline.pipelineStatus?.progress?.percentage ?? 0}
                            showApprovalControls={slug !== 'create'}
                        />
                    )}

                    {/* Results section - Only show for general 'create' or pipeline pages, hide for dedicated Studios */}
                    {slug === 'create' && (
                        <div className="grid gap-6 md:grid-cols-2">
                            <Card className="p-6 md:col-span-2 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
                                <h2 className="text-xl font-bold mb-4 text-slate-900">SNS Content</h2>
                                <SnsContentSection socialPosts={pipeline.socialPosts} />
                            </Card>
	                            <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
		                                <h2 className="text-xl font-bold mb-4 text-slate-900">Thumbnails</h2>
		                                <div className="grid grid-cols-2 gap-3">
		                                    {displayThumbCandidates.map((item, i) => {
	                                            const url = item.url;
	                                            const score = thumbScores[url];
	                                            const isSelected = selectedThumbUrl === url;
	                                            return (
                                                <div key={`${url}-${i}`} className="rounded-md border border-slate-200 bg-white overflow-hidden">
                                                    {/* eslint-disable-next-line @next/next/no-img-element -- 외부/동적 URL(서명 URL 포함)이라 next/image 최적화 적용이 어렵습니다. */}
                                                    <img src={url} alt="thumb" className="w-full aspect-[9/16] object-cover" />
                                                    <div className="p-2 flex items-center justify-between gap-2">
                                                        <div className="text-[11px] text-slate-600">
                                                            {score?.predictedCtr != null ? (
                                                                <span className="font-semibold text-slate-900">
                                                                    {score.predictedCtr}% {score.grade ? `(${score.grade})` : ''}
                                                                </span>
                                                            ) : score?.totalScore != null ? (
                                                                <span className="font-semibold text-slate-900">score {score.totalScore}</span>
                                                            ) : (
                                                                <span>-</span>
                                                            )}
                                                        </div>
	                                                        <Button
	                                                            onClick={async () => {
	                                                                if (!taskId) return;
	                                                                await selectPipelineOutput({
	                                                                    task_id: taskId,
	                                                                    kind: 'thumbnail',
	                                                                    url,
	                                                                    meta: { ...(score || {}), hook_text: item.hookText, style: item.style },
	                                                                });
	                                                                // Distribution 등 다른 탭에서도 바로 보이도록 결과를 갱신한다.
	                                                                try {
	                                                                    const refreshed = await fetchPipelineResult(taskId);
	                                                                    usePipelineStore.getState().setExecutionState({ result: refreshed });
	                                                                } catch {
	                                                                    // ignore (UI는 로컬 상태로도 표시됨)
	                                                                }
	                                                                setSelectedThumbUrl(url);
	                                                            }}
	                                                            variant={isSelected ? 'secondary' : 'default'}
	                                                            className={
                                                                isSelected
                                                                    ? 'bg-slate-900 hover:bg-slate-800 text-white font-semibold'
                                                                    : 'bg-indigo-600 hover:bg-indigo-700 text-white font-semibold'
                                                            }
                                                        >
                                                            {isSelected ? '채택됨' : '채택'}
                                                        </Button>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                </div>
                                <div className="mt-4 flex flex-wrap gap-2">
                                    {selectedThumbUrl ? (
                                        <p className="text-sm text-slate-700 font-medium">
                                            선택됨: <span className="font-semibold">thumbnail</span>
                                        </p>
                                    ) : (
                                        <p className="text-sm text-slate-500">아직 채택된 썸네일이 없습니다.</p>
                                    )}
                                    <Button asChild variant="secondary" className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">
                                        <Link href="/pipeline/distribution">다음 단계로</Link>
                                    </Button>
                                </div>
	                            </Card>
	                            <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
	                                <h2 className="text-xl font-bold mb-4 text-slate-900">Videos</h2>
	                                <div className="mb-4 flex flex-wrap gap-2">
	                                    <Button
	                                        onClick={async () => {
	                                            if (!taskId) return;
	                                            if (!selectedThumbUrl) {
                                                    console.warn('[pipeline-ui] i2v skipped: no selected thumbnail');
	                                                setI2vStatus({ loading: false, error: '먼저 썸네일을 채택해 주세요.' });
	                                                return;
	                                            }
	                                            setI2vStatus({ loading: true, error: '' });
	                                            try {
	                                                const res = await generateVideoFromSelectedThumbnail(taskId);
	                                                if (res?.video_url) {
	                                                    setSelectedVideoUrl(res.video_url);
	                                                }
	                                                // 서버 쪽에서 selected_outputs.video를 자동 채택하므로, 화면 상태도 동기화한다.
	                                                try {
	                                                    const refreshed = await fetchPipelineResult(taskId);
	                                                    usePipelineStore.getState().setExecutionState({ result: refreshed });
	                                                } catch {
	                                                    // ignore
	                                                }
	                                            } catch (e: unknown) {
	                                                const msg =
	                                                    e instanceof Error
	                                                        ? e.message
	                                                        : '선택 썸네일 기반 비디오 생성에 실패했습니다.';
                                                    console.warn('[pipeline-ui] i2v generation failed', msg);
	                                                setI2vStatus({ loading: false, error: msg });
	                                                return;
                                            } finally {
                                                setI2vStatus((s) => ({ ...s, loading: false }));
                                            }
	                                        }}
	                                        disabled={!selectedThumbUrl || i2vStatus.loading}
	                                        variant="secondary"
	                                        className="bg-slate-900 hover:bg-slate-800 text-white font-semibold disabled:opacity-60"
	                                    >
	                                        {i2vStatus.loading ? '생성 중...' : '선택 썸네일로 비디오 생성'}
	                                    </Button>
	                                    <p className="text-xs text-slate-500 self-center">
	                                        선택된 썸네일을 Start Frame으로 사용해 I2V로 새 비디오를 만들고 자동 채택합니다.
	                                    </p>
	                                </div>
	                                <div className="space-y-4">
	                                    {(pipeline.videoUrls.length ? pipeline.videoUrls : DUMMY_VIDEO_URLS).map(
	                                        (url, i) => (
	                                            <div key={i} className="rounded-md border border-slate-200 bg-white overflow-hidden">
                                                <video src={url} controls className="w-full" />
                                                <div className="p-2 flex items-center justify-between">
                                                    <div className="text-[11px] text-slate-600">
                                                        {selectedVideoUrl === url ? <span className="font-semibold text-slate-900">채택됨</span> : <span>-</span>}
                                                    </div>
	                                                    <Button
	                                                        onClick={async () => {
	                                                            if (!taskId) return;
	                                                            await selectPipelineOutput({
	                                                                task_id: taskId,
	                                                                kind: 'video',
	                                                                url,
	                                                                meta: {},
	                                                            });
	                                                            try {
	                                                                const refreshed = await fetchPipelineResult(taskId);
	                                                                usePipelineStore.getState().setExecutionState({ result: refreshed });
	                                                            } catch {
	                                                                // ignore
	                                                            }
	                                                            setSelectedVideoUrl(url);
	                                                        }}
	                                                        variant={selectedVideoUrl === url ? 'secondary' : 'default'}
	                                                        className={
                                                            selectedVideoUrl === url
                                                                ? 'bg-slate-900 hover:bg-slate-800 text-white font-semibold'
                                                                : 'bg-indigo-600 hover:bg-indigo-700 text-white font-semibold'
                                                        }
                                                    >
                                                        {selectedVideoUrl === url ? '채택됨' : '채택'}
                                                    </Button>
                                                </div>
                                            </div>
                                        ),
                                    )}
                                </div>
                            </Card>
                        </div>
                    )}
                    </div>
                </div>
            </main>
        </>
    );
}
