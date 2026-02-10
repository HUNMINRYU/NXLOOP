import { Suspense } from 'react';
import SchedulerClient from './SchedulerClient';

export const metadata = {
    title: '파이프라인 스케줄러 관리 | NEXLOOP',
    description: 'GCP Cloud Scheduler를 통한 파이프라인 자동 실행 관리',
};

export default function SchedulerPage() {
    return (
        <div className="container mx-auto p-6">
            <div className="mb-6">
                <h1 className="font-display text-3xl font-bold text-slate-900">파이프라인 스케줄러 관리</h1>
                <p className="font-body text-slate-600 mt-2">파이프라인의 자동 실행 일정을 관리합니다.</p>
            </div>
            <Suspense fallback={<div className="text-slate-600 font-medium">로딩 중...</div>}>
                <SchedulerClient />
            </Suspense>
        </div>
    );
}
