import { redirect } from 'next/navigation';

export default function PipelineIndexPage() {
    // /pipeline 는 과거 링크/버튼에서 종종 참조되므로,
    // 기본 진입점을 명확히 /pipeline/create 로 고정한다.
    redirect('/pipeline/create');
}

