import { Button, Card, Input } from '@/components/ui';
import type { HookStyle, ThumbnailCompareItem, ThumbnailStyle } from '../hooks/useThumbnailStudio';

interface ThumbnailStudioSectionProps {
    selectedProduct: string;
    products: string[];
    setSelectedProduct: (val: string) => void;
    hookText: string;
    setHookText: (val: string) => void;
    hookStrategies: HookStyle[];
    styles: ThumbnailStyle[]; // Thumbnail styles
    useHookInput: boolean;
    setUseHookInput: (val: boolean) => void;
    includeTextOverlay: boolean;
    setIncludeTextOverlay: (val: boolean) => void;
    compareItems: ThumbnailCompareItem[];
    isComparing: boolean;
    thumbError: string;
    handleGenerateHook: (styleKey: string) => void;
    handleCompareStyles: () => void;
    handleGenerateSingleThumbnail: (styleKey: string) => void;
    hookLength: string;
    setHookLength: (val: string) => void;
}

export function ThumbnailStudioSection({
    selectedProduct,
    products,
    setSelectedProduct,
    hookText,
    setHookText,
    hookStrategies,
    styles,
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
}: ThumbnailStudioSectionProps) {
    return (
        <div className="space-y-10 animate-in fade-in duration-1000">
            {/* Studio Header: Strategic Input Area */}
            <Card className="p-8 bg-white border-2 border-slate-100 shadow-2xl rounded-[32px] overflow-hidden relative">
                <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -mr-16 -mt-16 blur-3xl" />

                <div className="relative z-10">
                    <header className="mb-8">
                        <h3 className="text-2xl font-bold text-slate-900 tracking-tight">Creative Workshop</h3>
                        <p className="text-sm text-slate-500 font-medium">
                            Configure your visual strategy and generate high-converting style variants.
                        </p>
                    </header>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                        <div className="space-y-3">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">
                                Focus Product
                            </label>
                            <select
                                className="w-full h-14 bg-slate-50 border-2 border-slate-100 rounded-2xl px-4 font-bold text-slate-700 focus:border-primary/50 focus:ring-0 transition-all outline-none appearance-none cursor-pointer hover:bg-slate-100"
                                value={selectedProduct}
                                onChange={(e) => setSelectedProduct(e.target.value)}
                            >
                                {products.length === 0 && <option>No Product Found</option>}
                                {products.map((p) => (
                                    <option key={p} value={p}>
                                        {p}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-3">
                            <div className="flex flex-col gap-1 w-full">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1 flex items-center justify-between">
                                    <span>Headline Strategy</span>
                                    <span className="text-[9px] text-slate-400 font-normal normal-case opacity-70">
                                        Adjust length for platform fit
                                    </span>
                                </label>
                                <div className="flex gap-2">
                                <div className="relative w-full">
                                    <Input
                                        className="w-full h-14 bg-slate-50 border-2 border-slate-100 rounded-2xl pl-4 pr-12 font-bold text-slate-700 transition-all focus:border-primary/50"
                                        value={hookText}
                                        onChange={(e) => setHookText(e.target.value)}
                                        placeholder="Enter a scroll-topping hook..."
                                    />
                                    <button
                                        type="button"
                                        onClick={() => {
                                            if (hookText) {
                                                navigator.clipboard.writeText(hookText);
                                                // Could add toast here
                                            }
                                        }}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-2 text-slate-400 hover:text-primary transition-colors active:scale-95"
                                        title="Copy to clipboard"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                                        </svg>
                                    </button>
                                </div>
                                    <div className="relative group">
                                        <select 
                                            className="h-14 bg-slate-50 border-2 border-slate-100 rounded-2xl pl-4 pr-10 font-bold text-slate-700 focus:border-primary/50 focus:ring-0 transition-all outline-none appearance-none cursor-pointer hover:bg-slate-100 text-sm min-w-[120px]"
                                            value={hookLength}
                                            onChange={(e) => setHookLength(e.target.value)}
                                        >
                                            <option value="short">Short (~20)</option>
                                            <option value="medium">Medium (~30)</option>
                                            <option value="long">Long (~45)</option>
                                        </select>
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-4 mb-8">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">
                            Copywriting Styles (Hook)
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {hookStrategies.map((s) => (
                                <button
                                    key={s.key}
                                    type="button"
                                    onClick={() => handleGenerateHook(s.key)}
                                    className="px-5 py-2.5 rounded-full bg-slate-50 border-2 border-slate-100 text-sm font-bold text-slate-600 hover:border-primary/40 hover:bg-primary/5 hover:text-primary transition-all active:scale-95 flex items-center gap-2"
                                >
                                    <span className="text-lg">{s.emoji || '✨'}</span>
                                    {s.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-4 mb-8">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">
                            Visual Styles (Single Generate)
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {styles?.length > 0 ? (
                                styles.map((s) => (
                                    <button
                                        key={s.key}
                                        type="button"
                                        onClick={() => handleGenerateSingleThumbnail(s.key)}
                                        className="px-5 py-2.5 rounded-full bg-indigo-50 border-2 border-indigo-100 text-sm font-bold text-indigo-600 hover:border-indigo-400 hover:bg-indigo-100 transition-all active:scale-95 flex items-center gap-2"
                                    >
                                        <span className="text-lg">🎨</span>
                                        {s.name}
                                    </button>
                                ))
                            ) : (
                                <p className="text-sm text-slate-400">No visual styles available.</p>
                            )}
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pt-6 border-t border-slate-50">
                        <div className="flex gap-8">
                            <label className="flex items-start gap-3 cursor-pointer group">
                                <input
                                    type="checkbox"
                                    className="w-5 h-5 mt-1 rounded-md border-2 border-slate-200 text-primary focus:ring-primary transition-all"
                                    checked={useHookInput}
                                    onChange={(e) => setUseHookInput(e.target.checked)}
                                />
                                <div className="flex flex-col">
                                    <span className="text-sm font-bold text-slate-700 group-hover:text-slate-900 transition-colors">
                                        Fixed Hook Mode
                                    </span>
                                    <span className="text-[10px] sm:text-xs text-slate-400 leading-tight">
                                        {useHookInput 
                                            ? "Applying current text to all styles" 
                                            : "Auto-generate unique text per style"}
                                    </span>
                                </div>
                            </label>

                            <label className="flex items-start gap-3 cursor-pointer group">
                                <input
                                    type="checkbox"
                                    className="w-5 h-5 mt-1 rounded-md border-2 border-slate-200 text-primary focus:ring-primary transition-all"
                                    checked={includeTextOverlay}
                                    onChange={(e) => setIncludeTextOverlay(e.target.checked)}
                                />
                                <div className="flex flex-col">
                                    <span className="text-sm font-bold text-slate-700 group-hover:text-slate-900 transition-colors">
                                        Render Text
                                    </span>
                                    <span className="text-[10px] sm:text-xs text-slate-400 leading-tight">
                                        {includeTextOverlay 
                                            ? "Burning text onto the image" 
                                            : "Generating clean background only"}
                                    </span>
                                </div>
                            </label>
                        </div>

                        <Button
                            size="lg"
                            onClick={handleCompareStyles}
                            disabled={isComparing}
                            className={`h-14 px-10 rounded-2xl font-black text-base shadow-xl transition-all ${isComparing ? 'opacity-70 bg-slate-400' : 'bg-slate-900 hover:bg-slate-800'}`}
                        >
                            {isComparing ? (
                                <div className="flex items-center gap-3">
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    Generating Analysis...
                                </div>
                            ) : (
                                'Generate 9 Style Variants'
                            )}
                        </Button>
                    </div>

                    {thumbError && (
                        <p className="mt-4 text-sm font-bold text-rose-500 animate-bounce">⚠️ {thumbError}</p>
                    )}
                </div>
            </Card>

            {/* Analysis Results: Grid Gallery Area */}
            <div className="space-y-6">
                <div className="flex items-center justify-between px-2">
                    <h4 className="text-xl font-black text-slate-900 tracking-tight">Variant Comparison Gallery</h4>
                    <span className="text-[10px] font-black uppercase tracking-widest text-[#0ca678] bg-[#0ca678]/10 px-3 py-1 rounded-full">
                        9 Styles Ready
                    </span>
                </div>

                <div className="grid gap-6 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                    {compareItems.length === 0 &&
                        Array.from({ length: 9 }).map((_, i) => (
                            <div
                                key={i}
                                className="aspect-[9/16] bg-slate-100 rounded-3xl animate-pulse flex items-center justify-center p-6 border-2 border-slate-50"
                            >
                                <div className="text-center space-y-2">
                                    <div className="w-10 h-10 bg-slate-200 rounded-full mx-auto" />
                                    <div className="w-16 h-2 bg-slate-200 rounded-full mx-auto" />
                                </div>
                            </div>
                        ))}

	                    {compareItems.map((item, idx) => (
	                        <div
	                            key={idx}
	                            className="group relative flex flex-col gap-3 animate-in fade-in zoom-in duration-500"
	                            style={{ animationDelay: `${idx * 100}ms` }}
	                        >
	                            <div className="relative aspect-[9/16] overflow-hidden rounded-[28px] border-2 border-white shadow-lg group-hover:shadow-2xl transition-all duration-500 group-hover:-translate-y-2">
	                                {/* eslint-disable-next-line @next/next/no-img-element -- 외부/동적 URL(서명 URL 포함)이라 next/image 최적화 적용이 어렵습니다. */}
	                                <img
	                                    src={item.url}
	                                    alt={item.name}
	                                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
	                                />
                                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                                <div className="absolute bottom-4 left-4 right-4 opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 transition-all duration-500">
                                    <div className="text-[10px] font-black text-white/70 uppercase tracking-widest mb-1">
                                        Preset Style
                                    </div>
                                    <div className="text-sm font-bold text-white truncate">{item.name}</div>
                                </div>
                                {/* AI Analysis Tag */}
                                <div className="absolute top-4 right-4 w-8 h-8 bg-white/20 backdrop-blur-md rounded-full border border-white/30 flex items-center justify-center text-white scale-0 group-hover:scale-100 transition-transform duration-500 font-bold text-xs">
                                    AI
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
