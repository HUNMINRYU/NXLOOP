'use client';

import { useState, useEffect } from 'react';
import { fetchSchedules, deleteSchedule, toggleSchedule } from '@/lib/api';
import { Schedule } from '@/types/schedule';
import { formatRelativeTime } from '@/lib/utils';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import ScheduleForm from './ScheduleForm';

export default function SchedulerClient() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null);

  useEffect(() => {
    loadSchedules();
  }, []);

  const loadSchedules = async () => {
    setIsLoading(true);
    try {
      const data = await fetchSchedules();
      setSchedules(data);
    } catch (error) {
      console.error('Failed to load schedules:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('이 스케줄을 삭제하시겠습니까?')) return;

    try {
      await deleteSchedule(id);
      await loadSchedules();
    } catch (error: unknown) {
      const status =
        typeof error === 'object' && error && 'status' in error && typeof (error as { status?: unknown }).status === 'number'
          ? (error as { status: number }).status
          : null;
      if (status === 404) {
        alert('스케줄을 찾을 수 없습니다. 새로고침합니다.');
        await loadSchedules();
      } else {
        alert('스케줄 삭제에 실패했습니다.');
        console.error(error);
      }
    }
  };

  const handleToggle = async (id: number, enabled: boolean) => {
    try {
      await toggleSchedule(id, enabled);
      await loadSchedules();
    } catch (error: unknown) {
      const status =
        typeof error === 'object' && error && 'status' in error && typeof (error as { status?: unknown }).status === 'number'
          ? (error as { status: number }).status
          : null;
      if (status === 409) {
        alert('스케줄이 다른 사용자에 의해 수정되었습니다. 새로고침합니다.');
        await loadSchedules();
      } else {
        alert('스케줄 상태 변경에 실패했습니다.');
        console.error(error);
      }
    }
  };

  const handleEdit = (schedule: Schedule) => {
    setEditingSchedule(schedule);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingSchedule(null);
    loadSchedules();
  };

  if (isLoading) {
    return <div className="text-center py-12 text-slate-600 font-medium">로딩 중...</div>;
  }

  return (
    <div>
      <div className="mb-6">
        <Button onClick={() => setShowForm(true)} variant="default" className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">
          + 새 스케줄 추가
        </Button>
      </div>

      {showForm && (
        <ScheduleForm
          schedule={editingSchedule}
          onClose={handleFormClose}
        />
      )}

      {schedules.length === 0 ? (
        <Card className="p-8 text-center border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
          <p className="text-slate-600 font-medium">
            생성된 스케줄이 없습니다. 새 스케줄을 추가해 보세요.
          </p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {schedules.map((schedule) => (
            <Card key={schedule.id} className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-slate-900">{schedule.name}</h3>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        schedule.enabled
                          ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/50'
                          : 'bg-slate-50 text-slate-600 ring-1 ring-slate-200/50'
                      }`}
                    >
                      {schedule.enabled ? '활성화' : '비활성화'}
                    </span>
                  </div>
                  {schedule.description && (
                    <p className="text-sm text-slate-600 font-medium mb-3">
                      {schedule.description}
                    </p>
                  )}
                  <div className="space-y-1 text-sm text-slate-700 font-medium">
                    <p>
                      <strong className="text-slate-900">제품:</strong> {schedule.product_name}
                    </p>
                    <p>
                      <strong className="text-slate-900">스케줄:</strong> {schedule.cron_expression}
                    </p>
                    <p>
                      <strong className="text-slate-900">타임존:</strong> {schedule.timezone}
                    </p>
                    {schedule.next_execution_at && schedule.enabled && (
                      <p>
                        <strong className="text-slate-900">다음 실행:</strong>{' '}
                        <span className="text-indigo-600 font-semibold">
                          {formatRelativeTime(schedule.next_execution_at)}
                        </span>
                      </p>
                    )}
                    {schedule.last_executed_at && (
                      <p>
                        <strong className="text-slate-900">마지막 실행:</strong>{' '}
                        {new Date(schedule.last_executed_at).toLocaleString('ko-KR')}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex gap-2 ml-4">
                  <Button
                    variant={schedule.enabled ? 'secondary' : 'default'}
                    onClick={() => handleToggle(schedule.id, !schedule.enabled)}
                    className={schedule.enabled ? 'bg-slate-900 hover:bg-slate-800 text-white font-semibold' : 'bg-indigo-600 hover:bg-indigo-700 text-white font-semibold'}
                  >
                    {schedule.enabled ? '비활성화' : '활성화'}
                  </Button>
                  <Button variant="outline" onClick={() => handleEdit(schedule)} className="border-slate-200 text-slate-700 hover:bg-slate-50 font-semibold">
                    수정
                  </Button>
                  <Button variant="destructive" onClick={() => handleDelete(schedule.id)} className="bg-rose-600 hover:bg-rose-700 text-white font-semibold">
                    삭제
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
