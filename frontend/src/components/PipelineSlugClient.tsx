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
                            <p className="mt-2 text-slate-600">The page you're looking for doesn't exist.</p>
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
                                    {(pipeline.thumbnails.length ? pipeline.thumbnails : DUMMY_THUMBNAILS).map(
                                        (url, i) => (
                                            <img
                                                key={i}
                                                src={url}
                                                alt="thumb"
                                                className="w-full aspect-[9/16] object-cover rounded-md"
                                            />
                                        ),
                                    )}
                                </div>
                            </Card>
                            <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
                                <h2 className="text-xl font-bold mb-4 text-slate-900">Videos</h2>
                                <div className="space-y-4">
                                    {(pipeline.videoUrls.length ? pipeline.videoUrls : DUMMY_VIDEO_URLS).map(
                                        (url, i) => (
                                            <video key={i} src={url} controls className="w-full rounded-md" />
                                        ),
                                    )}
                                </div>
                            </Card>
                        </div>
                    )}
                </div>
            </main>
        </>
    );
}
