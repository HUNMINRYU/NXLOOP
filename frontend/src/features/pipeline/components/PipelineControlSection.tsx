'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Input } from '@/components/ui';
import type { PipelineStatus } from '@/types/api';
import { Toggle } from './Toggle';

interface PipelineControlSectionProps {
  selectedProduct: string;
  products: string[];
  setSelectedProduct: (val: string) => void;
  handleRunPipeline: () => void;
  isRunning: boolean;
  youtubeCount: number;
  setYoutubeCount: (val: number) => void;
  naverCount: number;
  setNaverCount: (val: number) => void;
  includeComments: boolean;
  setIncludeComments: (val: boolean) => void;
  generateSocial: boolean;
  setGenerateSocial: (val: boolean) => void;
  generateVideo: boolean;
  setGenerateVideo: (val: boolean) => void;
  generateThumbnails: boolean;
  setGenerateThumbnails: (val: boolean) => void;
  exportToNotion: boolean;
  setExportToNotion: (val: boolean) => void;
  pipelineStatus: PipelineStatus | null;
  progressPercent: number;
  errorMessage: string;
  approvalStatus: string | null;
  canApprove: boolean;
  handleApproval: (status: 'approved' | 'rejected') => void;
  isUpdatingApproval: boolean;
  approvalMessage: string;
  /** Create 단계에서는 "승인/거부"가 채택(selected_outputs) 흐름과 중복되므로 숨길 수 있다. */
  showApprovalControls?: boolean;
}

export function PipelineControlSection({
  selectedProduct,
  products,
  setSelectedProduct,
  handleRunPipeline,
  isRunning,
  youtubeCount,
  setYoutubeCount,
  naverCount,
  setNaverCount,
  includeComments,
  setIncludeComments,
  generateSocial,
  setGenerateSocial,
  generateVideo,
  setGenerateVideo,
  generateThumbnails,
  setGenerateThumbnails,
  exportToNotion,
  setExportToNotion,
  pipelineStatus,
  progressPercent,
  errorMessage,
  approvalStatus,
  canApprove,
  handleApproval,
  isUpdatingApproval,
  approvalMessage,
  showApprovalControls = true,
}: PipelineControlSectionProps) {
  useEffect(() => {
    if (!errorMessage) return;
    console.warn('[pipeline-ui] hidden error:', errorMessage);
  }, [errorMessage]);
  const mockSteps = useMemo(
    () => [
      '기업 지식 베이스 검색 중...',
      'Nexloop Guard: 브랜드 톤앤매너 검수 중...',
      'X-Algorithm: 바이럴 점수 예측 중...',
      '데이터 수집 파이프라인 정합성 검증 중...',
      '저품질 후보 필터링 및 재랭킹 중...',
    ],
    []
  );

  const lastRealStep = useMemo(() => {
    const logs = pipelineStatus?.process_logs;
    if (Array.isArray(logs) && logs.length > 0) {
      const last = logs[logs.length - 1];
      if (typeof last === 'string' && last.trim()) return last.trim();
    }
    const msg = pipelineStatus?.progress?.message;
    return typeof msg === 'string' && msg.trim() ? msg.trim() : '';
  }, [pipelineStatus?.process_logs, pipelineStatus?.progress?.message]);

  const [displayStep, setDisplayStep] = useState<string>('');
  const [hasRealStep, setHasRealStep] = useState(false);
  const [mockLogTrail, setMockLogTrail] = useState<string[]>([]);
  const mockIndexRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const recentLogs = useMemo(() => {
    const logs = pipelineStatus?.process_logs;
    if (Array.isArray(logs) && logs.length > 0) {
      return logs.slice(-8);
    }
    return mockLogTrail.slice(-8);
  }, [mockLogTrail, pipelineStatus?.process_logs]);

  useEffect(() => {
    if (!isRunning) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      mockIndexRef.current = 0;
      // React Hook 경고(react-hooks/set-state-in-effect) 회피: effect 본문에서 동기 setState 대신 microtask로 분리합니다.
      queueMicrotask(() => {
        setHasRealStep(false);
        setDisplayStep('');
        setMockLogTrail([]);
      });
      return;
    }

    // 실시간 로그가 들어오기 전까지 1.5초 간격으로 Mock 단계 노출
    queueMicrotask(() => {
      setDisplayStep(mockSteps[0] || '');
      setMockLogTrail((prev) => {
        const first = mockSteps[0] || '';
        return first ? [...prev, first] : prev;
      });
    });
    timerRef.current = setInterval(() => {
      if (hasRealStep) return;
      mockIndexRef.current = (mockIndexRef.current + 1) % Math.max(mockSteps.length, 1);
      const next = mockSteps[mockIndexRef.current] || '';
      setDisplayStep(next);
      setMockLogTrail((prev) => {
        if (!next) return prev;
        const last = prev.length > 0 ? prev[prev.length - 1] : null;
        if (last === next) return prev;
        const appended = [...prev, next];
        return appended.length > 30 ? appended.slice(-30) : appended;
      });
    }, 1500);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [hasRealStep, isRunning, mockSteps]);

  useEffect(() => {
    if (!isRunning) return;
    if (!lastRealStep) return;

    queueMicrotask(() => {
      setHasRealStep(true);
      setDisplayStep(lastRealStep);
    });
  }, [isRunning, lastRealStep]);

  return (
    <div className="flex flex-col gap-4 soft-section p-4">
      <label className="soft-label font-bold">제품 선택</label>
      <div className="flex flex-wrap items-center gap-4">
        <select className="soft-input px-4 py-2" value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}>
          {products.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <Button onClick={handleRunPipeline} disabled={!selectedProduct || isRunning}>
          {isRunning ? '실행 중...' : '실행'}
        </Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="soft-section p-3">
          <label className="soft-label text-xs font-bold text-[var(--color-muted)]">YouTube 결과 수</label>
          <Input type="number" min={1} max={10} value={youtubeCount} onChange={(e) => setYoutubeCount(Number(e.target.value))} className="mt-2 w-full" />
        </div>
        <div className="soft-section p-3">
          <label className="soft-label text-xs font-bold text-[var(--color-muted)]">Naver 결과 수</label>
          <Input type="number" min={5} max={30} value={naverCount} onChange={(e) => setNaverCount(Number(e.target.value))} className="mt-2 w-full" />
        </div>
        <div className="grid grid-cols-2 gap-2 md:col-span-2">
          <Toggle label="댓글 분석" checked={includeComments} onChange={setIncludeComments} />
          <Toggle label="SNS 소재" checked={generateSocial} onChange={setGenerateSocial} />
          <Toggle label="비디오 생성" checked={generateVideo} onChange={setGenerateVideo} />
          <Toggle label="썸네일 생성" checked={generateThumbnails} onChange={setGenerateThumbnails} />
          <Toggle label="Notion 내보내기" checked={exportToNotion} onChange={setExportToNotion} />
        </div>
      </div>
      <div className="soft-section p-3">
        <div className="flex justify-between text-sm">
          <span>{pipelineStatus?.message || '대기 중'}</span>
          <span>{progressPercent}%</span>
        </div>
        <div className="mt-2 h-2 rounded-full bg-slate-200 overflow-hidden">
          <div className="h-full bg-blue-500 transition-all duration-300" style={{ width: `${progressPercent}%` }} />
        </div>
        {isRunning && (
          <div className="mt-4 flex items-start gap-3">
            <div className="mt-0.5 h-4 w-4 rounded-full border-2 border-slate-300 border-t-slate-900 animate-spin" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-900">거버넌스 진행 중</p>
              <p className="text-sm text-slate-600 break-words">{displayStep || '처리 단계 준비 중...'}</p>
              {recentLogs.length > 0 && (
                <div className="mt-3 rounded-lg border border-slate-200 bg-white/70 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-700">최근 단계</p>
                  <ul className="mt-2 space-y-1">
                    {recentLogs.map((line, idx) => (
                      <li key={`${idx}-${line}`} className="text-xs text-slate-600 break-words">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      {showApprovalControls && (
        <div className="soft-section p-3 space-y-3">
          <div className="flex justify-between text-sm font-medium">
            <span>승인 상태</span>
            <span className="capitalize text-[var(--color-primary)]">{approvalStatus || '대기 중'}</span>
          </div>
          {canApprove && (
            <div className="flex gap-2">
              <Button onClick={() => handleApproval('approved')} disabled={isUpdatingApproval}>
                승인
              </Button>
              <Button variant="outline" onClick={() => handleApproval('rejected')} disabled={isUpdatingApproval}>
                거부
              </Button>
            </div>
          )}
          {approvalMessage && <p className="text-xs text-[var(--color-muted)]">{approvalMessage}</p>}
        </div>
      )}
    </div>
  );
}
