import { Button, Card } from '@/components/ui';
import Link from 'next/link';

export default function AdminPage() {
    return (
        <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
            <p className="font-display font-semibold text-indigo-600 uppercase tracking-[0.2em] text-sm mb-1">Admin</p>
            <h1 className="font-display text-2xl font-bold text-slate-900 mb-2">관리자 대시보드</h1>
            <p className="font-body text-base text-slate-600 mb-4">
                시스템 상태, 프롬프트 로그, 저장소 메타데이터를 관리합니다.
            </p>
            <div className="flex flex-wrap gap-3">
                <Link href="/search/discovery">
                    <Button variant="secondary" className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">Discovery 검색 UI</Button>
                </Link>
                <Link href="/admin/roles">
                    <Button variant="secondary" className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">Role / Team 관리</Button>
                </Link>
                <Link href="/admin/audit-logs">
                    <Button variant="default" className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">감사 로그</Button>
                </Link>
                <Link href="/admin/scheduler">
                    <Button variant="default" className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">스케줄러 관리</Button>
                </Link>
            </div>
        </Card>
    );
}

