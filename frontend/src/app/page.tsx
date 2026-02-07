import React from 'react';
import { 
  Navbar, 
  Hero, 
  VideoMessageSection, 
  SliderMessageSection, 
  Features, 
  LeadCaptureSection, 
  Footer 
} from '@/features/landing/index';
import { SLIDER_GIFS, SLIDER_IMAGES } from '@/features/landing/components/SliderMessageSection';

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden selection:bg-[#0ca678] selection:text-white">
      {/* Light Elegant Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
      <div className="absolute inset-0 bg-gradient-to-tr from-teal-500/[0.02] via-transparent to-indigo-500/[0.02]" />
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgb(15 23 42 / 0.08) 1px, transparent 1px),
            linear-gradient(to bottom, rgb(15 23 42 / 0.08) 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
        }}
      />
      <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-teal-400/[0.06] blur-[140px] rounded-full" />
      <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />

      <div className="relative z-10">
      <Navbar />

      <div className="relative">
        <Hero demoUrl="/pipeline/create" />
      </div>

      {/* Video + Message Section */}
      <VideoMessageSection />

      {/* 9:16 box - GIF 슬라이드 (Generate Video) */}
      <SliderMessageSection
        title="Generate Video, Don't Record"
        description="Your video is already ready. Let Gemini's automated pipeline uncover the best of your content."
        brandLabel="VEO 3.1"
        variant="green"
        images={SLIDER_GIFS}
      />

      {/* Social Proof / Stats Section - Light Marquee */}
      <section className="relative py-20 overflow-hidden bg-white/60 backdrop-blur-sm border-y border-slate-200/60">
        <div className="absolute inset-0 bg-gradient-to-r from-teal-500/[0.02] via-transparent to-indigo-500/[0.02] pointer-events-none" />
        <div className="flex whitespace-nowrap animate-marquee py-2">
          {[...Array(10)].map((_, i) => (
            <span key={i} className="flex items-center text-slate-400 text-2xl font-black mx-12 uppercase tracking-[0.2em]">
              <span className="text-teal-600">Gemini 3.0</span>
              <span className="mx-6 opacity-30">•</span>
              <span>Automated Pipeline</span>
              <span className="mx-6 opacity-30">•</span>
              <span className="text-indigo-600">VEO 3.1</span>
              <span className="mx-6 opacity-30">•</span>
              <span>Real-time Analysis</span>
              <span className="mx-6 opacity-40 ml-12">✦</span>
            </span>
          ))}
        </div>
      </section>

      {/* 9:16 box - 이미지 슬라이드 (Generate Thumbnail) */}
      <SliderMessageSection
        title="Generate thumbnail, Don't Edit"
        description="Set your goals, then let Gemini's machine intelligence bridge the gap between idea and engagement."
        brandLabel="Gemini 3.0"
        variant="cyan"
        images={SLIDER_IMAGES}
      />
      
      <Features />

      {/* CTA Section - Client Component */}
      <LeadCaptureSection />

      <Footer />
      </div>
    </main>
  );
}
