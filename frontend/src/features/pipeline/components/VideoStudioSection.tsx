import { Button, Card, Input } from '@/components/ui';
import type { VideoPresets } from '@/types/api';

interface VideoStudioSectionProps {
  selectedProduct: string;
  products: string[];
  setSelectedProduct: (val: string) => void;
  videoPresets: VideoPresets | null;
  videoHookStyle: string;
  setVideoHookStyle: (val: string) => void;
  videoHookText: string;
  setVideoHookText: (val: string) => void;
  videoDuration: number;
  setVideoDuration: (val: number) => void;
  videoResolution: string;
  setVideoResolution: (val: string) => void;
  cameraMovement: string;
  setCameraMovement: (val: string) => void;
  composition: string;
  setComposition: (val: string) => void;
  lightingMood: string;
  setLightingMood: (val: string) => void;
  audioPreset: string;
  setAudioPreset: (val: string) => void;
  sfxInput: string;
  setSfxInput: (val: string) => void;
  ambientInput: string;
  setAmbientInput: (val: string) => void;
  generatedVideoUrl: string;
  videoPrompt: string;
  videoError: string;
  isVideoGenerating: boolean;
  handleGenerateVideoHook: () => void;
  handleGenerateVideo: () => void;
  // Custom Studio Mode Props
  isStudioMode: boolean;
  setIsStudioMode: (val: boolean) => void;
  handleCreateDraft: () => void;
  handleRefinePrompt: () => void;
  studioFeedback: string;
  setStudioFeedback: (val: string) => void;
  isStudioLoading: boolean;
  setVideoPrompt: (val: string) => void;
  // Extension
  handleExtendVideo: () => void;
  isExtending: boolean;
  extensionDuration: number;
  setExtensionDuration: (val: number) => void;
}

export function VideoStudioSection({
  selectedProduct,
  products,
  setSelectedProduct,
  videoPresets,
  videoHookStyle,
  setVideoHookStyle,
  videoHookText,
  setVideoHookText,
  videoDuration,
  setVideoDuration,
  videoResolution,
  setVideoResolution,
  generatedVideoUrl,
  videoPrompt,
  videoError,
  isVideoGenerating,
  handleGenerateVideoHook,
  handleGenerateVideo,
  isStudioMode,
  setIsStudioMode,
  handleCreateDraft,
  handleRefinePrompt,
  studioFeedback,
  setStudioFeedback,
  isStudioLoading,
  setVideoPrompt,
  handleExtendVideo,
  isExtending,
  extensionDuration,
  setExtensionDuration,
}: VideoStudioSectionProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-gray-100 mb-4">
        <h3 className="font-bold text-lg">Video Studio</h3>
        <div className="flex items-center gap-2">
           <label className="text-sm text-[var(--color-muted)] font-medium">Custom Mode</label>
           <input 
             type="checkbox" 
             checked={isStudioMode} 
             onChange={(e) => setIsStudioMode(e.target.checked)}
             className="toggle-checkbox"
           />
        </div>
      </div>

      <div className="soft-section p-4 space-y-4">
        <label className="soft-label font-bold">제품 선택</label>
        <select
          className="soft-input w-full px-4 py-2"
          value={selectedProduct}
          onChange={(e) => setSelectedProduct(e.target.value)}
        >
          {products.length === 0 && <option>제품 없음</option>}
          {products.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        
        <div className="grid gap-4 md:grid-cols-2">
          {!isStudioMode ? (
            /* Standard Preset Mode */
             <>
              <div>
                <label className="soft-label text-xs font-bold text-[var(--color-muted)]">후킹 스타일</label>
                <select className="soft-input mt-2 w-full" value={videoHookStyle} onChange={(e) => setVideoHookStyle(e.target.value)}>
                  {(videoPresets?.hook_styles || []).map((s) => (
                    <option key={s.key} value={s.key}>{s.emoji} {s.name}</option>
                  ))}
                </select>
                <Button variant="secondary" className="mt-2" onClick={handleGenerateVideoHook}>후킹 문구 생성</Button>
              </div>
              <div>
                <label className="soft-label text-xs font-bold text-[var(--color-muted)]">후킹 문구</label>
                <Input className="mt-2 w-full" value={videoHookText} onChange={(e) => setVideoHookText(e.target.value)} placeholder="후킹 문구 입력" />
              </div>
             </>
          ) : (
             /* Custom Studio Mode */
             <div className="md:col-span-2 space-y-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
               <div>
                  <label className="soft-label text-xs font-bold text-[var(--color-muted)]">Concept / Hook</label>
                  <Input 
                    className="mt-2 w-full" 
                    value={videoHookText} 
                    onChange={(e) => setVideoHookText(e.target.value)} 
                    placeholder="Enter your video concept or hook..." 
                  />
               </div>
               <div className="flex gap-2">
                  <Button variant="outline" onClick={handleCreateDraft} disabled={isStudioLoading || !videoHookText}>
                    {isStudioLoading ? 'Drafting...' : 'AI Draft Prompt'}
                  </Button>
               </div>
               
               {videoPrompt && (
                 <div className="space-y-2 pt-2 border-t border-slate-100">
                    <label className="soft-label text-xs font-bold text-purple-600">Director&apos;s Prompt (Editable)</label>
                    <textarea 
                      className="w-full h-32 p-3 text-sm bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 transition-all font-mono leading-relaxed"
                      value={videoPrompt}
                      onChange={(e) => setVideoPrompt(e.target.value)}
                    />
                    
                    <div className="flex gap-2 items-end">
                       <div className="flex-1">
                          <label className="soft-label text-xs font-bold text-[var(--color-muted)]">Refinement Instructions</label>
                          <Input 
                            className="mt-1 w-full" 
                            value={studioFeedback} 
                            onChange={(e) => setStudioFeedback(e.target.value)} 
                            placeholder="e.g. Make lighting warmer, zoom in slower..." 
                          />
                       </div>
                       <Button onClick={handleRefinePrompt} disabled={isStudioLoading || !studioFeedback}>
                         {isStudioLoading ? 'Refining...' : 'Refine'}
                       </Button>
                    </div>
                 </div>
               )}
             </div>
          )}
        </div>
        
        {/* Common Settings */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-slate-100">
             <div>
               <label className="soft-label text-xs text-[var(--color-muted)]">Resolution</label>
               <select className="soft-input mt-1 w-full text-xs" value={videoResolution} onChange={(e) => setVideoResolution(e.target.value)}>
                  {videoPresets?.resolutions?.map((r) => <option key={r} value={r}>{r}</option>)}
               </select>
             </div>
             <div>
               <label className="soft-label text-xs text-[var(--color-muted)]">Duration</label>
                <select className="soft-input mt-1 w-full text-xs" value={videoDuration} onChange={(e) => setVideoDuration(Number(e.target.value))}>
                  {videoPresets?.durations?.map((d) => <option key={d} value={d}>{d}s</option>)}
               </select>
             </div>
             {/* Add more common controls if needed */}
        </div>

        <Button onClick={handleGenerateVideo} disabled={isVideoGenerating} className="w-full h-12 text-lg font-bold bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 shadow-lg text-white">
          {isVideoGenerating ? 'Generaing High-Fidelity Video...' : '🎬 Generate Video'}
        </Button>
        {videoError && <p className="text-sm text-red-500 font-medium text-center">{videoError}</p>}
      </div>
      {generatedVideoUrl && (
        <Card className="overflow-hidden border-0 shadow-2xl ring-1 ring-black/5 bg-slate-900">
          <div className="relative aspect-[9/16] max-h-[600px] mx-auto">
             <video src={generatedVideoUrl} controls className="w-full h-full object-contain" />
          </div>
          <div className="p-4 bg-white flex justify-between items-center gap-4">
             <p className="text-xs font-mono text-slate-500 line-clamp-3 hover:line-clamp-none cursor-pointer transition-all flex-1">{videoPrompt}</p>
               <div className="flex flex-col items-end gap-1">
                 <div className="flex items-center gap-2">
                   <select 
                     className="soft-input py-1 px-2 text-xs" 
                     value={extensionDuration} 
                     onChange={(e) => setExtensionDuration(Number(e.target.value))}
                   >
                     {[4, 5, 6, 7].map(d => <option key={d} value={d}>+{d}s</option>)}
                   </select>
                   <Button 
                     variant="outline" 
                     size="sm" 
                     onClick={handleExtendVideo} 
                     disabled={isExtending}
                     className="border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                   >
                     {isExtending ? 'Extending...' : 'Extend'}
                   </Button>
                 </div>
                 <p className="text-[10px] text-gray-400">Max Gap: 7s per step | Total Limit: 141s</p>
               </div>
          </div>
        </Card>
      )}
    </div>
  );
}
