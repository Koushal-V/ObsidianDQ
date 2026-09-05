"use client";

import React from "react";
import { ShieldCheck, Heart } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-[#3D1534] text-[#FFF4EB] mt-16 border-t border-[#3D1534]">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left */}
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-[#3E4B8E] rounded-lg text-[#FFF4EB]">
            <ShieldCheck className="w-4 h-4 text-[#F6E0B6]" />
          </div>
          <div>
            <span className="font-bold text-sm text-[#FFF4EB]">ObsidianDQ</span>
            <span className="text-xs text-[#A6BCC9] ml-2">
              Autonomous Self-Healing Data Pipeline Engine
            </span>
          </div>
        </div>

        {/* Center / Right links */}
        <div className="flex items-center gap-6 text-xs text-[#A6BCC9]">
          <span className="hover:text-[#FFF4EB] transition-colors cursor-pointer">
            Documentation
          </span>
          <span className="hover:text-[#FFF4EB] transition-colors cursor-pointer">
            AST Healer Specs
          </span>
          <span className="hover:text-[#FFF4EB] transition-colors cursor-pointer">
            Lineage Traversal
          </span>
          <span className="hover:text-[#FFF4EB] transition-colors cursor-pointer">
            API Endpoints
          </span>
        </div>

        {/* Copyright */}
        <div className="text-[11px] text-[#A6BCC9] flex items-center gap-1">
          <span>ObsidianDQ © {new Date().getFullYear()}</span>
          <span>·</span>
          <span>Deterministic Telemetry</span>
        </div>
      </div>
    </footer>
  );
};
