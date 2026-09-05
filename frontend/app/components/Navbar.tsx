"use client";

import React from "react";
import { ShieldCheck, Activity, Database, Sparkles } from "lucide-react";

export const Navbar: React.FC = () => {
  return (
    <nav className="w-full bg-[#3D1534] text-[#FFF4EB] shadow-md border-b border-[#3D1534]">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-3.5 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#3E4B8E] rounded-xl text-[#FFF4EB] shadow-sm">
            <ShieldCheck className="w-6 h-6 text-[#F6E0B6]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-[#FFF4EB]">
                ObsidianDQ
              </span>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-[#F6E0B6] text-[#3D1534] uppercase tracking-wider">
                Engine v2.0
              </span>
            </div>
            <p className="text-[11px] text-[#A6BCC9] font-medium hidden sm:block">
              Deterministic &amp; Agentic Data Quality Telemetry
            </p>
          </div>
        </div>

        {/* Right Status Indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs text-[#FFF4EB]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono text-[11px] font-medium">System Online</span>
          </div>

          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F6E0B6] text-[#3D1534] text-xs font-bold shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-[#3E4B8E]" />
            <span>FastAPI + LangGraph + DuckDB</span>
          </div>
        </div>
      </div>
    </nav>
  );
};
