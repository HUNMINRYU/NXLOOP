import { Suspense } from 'react';
import CTRRankerClient from './CTRRankerClient';

export const metadata = {
    title: 'CTR Ranker 승인 | NEXLOOP',
    description: 'CTR Ranker 후보를 확인하고 1개를 승인(채택)합니다.',
};

export default function CTRRankerPage() {
    return (
        <div className="container mx-auto p-6">
            <div className="mb-6">
                <h1 className="font-display text-3xl font-bold text-slate-900">CTR Ranker 승인</h1>
                <p className="font-body text-slate-600 mt-2">
                    3개 요약(top1 변경, entered/dropped, NDCG)과 Top5 후보만 보고 빠르게 1개를 채택합니다.
                </p>
            </div>
            <Suspense fallback={<div className="text-slate-600 font-medium">로딩 중...</div>}>
                <CTRRankerClient />
            </Suspense>
        </div>
    );
}

