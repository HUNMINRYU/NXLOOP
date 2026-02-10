import { useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchPipelineResult,
  fetchPipelineStatus,
  fetchProducts,
  runPipeline,
} from '@/lib/api';
import { DUMMY_PRODUCTS } from '@/lib/dummyData';
import { PipelineStatus } from '@/types/api';
import { GeneratedThumbnail } from '@/types/domain';
import { TaskId } from '@/types/common';
import { usePipelineStore } from '@/store/usePipelineStore';

export default function usePipeline() {
  const isDev = process.env.NODE_ENV === 'development';
  const hasFetchedResultRef = useRef(false);
  const didInitProductsRef = useRef(false);
  
  // Zustand Store 구독
	  const {
	    selectedProduct, youtubeCount, naverCount, includeComments,
	    generateSocial, generateVideo, generateThumbnails, exportToNotion,
	    taskId, isRunning, status: pipelineStatus, result: pipelineResult, error: errorMessage,
	    setConfiguration, setExecutionState
	  } = usePipelineStore();

  // 제품 목록 페칭 (이 부분은 React Query로 대체 가능하지만, 현재 구조 유지하되 products 로컬 상태는 훅 내부에 둠)
  // TODO: 추후 products도 React Query로 전환 권장
	  const [products, setProducts] = useState<string[]>([]); // React import 필요
	  
	  useEffect(() => {
	    if (didInitProductsRef.current) return;
	    didInitProductsRef.current = true;

	    let isMounted = true;
	    fetchProducts()
	      .then((data) => {
	        if (!isMounted) return;
	        const names = data?.products || [];
	        if (names.length > 0) {
	          setProducts(names);
	          // 초기 선택값이 없을 때만 설정
	          if (!usePipelineStore.getState().selectedProduct && names.length > 0) {
	            setConfiguration({ selectedProduct: names[0] });
	          }
	          return;
	        }
	        if (isDev) {
	          setProducts(DUMMY_PRODUCTS);
	          if (!usePipelineStore.getState().selectedProduct && DUMMY_PRODUCTS.length > 0) {
	            setConfiguration({ selectedProduct: DUMMY_PRODUCTS[0] });
	          }
	          return;
	        }
        setProducts([]);
        setConfiguration({ selectedProduct: '' });
        setExecutionState({ error: '제품 목록을 불러오지 못했습니다.' });
      })
	      .catch(() => {
	        if (!isMounted) return;
	        if (isDev) {
	          setProducts(DUMMY_PRODUCTS);
	          if (!usePipelineStore.getState().selectedProduct && DUMMY_PRODUCTS.length > 0) {
	             setConfiguration({ selectedProduct: DUMMY_PRODUCTS[0] });
	          }
	          return;
	        }
	        setProducts([]);
	        setConfiguration({ selectedProduct: '' });
	        setExecutionState({ error: '제품 목록을 불러오지 못했습니다.' });
	      });

	    return () => {
	      isMounted = false;
	    };
	  }, [isDev, setConfiguration, setExecutionState]); // 마운트 시 1회만 실행되도록 ref로 가드

  // Polling 및 EventSource 로직
  useEffect(() => {
    if (!taskId) return;

    let isActive = true;
    let pollIntervalId: ReturnType<typeof setInterval> | undefined;
    let reconnectTimeoutId: ReturnType<typeof setTimeout> | undefined;
    let sseWatchdogId: ReturnType<typeof setInterval> | undefined;
    let eventSource: EventSource | null = null;

    // SSE 상태 플래그: SSE가 정상으로 판단되면 polling은 즉시 중단한다.
    let isSseHealthy = false;
    let lastSseMessageAtMs = 0;
    let reconnectDelayMs = 1000;

    const fetchResultOnce = async () => {
      if (hasFetchedResultRef.current) return;
      try {
        const result = await fetchPipelineResult(taskId as TaskId);
        if (isActive) {
          setExecutionState({ result });
        }
        hasFetchedResultRef.current = true;
      } catch (err: unknown) {
        if (isActive) {
          const message = err instanceof Error ? err.message : '';
          setExecutionState({ error: message || '결과를 불러오지 못했습니다.' });
        }
      }
    };

    const handleFinished = async (finalStatus: PipelineStatus) => {
      setExecutionState({ status: finalStatus, isRunning: false });
      await fetchResultOnce();
    };

    const stopPolling = () => {
      if (pollIntervalId) {
        clearInterval(pollIntervalId);
        pollIntervalId = undefined;
      }
    };

    const stopReconnectTimer = () => {
      if (reconnectTimeoutId) {
        clearTimeout(reconnectTimeoutId);
        reconnectTimeoutId = undefined;
      }
    };

    const stopSseWatchdog = () => {
      if (sseWatchdogId) {
        clearInterval(sseWatchdogId);
        sseWatchdogId = undefined;
      }
    };

    const closeEventSource = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      isSseHealthy = false;
      lastSseMessageAtMs = 0;
    };

    const markSseHealthy = () => {
      isSseHealthy = true;
      reconnectDelayMs = 1000;
      stopPolling();
      stopReconnectTimer();
    };

    const startSseWatchdogIfNeeded = () => {
      if (sseWatchdogId) return;
      // SSE 연결이 열려도 메시지가 안 오면(half-open/서버 이슈) polling까지 같이 멈춰 보일 수 있다.
      // 마지막 메시지 기준으로 watchdog을 두고, 일정 시간 동안 메시지가 없으면 polling 폴백 + 재연결한다.
      sseWatchdogId = setInterval(() => {
        if (!isActive) return;
        if (!isSseHealthy) return;
        if (!lastSseMessageAtMs) return;
        if (Date.now() - lastSseMessageAtMs < 15_000) return;

        closeEventSource();
        startPolling();
        scheduleReconnect();
      }, 5000);
    };

    const poll = async () => {
      // SSE가 정상이라면 polling을 하지 않는다 (스팸 방지 + 단일 소스 유지).
      if (isSseHealthy) return;
      try {
        const currentStatus = await fetchPipelineStatus(taskId as TaskId);
        if (!isActive) return;
        setExecutionState({ status: currentStatus });
        
        const finished = currentStatus?.status === 'success' || currentStatus?.status === 'failed';
        if (finished) {
          stopPolling();
          stopReconnectTimer();
          closeEventSource();
          await handleFinished(currentStatus);
        }
      } catch (err: unknown) {
        if (isActive) {
          const message = err instanceof Error ? err.message : '';
          setExecutionState({ error: message || '상태를 불러오지 못했습니다.' });
        }
      }
    };

    const startPolling = () => {
      if (pollIntervalId) return;
      poll();
      pollIntervalId = setInterval(poll, 3000);
    };

    const scheduleReconnect = () => {
      if (!isActive) return;
      if (typeof EventSource === 'undefined') return;
      if (reconnectTimeoutId) return;

      reconnectTimeoutId = setTimeout(() => {
        reconnectTimeoutId = undefined;
        connectSse();
      }, reconnectDelayMs);

      reconnectDelayMs = Math.min(reconnectDelayMs * 2, 30_000);
    };

    const connectSse = () => {
      if (!isActive) return;
      if (typeof EventSource === 'undefined') return;

      // 기존 연결 정리 후 재연결
      closeEventSource();

      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
        eventSource = new EventSource(`${baseUrl}/api/v1/pipeline/status-stream/${taskId}`);

        eventSource.onmessage = async (event) => {
          if (!isActive) return;
          try {
            const streamStatus = JSON.parse(event.data) as PipelineStatus;
            lastSseMessageAtMs = Date.now();
            markSseHealthy();
            startSseWatchdogIfNeeded();

            const finished = streamStatus?.status === 'success' || streamStatus?.status === 'failed';

            if (finished) {
              stopPolling();
              stopReconnectTimer();
              stopSseWatchdog();
              closeEventSource();
              await handleFinished(streamStatus);
            } else {
              setExecutionState({ status: streamStatus });
            }
          } catch {
            // payload가 예상과 다르면 polling 폴백 + 재연결로 복구한다.
            closeEventSource();
            startPolling();
            scheduleReconnect();
          }
        };

        eventSource.onerror = () => {
          if (!isActive) return;

          // SSE가 깨지면 즉시 polling으로 폴백하고, 백오프로 SSE 재연결을 시도한다.
          closeEventSource();
          startPolling();
          scheduleReconnect();
        };
      } catch {
        closeEventSource();
        startPolling();
        scheduleReconnect();
      }
    };

    if (typeof EventSource !== 'undefined') {
      connectSse();
    } else {
      startPolling();
    }

    return () => {
      isActive = false;
      stopReconnectTimer();
      stopSseWatchdog();
      closeEventSource();
      stopPolling();
    };
  }, [taskId, setExecutionState]);

  const handleRunPipeline = async () => {
    if (!selectedProduct || isRunning) return;
    
    setExecutionState({ 
        taskId: '',
        error: '', 
        result: null, 
        status: null, 
        isRunning: true 
    });
    hasFetchedResultRef.current = false;

    try {
      const response = await runPipeline({
        product_name: selectedProduct,
        youtube_count: youtubeCount,
        naver_count: naverCount,
        include_comments: includeComments,
        generate_social: generateSocial,
        generate_video: generateVideo,
        generate_thumbnails: generateThumbnails,
        export_to_notion: exportToNotion,
      });
      
      const newTaskId = response.task_id;
      setExecutionState({ 
          taskId: newTaskId,
          status: {
            status: 'triggered',
            message: '파이프라인을 시작했습니다.',
            progress: { percentage: 0, message: '대기 중', step: 'initialized' },
            task_id: newTaskId,
          }
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '';
      setExecutionState({ 
          isRunning: false, 
          error: message || '파이프라인 실행에 실패했습니다.' 
      });
    }
  };



// ...

  // Memoized Derived Data
  const thumbnails = useMemo(() => {
    const items: string[] = [];
    const generatedContent = pipelineResult?.result?.generated_content || null;
    if (generatedContent?.thumbnail_url) items.push(generatedContent.thumbnail_url);
    if (Array.isArray(generatedContent?.multi_thumbnails)) {
      generatedContent.multi_thumbnails.forEach((item: GeneratedThumbnail) => {
        if (!item) return;
        const url = item.url || item.thumbnail_url || item.image_url;
        if (url) items.push(url);
      });
    }
    return items;
  }, [pipelineResult]);

  const videoUrls = useMemo(() => {
    const items: string[] = [];
    const generatedContent = pipelineResult?.result?.generated_content || null;
    if (generatedContent?.video_url) items.push(generatedContent.video_url);
    return items;
  }, [pipelineResult]);

  const analyticsData = useMemo(() => {
    const collected = pipelineResult?.result?.collected_data || {};
    const strategy = pipelineResult?.result?.strategy;
    
    // Type guards/checks are now implicitly handled by interfaces, but fallback is safe
    const youtubeItems = collected.youtube_data?.items;
    const naverItems = collected.naver_data?.items;
    
    const visibility = Array.isArray(youtubeItems)
      ? youtubeItems.length
      : Array.isArray(naverItems)
        ? naverItems.length
        : 0;

    const ctrPrecision = strategy?.ctr ?? 0;
    const sentiment = strategy?.sentiment || strategy?.summary || 'N/A';
    return { visibility, ctrPrecision, sentiment };
  }, [pipelineResult]);

  const socialPosts = useMemo(() => {
    return pipelineResult?.result?.strategy?.social_posts || null;
  }, [pipelineResult]);

  return {
    products,
    selectedProduct,
    setSelectedProduct: (val: string) => setConfiguration({ selectedProduct: val }),
    pipelineStatus,
    pipelineResult,
    taskId,
    isRunning,
    errorMessage,
    youtubeCount,
    naverCount,
    includeComments,
    generateSocial,
    generateVideo,
    generateThumbnails,
    exportToNotion,
    setYoutubeCount: (val: number) => setConfiguration({ youtubeCount: val }),
    setNaverCount: (val: number) => setConfiguration({ naverCount: val }),
    setIncludeComments: (val: boolean) => setConfiguration({ includeComments: val }),
    setGenerateSocial: (val: boolean) => setConfiguration({ generateSocial: val }),
    setGenerateVideo: (val: boolean) => setConfiguration({ generateVideo: val }),
    setGenerateThumbnails: (val: boolean) => setConfiguration({ generateThumbnails: val }),
    setExportToNotion: (val: boolean) => setConfiguration({ exportToNotion: val }),
    handleRunPipeline,
    thumbnails,
    videoUrls,
    analyticsData,
    socialPosts,
  };
}
