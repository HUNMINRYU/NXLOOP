import { useState, useEffect } from 'react';
import {
    generateHooks,
    generateVideo as generateVideoRequest,
    createStudioDraft,
    refineStudioPrompt,
    extendVideo,
    fetchVideoPresets,
} from '@/lib/api';
import type { VideoPresets } from '@/types/api';

interface UseVideoStudioProps {
    selectedProduct: string;
    initialVideoPresets?: VideoPresets | null;
}

export function useVideoStudio({ selectedProduct, initialVideoPresets }: UseVideoStudioProps) {
    const [videoPresets, setVideoPresets] = useState<VideoPresets | null>(initialVideoPresets ?? null);
    const [videoHookStyle, setVideoHookStyle] = useState(initialVideoPresets?.hook_styles?.[0]?.key || '');
    const [videoHookText, setVideoHookText] = useState('');
    const [videoDuration, setVideoDuration] = useState(initialVideoPresets?.durations?.[0] || 8);
    const [videoResolution, setVideoResolution] = useState(initialVideoPresets?.resolutions?.[0] || '720p');
    const [cameraMovement, setCameraMovement] = useState(initialVideoPresets?.camera_movements?.[0]?.key || '');
    const [composition, setComposition] = useState(initialVideoPresets?.compositions?.[0]?.key || '');
    const [lightingMood, setLightingMood] = useState(initialVideoPresets?.lighting_moods?.[0]?.key || '');
    const [audioPreset, setAudioPreset] = useState(initialVideoPresets?.audio_presets?.[0]?.key || '');
    const [sfxInput, setSfxInput] = useState('');
    const [ambientInput, setAmbientInput] = useState('');
    const [generatedVideoUrl, setGeneratedVideoUrl] = useState('');
    const [videoPrompt, setVideoPrompt] = useState('');
    const [videoError, setVideoError] = useState('');
    const [isVideoGenerating, setIsVideoGenerating] = useState(false);

    // Extension State
    const [generatedVideoGcsPath, setGeneratedVideoGcsPath] = useState('');
    const [isExtending, setIsExtending] = useState(false);
    const [extensionDuration, setExtensionDuration] = useState(4);

    // Studio (Custom) Mode States
    const [isStudioMode, setIsStudioMode] = useState(false);
    const [studioFeedback, setStudioFeedback] = useState('');
    const [isStudioLoading, setIsStudioLoading] = useState(false);

    // 클라이언트 사이드 데이터 페칭
    useEffect(() => {
        if (!videoPresets) {
            const loadPresets = async () => {
                try {
                    const presets = await fetchVideoPresets();
                    setVideoPresets(presets);
                    // 초기값 설정
                    if (presets) {
                        setVideoHookStyle(presets.hook_styles?.[0]?.key || '');
                        setVideoDuration(presets.durations?.[0] || 8);
                        setVideoResolution(presets.resolutions?.[0] || '720p');
                        setCameraMovement(presets.camera_movements?.[0]?.key || '');
                        setComposition(presets.compositions?.[0]?.key || '');
                        setLightingMood(presets.lighting_moods?.[0]?.key || '');
                        setAudioPreset(presets.audio_presets?.[0]?.key || '');
                    }
                } catch (err) {
                    console.error('Failed to load video presets:', err);
                }
            };
            loadPresets();
        }
    }, [videoPresets]);

    const handleGenerateVideoHook = async () => {
        if (!selectedProduct || !videoHookStyle) return;
        setVideoError('');
        try {
            const response = await generateHooks({ product_name: selectedProduct, style: videoHookStyle, count: 1 });
            if (response?.hooks?.length) {
                setVideoHookText(response.hooks[0] ?? '');
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '';
            setVideoError(message || '훅 생성에 실패했습니다.');
        }
    };

    const handleCreateDraft = async () => {
        if (!selectedProduct || !videoHookText) return;
        setIsStudioLoading(true);
        try {
            const result = await createStudioDraft({
                product_name: selectedProduct,
                product_desc: 'Visual Studio Product Description',
                hook_text: videoHookText,
                style: 'Cinematic',
            });
            const prompt = typeof result.veo_prompt === 'string' ? result.veo_prompt : '';
            setVideoPrompt(prompt);
            setIsStudioMode(true);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '';
            setVideoError(message || '초안 생성에 실패했습니다.');
        } finally {
            setIsStudioLoading(false);
        }
    };

    const handleRefinePrompt = async () => {
        if (!videoPrompt || !studioFeedback) return;
        setIsStudioLoading(true);
        try {
            const result = await refineStudioPrompt({
                original_prompt: videoPrompt,
                user_feedback: studioFeedback,
            });
            const prompt = typeof result.refined_prompt === 'string' ? result.refined_prompt : '';
            setVideoPrompt(prompt);
            setStudioFeedback('');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '';
            setVideoError(message || '프롬프트 수정에 실패했습니다.');
        } finally {
            setIsStudioLoading(false);
        }
    };

    const handleGenerateVideo = async () => {
        if (!selectedProduct) {
            setVideoError('제품을 선택해주세요.');
            return;
        }
        if (!videoHookText.trim() && !videoPrompt) {
            setVideoError('후킹 문구 또는 프롬프트를 입력해주세요.');
            return;
        }
        setIsVideoGenerating(true);
        setVideoError('');
        setGeneratedVideoUrl('');
        try {
            const response = await generateVideoRequest({
                product_name: selectedProduct,
                hook_text: videoHookText || 'Manual Studio Production',
                duration_seconds: videoDuration,
                resolution: videoResolution,
                camera_movement: cameraMovement,
                composition,
                lighting_mood: lightingMood,
                audio_preset: audioPreset,
                sfx: sfxInput
                    ? sfxInput
                          .split(',')
                          .map((v) => v.trim())
                          .filter(Boolean)
                    : [],
                ambient: ambientInput || null,
                custom_prompt: isStudioMode && videoPrompt ? videoPrompt : undefined,
            });
            setGeneratedVideoUrl(response.url);
            setGeneratedVideoGcsPath(response.gcs_path || '');
            setVideoPrompt(response.prompt);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '';
            setVideoError(message || '비디오 생성에 실패했습니다.');
        } finally {
            setIsVideoGenerating(false);
        }
    };

    const handleExtendVideo = async () => {
        if (!generatedVideoGcsPath) return;
        setIsExtending(true);
        setVideoError('');
        try {
            const response = await extendVideo({
                video_uri: generatedVideoGcsPath,
                prompt: videoPrompt,
                duration_seconds: extensionDuration,
            });
            setGeneratedVideoUrl(response.url);
            setGeneratedVideoGcsPath(response.gcs_path || '');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '';
            setVideoError(message || '비디오 연장에 실패했습니다.');
        } finally {
            setIsExtending(false);
        }
    };

    return {
        videoPresets,
        videoHookStyle,
        setVideoHookStyle,
        videoHookText,
        setVideoHookText,
        videoDuration,
        setVideoDuration,
        videoResolution,
        setVideoResolution,
        cameraMovement,
        setCameraMovement,
        composition,
        setComposition,
        lightingMood,
        setLightingMood,
        audioPreset,
        setAudioPreset,
        sfxInput,
        setSfxInput,
        ambientInput,
        setAmbientInput,
        generatedVideoUrl,
        videoPrompt,
        setVideoPrompt,
        videoError,
        isVideoGenerating,
        isStudioMode,
        setIsStudioMode,
        studioFeedback,
        setStudioFeedback,
        isStudioLoading,
        handleGenerateVideoHook,
        handleGenerateVideo,
        handleCreateDraft,
        handleRefinePrompt,
        handleExtendVideo,
        isExtending,
        generatedVideoGcsPath,
        extensionDuration,
        setExtensionDuration,
    };
}
