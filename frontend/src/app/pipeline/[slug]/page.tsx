import PipelineSlugClient from '@/components/PipelineSlugClient';
import { pipelineSlugs } from '@/lib/slugs';
import { Metadata } from 'next';

const slugsInfo: Record<string, { title: string }> = {
    'data-source': { title: 'Data Source' },
    'ai-prompt': { title: 'AI Prompt' },
    create: { title: 'Create' },
    distribution: { title: 'Distribution' },
    thumbnail: { title: 'Thumbnail Studio' },
    video: { title: 'Video Studio' },
};

export function generateStaticParams() {
    return pipelineSlugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
    const { slug } = await params;
    const title = slugsInfo[slug]?.title || 'Pipeline';
    return {
        title: `${title} | NEXLOOP Pipeline`,
        description: `${title} pipeline step for AI content automation.`,
    };
}

export default async function PipelineSlugPage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params;

    // 임포트를 제거하여 빌드 타임 의존성 문제를 원천 차단
    return <PipelineSlugClient slug={slug} />;
}
