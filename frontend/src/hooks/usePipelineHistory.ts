'use client';

import { useState, useEffect } from 'react';
import { fetchPipelineHistory } from '@/lib/api';
import { DUMMY_PIPELINE_TASKS } from '@/lib/dummyData';
import { PipelineResult } from '@/types/api';

export default function usePipelineHistory() {
    const isDev = process.env.NODE_ENV === 'development';
    const [tasks, setTasks] = useState<PipelineResult[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isError, setIsError] = useState(false);
    const [isDummy, setIsDummy] = useState(false);

    useEffect(() => {
        let isMounted = true;
        const isForcedDummy = typeof window !== 'undefined' && window.location.search.includes('dummy=true');

        async function fetchData() {
            try {
                setIsLoading(true);
                const response = await fetchPipelineHistory();
                if (isMounted) {
                    const fetchedTasks = response?.tasks || [];
                    if (fetchedTasks.length === 0 && isForcedDummy) {
                        throw new Error('Empty to dummy');
                    }
                    setTasks(fetchedTasks);
                    setIsError(false);
                    setIsDummy(false);
                }
            } catch (error) {
                if (isMounted) {
                    if (isDev || isForcedDummy) {
                        console.warn('API fetch failed or forced, returning dummy data.');
                        setTasks(DUMMY_PIPELINE_TASKS as unknown as PipelineResult[]);
                        setIsDummy(true);
                        setIsError(false);
                    } else {
                        console.error('Failed to fetch pipeline history:', error);
                        setIsError(true);
                    }
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        fetchData();

        return () => {
            isMounted = false;
        };
    }, [isDev]);

    return {
        tasks,
        error: isError ? '파이프라인 이력을 불러오지 못했습니다.' : '',
        isLoading,
        isDummy,
    };
}
