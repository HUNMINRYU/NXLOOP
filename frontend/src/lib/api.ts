import { TaskId, GcsPath, Email, asGcsPath } from '@/types/common';
import * as ApiTypes from '@/types/api';
import { Schedule, SchedulePayload } from '@/types/schedule';
import {
    DailyReportResponse,
    InsightFailuresResponse,
    InsightMetricsResponse,
    InsightSearchResponse,
    NaverIngestResponse,
    YouTubeIngestResponse,
} from '@/types/insights';

const API_PREFIX = '/api/v1';
const FORCE_CROSS_ORIGIN_API = process.env.NEXT_PUBLIC_FORCE_CROSS_ORIGIN_API === '1';

function resolveApiBaseUrl(): string {
    // 브라우저에서는 same-origin(/api/v1/*) 호출을 기본값으로 사용해
    // cross-site 쿠키 이슈(로그인 직후 /auth/me 401 루프)를 줄인다.
    if (typeof window !== 'undefined') {
        if (FORCE_CROSS_ORIGIN_API) {
            return process.env.NEXT_PUBLIC_API_URL || '';
        }
        return '';
    }
    return process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || '';
}

type RequestOptions = Omit<RequestInit, 'body'> & { body?: string | FormData };
export class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}
type CacheStats = {
    entries?: number;
    hits?: number;
    misses?: number;
    hit_rate?: number;
    total_entries?: number;
    active_entries?: number;
    expired_entries?: number;
};
type GcsMetadataItem = {
    name?: string;
    size?: number | string;
    updated?: string;
    content_type?: string;
    signed_url?: string;
};
type PromptLogItem = {
    history_id?: string;
    product_name?: string;
    executed_at?: string;
    prompt_log?: Record<string, unknown>;
};
type DiscoveryResult = {
    title?: string;
    snippet?: string;
    url?: string;
};

function getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null;
    const parts = document.cookie.split(';').map((p) => p.trim());
    const prefix = `${name}=`;
    for (const p of parts) {
        if (p.startsWith(prefix)) return decodeURIComponent(p.slice(prefix.length));
    }
    return null;
}

const CSRF_STORAGE_KEY = 'nexloop_csrf_token';

function getStoredCsrfToken(): string | null {
    if (typeof sessionStorage === 'undefined') return null;
    try {
        return sessionStorage.getItem(CSRF_STORAGE_KEY);
    } catch {
        return null;
    }
}

function setStoredCsrfToken(token: string): void {
    if (typeof sessionStorage === 'undefined') return;
    try {
        sessionStorage.setItem(CSRF_STORAGE_KEY, token);
    } catch {
        // ignore
    }
}

function clearStoredCsrfToken(): void {
    if (typeof sessionStorage === 'undefined') return;
    try {
        sessionStorage.removeItem(CSRF_STORAGE_KEY);
    } catch {
        // ignore
    }
}

/** cross-origin에서는 백엔드 쿠키를 JS로 읽을 수 없으므로, 응답 본문으로 받은 토큰을 sessionStorage에서 사용 */
function getCsrfHeader(method?: string): Record<string, string> {
    const m = (method || 'GET').toUpperCase();
    if (m === 'GET' || m === 'HEAD' || m === 'OPTIONS') return {};
    const token = getCookie('nexloop_csrf') ?? getStoredCsrfToken();
    return token ? { 'X-CSRF-Token': token } : {};
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const apiBaseUrl = resolveApiBaseUrl();
    const crossOriginBaseUrl = process.env.NEXT_PUBLIC_API_URL || '';
    // 빌드 타임(서버 사이드)에서 백엔드 URL이 없으면 fetch 시도 차단 (빌드 무한 대기/실패 방지)
    if (typeof window === 'undefined' && !apiBaseUrl && !path.startsWith('http')) {
        console.warn(`[Build] Skipping server-side fetch for ${path} due to missing API_BASE_URL`);
        return {} as T;
    }

    const effectivePath =
        !path.startsWith('http') && path.startsWith('/') && !path.startsWith(API_PREFIX)
            ? `${API_PREFIX}${path}`
            : path;

    const requestInit: RequestInit = {
        ...options,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...getCsrfHeader(options.method),
            ...(options.headers || {}),
        } as Record<string, string>,
    };
    const requestUrl = `${apiBaseUrl}${effectivePath}`;
    let response = await fetch(requestUrl, requestInit);

    // same-origin 프록시가 아직 반영되지 않았거나 중간에 실패한 경우,
    // cross-origin 백엔드 URL로 한 번만 재시도한다.
    const shouldRetryWithCrossOrigin =
        typeof window !== 'undefined' &&
        !FORCE_CROSS_ORIGIN_API &&
        !path.startsWith('http') &&
        apiBaseUrl === '' &&
        !!crossOriginBaseUrl &&
        effectivePath.startsWith(API_PREFIX) &&
        !response.ok &&
        (response.status === 404 || response.status >= 500);
    if (shouldRetryWithCrossOrigin) {
        response = await fetch(`${crossOriginBaseUrl}${effectivePath}`, requestInit);
    }

    if (!response.ok) {
        // Only redirect to login for authenticated endpoints (not /chat for guests)
        if (response.status === 401 && typeof window !== 'undefined' && effectivePath !== `${API_PREFIX}/chat`) {
            sessionStorage.removeItem('auth-storage');
            clearStoredCsrfToken();
            try {
                const { clearStoredChat } = await import('@/lib/chatStorage');
                clearStoredChat();
            } catch {
                // ignore
            }
            if (!window.location.pathname.startsWith('/login')) {
                const currentPath = window.location.pathname + window.location.search;
                window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
            }
        }
        if (response.status === 403) throw new ApiError(403, '접근 권한이 없습니다.');
        if (response.status === 429) {
            // Rate limit exceeded
            const message = await response.text();
            throw new ApiError(response.status, message || 'Too many requests. Please try again later.');
        }
        const message = await response.text();
        throw new ApiError(response.status, message || `Request failed: ${response.status}`);
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        const data = (await response.json()) as T & { csrf_token?: string };
        if (data && typeof data === 'object' && typeof (data as { csrf_token?: string }).csrf_token === 'string') {
            setStoredCsrfToken((data as { csrf_token: string }).csrf_token);
        }
        if (effectivePath.includes('/auth/logout')) {
            clearStoredCsrfToken();
        }
        return data as T;
    }
    return (await response.text()) as unknown as T;
}

export function fetchProducts() {
    return request<{ products: string[] }>('/products/');
}

export type CTRRankerRun = {
    id: string;
    product_name: string;
    report_date: string; // ISO date
    mode: string;
    created_at?: string | null;
    metrics?: Record<string, { before: number; after: number }>;
};

export type CTRRankerCandidate = {
    id: number;
    title: string;
    video_id?: string | null;
    thumbnail_url?: string | null;
    baseline_rank?: number | null;
    baseline_score?: number | null;
    after_rank?: number | null;
    after_score?: number | null;
    proxy_score?: number | null;
};

export type CTRRankerCandidatesResponse = {
    summary: {
        top1_changed: boolean;
        entered_count: number;
        dropped_count: number;
        entered_titles: string[];
        dropped_titles: string[];
        top1_before_title?: string | null;
        top1_after_title?: string | null;
    };
    approved_candidate_id?: number | null;
    candidates: CTRRankerCandidate[];
};

export function adminImportCtrRankerRun(payload: { product_name: string; report_date: string }) {
    return request<{ run_id: string; candidate_count: number }>('/admin/ctr-ranker/runs/import', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function adminListCtrRankerRuns(productName: string) {
    return request<{ runs: CTRRankerRun[] }>(`/admin/ctr-ranker/runs?product_name=${encodeURIComponent(productName)}`);
}

export function adminListCtrRankerCandidates(runId: string) {
    return request<CTRRankerCandidatesResponse>(`/admin/ctr-ranker/runs/${encodeURIComponent(runId)}/candidates`);
}

export function adminApproveCtrRankerCandidate(runId: string, payload: { candidate_id: number; note?: string }) {
    return request<{
        approval: {
            id: number;
            run_id: string;
            candidate_id: number;
            approved_by_user_id?: number | null;
            note?: string | null;
            approved_at?: string | null;
        };
    }>(`/admin/ctr-ranker/runs/${encodeURIComponent(runId)}/approve`, {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function fetchMe() {
    return request<{
        email: Email;
        role: string;
        name: string;
        tier?: string;
        subscription_status?: string;
    }>('/auth/me');
}

export function runPipeline(payload: {
    product_name: string;
    youtube_count: number;
    naver_count: number;
    include_comments: boolean;
    generate_social: boolean;
    generate_video: boolean;
    generate_thumbnails: boolean;
    export_to_notion: boolean;
}) {
    return request<{ task_id: TaskId }>('/pipeline/run', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function fetchPipelineStatus(taskId: TaskId) {
    return request<ApiTypes.PipelineStatus>(`/pipeline/status/${taskId}`);
}

export function fetchPipelineResult(taskId: TaskId) {
    return request<ApiTypes.PipelineResult>(`/pipeline/result/${taskId}`);
}

export function updateApprovalStatus(taskId: TaskId, status: 'approved' | 'rejected') {
    return request<{ status: string }>(`/pipeline/result/${taskId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
    });
}

export function fetchPipelineHistory() {
    return request<{ tasks: Array<ApiTypes.PipelineResult> }>('/pipeline/history');
}

export function refreshUrl(gcsPath: GcsPath) {
    return request<{ url: string }>('/refresh-url', {
        method: 'POST',
        body: JSON.stringify({ gcs_path: gcsPath }),
    });
}

export function deriveGcsPathFromUrl(url: string | null | undefined): GcsPath | null {
    if (!url) return null;
    if (url.startsWith('gs://')) {
        return asGcsPath(url);
    }
    try {
        const parsed = new URL(url);
        const host = parsed.hostname;
        const pathname = parsed.pathname || '';

        // Format: https://storage.googleapis.com/<bucket>/<object>
        if (host === 'storage.googleapis.com') {
            const parts = pathname.split('/').filter(Boolean);
            if (parts.length >= 2) {
                const bucket = parts[0];
                const objectPath = parts.slice(1).join('/');
                return asGcsPath(`gs://${bucket}/${decodeURIComponent(objectPath)}`);
            }
        }

        // Format: https://<bucket>.storage.googleapis.com/<object>
        if (host.endsWith('.storage.googleapis.com')) {
            const bucket = host.replace('.storage.googleapis.com', '');
            const objectPath = pathname.replace(/^\//, '');
            if (bucket && objectPath) {
                return asGcsPath(`gs://${bucket}/${decodeURIComponent(objectPath)}`);
            }
        }

        // Format: https://storage.googleapis.com/<bucket>/o/<object>
        const oIndex = pathname.indexOf('/o/');
        if (host === 'storage.googleapis.com' && oIndex >= 0) {
            const parts = pathname.split('/').filter(Boolean);
            const bucket = parts[0];
            const objectPath = pathname.slice(oIndex + 3);
            if (bucket && objectPath) {
                return asGcsPath(`gs://${bucket}/${decodeURIComponent(objectPath)}`);
            }
        }
    } catch {
        // fall through
    }
    return null;
}

export function fetchCacheStats() {
    return request<{ stats: CacheStats }>('/admin/cache/stats');
}

export function clearCache() {
    return request<{ cleared: number }>('/admin/cache/clear', {
        method: 'POST',
    });
}

export function fetchGcsMetadata(params: { gcs_path?: GcsPath; prefix?: string; limit?: number }) {
    const search = new URLSearchParams();
    if (params.gcs_path) {
        search.set('gcs_path', params.gcs_path);
    }
    if (params.prefix) {
        search.set('prefix', params.prefix);
    }
    if (params.limit) {
        search.set('limit', String(params.limit));
    }
    const query = search.toString();
    return request<{ items: Array<GcsMetadataItem> }>(`/admin/gcs/metadata${query ? `?${query}` : ''}`);
}

export function fetchPromptLogs(limit = 20) {
    return request<{ logs: Array<PromptLogItem> }>(`/admin/prompt-logs?limit=${limit}`);
}

export function exportNotion(payload: { task_id?: TaskId; history_id?: string; parent_page_id?: string }) {
    return request<{ url: string }>('/pipeline/export/notion', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function searchDiscovery(query: string, maxResults = 5) {
    const params = new URLSearchParams();
    params.set('q', query);
    params.set('max_results', String(maxResults));
    return request<{ results: Array<DiscoveryResult> }>(`/search/discovery?${params.toString()}`);
}

export function searchInsights(params: {
    query: string;
    max_results?: number;
    doc_type?: string;
    campaign_name?: string;
    channel?: string;
    region?: string;
    period_start?: string;
    period_end?: string;
}) {
    const search = new URLSearchParams();
    search.set('q', params.query);
    if (params.max_results) search.set('max_results', String(params.max_results));
    if (params.doc_type) search.set('doc_type', params.doc_type);
    if (params.campaign_name) search.set('campaign_name', params.campaign_name);
    if (params.channel) search.set('channel', params.channel);
    if (params.region) search.set('region', params.region);
    if (params.period_start) search.set('period_start', params.period_start);
    if (params.period_end) search.set('period_end', params.period_end);
    return request<InsightSearchResponse>(`/insights/search?${search.toString()}`);
}

export function generateDailyReport(payload: {
    query: string;
    max_results?: number;
    doc_type?: string | null;
    campaign_name?: string | null;
    channel?: string | null;
    region?: string | null;
    period_start?: string | null;
    period_end?: string | null;
    title?: string | null;
}) {
    return request<DailyReportResponse>('/insights/reports/daily', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function ingestNaverInsights(payload: {
    query: string;
    max_results?: number;
    include_products?: boolean;
    include_blogs?: boolean;
    include_news?: boolean;
    campaign_name?: string | null;
    channel?: string | null;
    region?: string | null;
    period_start?: string | null;
    period_end?: string | null;
}) {
    return request<NaverIngestResponse>('/insights/external/naver', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function ingestYoutubeInsights(payload: {
    query: string;
    max_results?: number;
    include_comments?: boolean;
    campaign_name?: string | null;
    channel?: string | null;
    region?: string | null;
    period_start?: string | null;
    period_end?: string | null;
}) {
    return request<YouTubeIngestResponse>('/insights/external/youtube', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function fetchInsightMetrics(days = 7, actorRole?: string, teamId?: number) {
    const params = new URLSearchParams();
    params.set('days', String(days));
    if (actorRole) params.set('actor_role', actorRole);
    if (teamId) params.set('team_id', String(teamId));
    return request<InsightMetricsResponse>(`/insights/metrics?${params.toString()}`);
}

export function fetchInsightFailures(
    params: { days?: number; limit?: number; actor_role?: string; team_id?: number } = {},
) {
    const search = new URLSearchParams();
    if (params.days) search.set('days', String(params.days));
    if (params.limit) search.set('limit', String(params.limit));
    if (params.actor_role) search.set('actor_role', params.actor_role);
    if (params.team_id) search.set('team_id', String(params.team_id));
    const suffix = search.toString();
    return request<InsightFailuresResponse>(`/insights/failures${suffix ? `?${suffix}` : ''}`);
}

export function fetchInsightTeams() {
    return request<{ teams: ApiTypes.Team[] }>('/insights/teams');
}

export function fetchRoles() {
    return request<{ roles: ApiTypes.Role[] }>('/admin/roles');
}

export function createRole(payload: { name: string; description?: string | null }) {
    return request<ApiTypes.Role>('/admin/roles', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function fetchTeams() {
    return request<{ teams: ApiTypes.Team[] }>('/admin/teams');
}

export function createTeam(payload: { name: string }) {
    return request<ApiTypes.Team>('/admin/teams', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function fetchAuditLogs(limit = 50) {
    return request<{ logs: ApiTypes.AuditLog[] }>(`/admin/audit-logs?limit=${limit}`);
}

export function fetchThumbnailStyles() {
    return request<{ styles: ApiTypes.ThumbnailStyle[] }>('/thumbnail/styles');
}

export function generateHooks(payload: { product_name: string; style: string; count?: number; length?: string }) {
    return request<{ hooks: string[] }>('/hooks/generate', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function generateThumbnailCompare(payload: {
    product_name: string;
    hook_text?: string;
    styles?: string[] | null;
    include_text_overlay?: boolean;
    max_styles?: number;
    auto_hook_per_style?: boolean;
}) {
    return request<{
        items: Array<{ style: string; name: string; url: string; gcs_path: GcsPath; hook_text: string }>;
        hook_text: string;
    }>('/thumbnail/compare-styles', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function fetchHookStyles() {
    return request<{
        styles: ApiTypes.HookStrategy[];
    }>('/hooks/styles');
}

export function fetchVideoPresets() {
    return request<ApiTypes.VideoPresets>('/video/presets');
}

export function generateVideo(payload: {
    product_name: string;
    hook_text: string;
    duration_seconds: number;
    resolution: string;
    camera_movement?: string;
    composition?: string;
    lighting_mood?: string;
    audio_preset?: string;
    sfx?: string[];
    ambient?: string | null;
    custom_prompt?: string;
}) {
    return request<{ url: string; gcs_path?: GcsPath; prompt: string }>('/video/generate', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function extendVideo(payload: { video_uri: string; prompt: string; duration_seconds?: number }) {
    return request<{ url: string; gcs_path?: GcsPath; prompt: string }>('/video/extend', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function analyzeStrategy(taskId: TaskId) {
    return request<{ strategy: Record<string, unknown> }>('/pipeline/analysis/strategy', {
        method: 'POST',
        body: JSON.stringify({ task_id: taskId }),
    });
}

export function analyzeCommentsBasic(taskId: TaskId) {
    return request<{ analysis: Record<string, unknown> }>('/pipeline/analysis/comments/basic', {
        method: 'POST',
        body: JSON.stringify({ task_id: taskId }),
    });
}

export function analyzeCommentsDeep(taskId: TaskId) {
    return request<{ analysis: Record<string, unknown> }>('/pipeline/analysis/comments/deep', {
        method: 'POST',
        body: JSON.stringify({ task_id: taskId }),
    });
}

export function predictCtr(payload: {
    task_id: TaskId;
    title: string;
    thumbnail_description?: string;
    competitor_titles?: string[];
}) {
    return request<{ prediction: Record<string, unknown> }>('/pipeline/analysis/ctr-predict', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function selectPipelineOutput(payload: {
    task_id: TaskId;
    kind: 'thumbnail' | 'video';
    url: string;
    meta?: Record<string, unknown>;
}) {
    return request<{ selected_outputs: Record<string, unknown> }>(`/pipeline/result/${payload.task_id}/select-output`, {
        method: 'POST',
        body: JSON.stringify({
            kind: payload.kind,
            url: payload.url,
            meta: payload.meta || {},
        }),
    });
}

export function generateVideoFromSelectedThumbnail(taskId: TaskId) {
    return request<{
        video_url: string;
        gcs_path?: GcsPath;
        selected_outputs?: Record<string, unknown>;
        source?: string;
    }>(`/pipeline/result/${taskId}/generate-video-from-selected-thumbnail`, {
        method: 'POST',
    });
}

export function login(payload: { email: Email; password: string }) {
    return request<{ email: Email; role: string; name: string; tier?: string; subscription_status?: string }>(
        '/auth/login',
        {
        method: 'POST',
        body: JSON.stringify(payload),
        }
    );
}

export function signup(payload: Record<string, unknown>) {
    return request<{ email: Email; role: string; name: string }>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function createCheckoutSession(plan: 'PRO' | 'BUSINESS') {
    return request<{ url: string }>('/api/v1/stripe/create-checkout-session', {
        method: 'POST',
        body: JSON.stringify({ plan }),
    });
}

export function logout() {
    return request<{ message: string; email?: string }>('/auth/logout', {
        method: 'POST',
    });
}

/** 남은 챗봇 횟수. 비로그인/FREE는 한도·리필 시각 포함. 로그인 PRO/BUSINESS는 remaining: null(무제한). */
type ChatRemainingResponse = {
    remaining: number | null;
    resets_at?: string;
    limit_per_day?: number;
};

// chat_remaining은 여러 화면에서 동시에 호출되기 쉬워 백엔드 로그/트래픽을 유발한다.
// - in-flight dedupe: 동시에 여러 번 호출되면 같은 Promise 공유
// - TTL cache: 짧은 시간 내 반복 호출은 캐시 응답
let _chatRemainingInFlight: Promise<ChatRemainingResponse> | null = null;
let _chatRemainingCache:
    | { value: ChatRemainingResponse; expiresAtMs: number }
    | null = null;
const CHAT_REMAINING_TTL_MS = 20_000;

export function getChatRemaining(opts?: { forceRefresh?: boolean }) {
    const forceRefresh = opts?.forceRefresh === true;
    const now = Date.now();

    if (!forceRefresh && _chatRemainingCache && _chatRemainingCache.expiresAtMs > now) {
        return Promise.resolve(_chatRemainingCache.value);
    }

    if (!forceRefresh && _chatRemainingInFlight) {
        return _chatRemainingInFlight;
    }

    _chatRemainingInFlight = request<ChatRemainingResponse>('/chat/remaining', {
        method: 'GET',
    })
        .then((value) => {
            _chatRemainingCache = { value, expiresAtMs: Date.now() + CHAT_REMAINING_TTL_MS };
            return value;
        })
        .finally(() => {
            _chatRemainingInFlight = null;
        });

    return _chatRemainingInFlight;
}

export function sendChatMessage(payload: { message: string; session_id: string }) {
    return request<{
        message: string;
        session_id?: string;
        card?: Record<string, unknown>;
        sources?: Record<string, unknown>[];
    }>('/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function createLead(payload: { email: string }) {
    return request<{ status: string }>('/leads', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

// ===== 스케줄 관리 API =====

/**
 * 스케줄 목록 조회
 */
export function fetchSchedules() {
    return request<Schedule[]>('/admin/schedules');
}

/**
 * 스케줄 생성
 */
export function createSchedule(payload: SchedulePayload) {
    return request<Schedule>('/admin/schedules', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

/**
 * 스케줄 수정
 */
export function updateSchedule(id: number, payload: SchedulePayload) {
    return request<Schedule>(`/admin/schedules/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
    });
}

/**
 * 스케줄 삭제
 */
export function deleteSchedule(id: number) {
    return request<{ message: string }>(`/admin/schedules/${id}`, {
        method: 'DELETE',
    });
}

/**
 * 스케줄 활성화/비활성화
 */
export function toggleSchedule(id: number, enabled: boolean) {
    return request<{ message: string }>(`/admin/schedules/${id}/toggle`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled }),
    });
}
// ===== Studio (Custom Mode) API =====

export function createStudioDraft(payload: {
    product_name: string;
    product_desc: string;
    hook_text: string;
    style?: string;
    brand_kit?: Record<string, unknown>;
}) {
    return request<Record<string, unknown>>('/studio/draft', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

export function refineStudioPrompt(payload: {
    original_prompt: string;
    user_feedback: string;
    brand_kit?: Record<string, unknown>;
}) {
    return request<Record<string, unknown>>('/studio/refine', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}
