import { useState, useEffect } from 'react';
import { generateHooks, generateThumbnailCompare, fetchThumbnailStyles, fetchHookStyles } from '@/lib/api';

export interface HookStyle {
    key: string;
    name: string;
    emoji?: string | null;
}

export interface ThumbnailStyle {
    key: string;
    name: string;
}

export interface ThumbnailCompareItem {
    url: string;
    name: string;
    [key: string]: unknown;
}

interface UseThumbnailStudioProps {
    selectedProduct: string;
    initialStyles?: ThumbnailStyle[];
    initialHookStrategies?: HookStyle[];
}

export function useThumbnailStudio({
    selectedProduct,
    initialStyles = [],
    initialHookStrategies = [],
}: UseThumbnailStudioProps) {
    const [styles, setStyles] = useState<ThumbnailStyle[]>(initialStyles);
    const [hookStrategies, setHookStrategies] = useState<HookStyle[]>(initialHookStrategies);
    const [hookText, setHookText] = useState('');
    const [useHookInput, setUseHookInput] = useState(true);
    const [includeTextOverlay, setIncludeTextOverlay] = useState(true);
    const [compareItems, setCompareItems] = useState<ThumbnailCompareItem[]>([]);
    const [isComparing, setIsComparing] = useState(false);
    const [thumbError, setThumbError] = useState('');
    const [hookLength, setHookLength] = useState('long');

    // 클라이언트 사이드 데이터 페칭
    useEffect(() => {
        if (styles.length === 0 || hookStrategies.length === 0) {
            const loadInitialData = async () => {
                try {
                    const [stylesRes, hooksRes] = await Promise.all([fetchThumbnailStyles(), fetchHookStyles()]);
                    setStyles(stylesRes.styles || []);
                    setHookStrategies(hooksRes.styles || []);
                } catch (err) {
                    console.error('Failed to load thumbnail studio meta data:', err);
                }
            };
            loadInitialData();
        }
    }, [hookStrategies.length, styles.length]);

    useEffect(() => {
        setHookText('');
    }, [selectedProduct]);

    const handleGenerateHook = async (styleKey: string) => {
        if (!selectedProduct) return;
        setThumbError('');
        try {
            const response = await generateHooks({
                product_name: selectedProduct,
                style: styleKey,
                count: 1,
                length: hookLength,
            });
            if (response?.hooks?.length) {
                setHookText(response.hooks[0] ?? '');
            }
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : '';
            setThumbError(errorMessage || '훅 생성에 실패했습니다.');
        }
    };

    const handleCompareStyles = async () => {
        if (!selectedProduct) {
            setThumbError('제품을 선택해주세요.');
            return;
        }
        setIsComparing(true);
        setThumbError('');
        setCompareItems([]);
        try {
            const response = await generateThumbnailCompare({
                product_name: selectedProduct,
                hook_text: hookText || undefined,
                include_text_overlay: includeTextOverlay,
                max_styles: 9,
                auto_hook_per_style: !useHookInput,
            });
            const items = (response.items || []) as ThumbnailCompareItem[];
            setCompareItems(items);
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : '';
            setThumbError(errorMessage || '스타일 비교 생성에 실패했습니다.');
        } finally {
            setIsComparing(false);
        }
    };

    const handleGenerateSingleThumbnail = async (styleKey: string) => {
        if (!selectedProduct) {
            setThumbError('제품을 선택해주세요.');
            return;
        }
        setThumbError('');
        try {
            const response = await generateThumbnailCompare({
                product_name: selectedProduct,
                hook_text: hookText || undefined,
                include_text_overlay: includeTextOverlay,
                styles: [styleKey],
                auto_hook_per_style: false,
            });
            const items = (response.items || []) as ThumbnailCompareItem[];
            const firstItem = items[0];
            if (!firstItem) {
                return;
            }
            setCompareItems((prev) => [firstItem, ...prev]);
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : '';
            setThumbError(errorMessage || '썸네일 생성에 실패했습니다.');
        }
    };

    return {
        styles,
        hookStrategies,
        hookText,
        setHookText,
        useHookInput,
        setUseHookInput,
        includeTextOverlay,
        setIncludeTextOverlay,
        compareItems,
        isComparing,
        thumbError,
        handleGenerateHook,
        handleCompareStyles,
        handleGenerateSingleThumbnail,
        hookLength,
        setHookLength,
    };
}
