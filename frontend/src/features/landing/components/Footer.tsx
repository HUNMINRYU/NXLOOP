import React from 'react';

export default function Footer() {
  return (
    <footer className="bg-slate-50 text-slate-600 py-24 px-6 md:px-12 border-t border-slate-200/60 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 blur-[120px] rounded-full" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-teal-500/5 blur-[120px] rounded-full" />

      <div className="relative max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-16">
        <div className="col-span-1 md:col-span-2">
          <h2 className="font-display text-3xl font-bold mb-6 tracking-tight text-slate-900">
            NEX<span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-indigo-600">LOOP</span>
          </h2>
          <p className="font-body text-lg text-slate-600 max-w-sm mb-10 leading-relaxed font-medium">
            The next generation of automated video pipelines powered by Gemini machine intelligence.
          </p>
          <div className="flex gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="w-12 h-12 bg-white border-2 border-slate-200/60 rounded-xl hover:bg-slate-50 hover:border-teal-600/50 transition-all cursor-pointer flex items-center justify-center group">
                <div className="w-2 h-2 bg-slate-400 rounded-full group-hover:scale-150 group-hover:bg-teal-600 transition-all" />
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="font-display text-sm font-bold mb-8 text-slate-900 uppercase tracking-[0.2em]">Service</h4>
          <ul className="space-y-4 font-semibold">
            <li><a href="#pipeline" className="hover:text-teal-600 transition-colors">Pipeline</a></li>
            <li><a href="#" className="hover:text-teal-600 transition-colors">Archive</a></li>
            <li><a href="#" className="hover:text-teal-600 transition-colors">Analytics</a></li>
            <li><a href="#" className="hover:text-teal-600 transition-colors">Prompt Lab</a></li>
          </ul>
        </div>

        <div>
          <h4 className="font-display text-sm font-bold mb-8 text-slate-900 uppercase tracking-[0.2em]">Company</h4>
          <ul className="space-y-4 font-semibold">
            <li className="text-slate-500">Email: help@nexloop.ai</li>
            <li className="text-slate-500">Address: Global AI Hub</li>
            <li><a href="#" className="hover:text-teal-600 transition-colors">Privacy Policy</a></li>
            <li><a href="#" className="hover:text-teal-600 transition-colors">Terms of Service</a></li>
          </ul>
        </div>
      </div>

      <div className="max-w-7xl mx-auto mt-24 pt-8 border-t border-slate-200/60 flex flex-col md:flex-row justify-between items-center gap-6 text-sm font-semibold text-slate-500">
        <p>© 2026 NEXLOOP AI. ALL RIGHTS RESERVED.</p>
        <div className="flex gap-8">
          <a href="#" className="hover:text-slate-900 transition-colors">Twitter</a>
          <a href="#" className="hover:text-slate-900 transition-colors">LinkedIn</a>
          <a href="#" className="hover:text-slate-900 transition-colors">GitHub</a>
        </div>
      </div>
    </footer>
  );
}
