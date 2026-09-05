"use client";

import React from "react";
import { ShieldAlert, ShieldCheck, AlertTriangle, Database, Clock, FileText, Activity } from "lucide-react";

interface HeaderBarProps {
  telemetry: {
    status: "HEALTHY" | "WARNING" | "ANOMALIES_DETECTED" | string;
    overall_health_score: number;
    total_records_scanned: number;
    execution_duration_ms: number;
    scanned_tables: string[];
  };
}

export const HeaderBar: React.FC<HeaderBarProps> = ({ telemetry }) => {
  const {
    status,
    overall_health_score,
    total_records_scanned,
    execution_duration_ms,
    scanned_tables,
  } = telemetry;

  const getStatusConfig = () => {
    switch (status) {
      case "HEALTHY":
        return {
          pill: "bg-emerald-50 border-emerald-300 text-emerald-800",
          icon: <ShieldCheck className="w-4 h-4 text-emerald-600" />,
          dot: "bg-emerald-500",
          label: "HEALTHY",
        };
      case "WARNING":
        return {
          pill: "bg-amber-50 border-amber-300 text-amber-800",
          icon: <AlertTriangle className="w-4 h-4 text-amber-600" />,
          dot: "bg-amber-500",
          label: "WARNING",
        };
      case "ANOMALIES_DETECTED":
      default:
        return {
          pill: "bg-rose-50 border-rose-300 text-rose-800",
          icon: <ShieldAlert className="w-4 h-4 text-rose-600" />,
          dot: "bg-rose-600",
          label: "ANOMALIES DETECTED",
        };
    }
  };

  const cfg = getStatusConfig();

  // Radial gauge math
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (overall_health_score / 100) * circumference;

  const scoreColor =
    overall_health_score >= 80
      ? "stroke-emerald-500 text-emerald-700"
      : overall_health_score >= 60
      ? "stroke-amber-500 text-amber-700"
      : "stroke-rose-500 text-rose-700";

  return (
    <div className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl p-5 shadow-sm">
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5">
        {/* Left — Brand & Status */}
        <div className="flex items-center gap-4">
          <div className="p-3 bg-[#3D1534] rounded-xl shadow-md text-[#FFF4EB]">
            <Activity className="w-6 h-6 text-[#F6E0B6]" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl font-extrabold text-[#3D1534] tracking-tight">ObsidianDQ</h1>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold rounded-full border ${cfg.pill}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                {cfg.icon}
                {cfg.label}
              </span>
            </div>
            <p className="text-xs text-[#3D1534]/70 mt-0.5 font-medium">
              Deterministic &amp; Agentic Telemetry Dashboard
            </p>
          </div>
        </div>

        {/* Center — Health Score Gauge (Wheat Surface #F6E0B6) */}
        <div className="flex items-center gap-3 bg-[#F6E0B6] border border-[#E4CA97] px-5 py-3 rounded-xl shadow-sm">
          <div className="relative w-14 h-14 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 64 64">
              <circle
                cx="32"
                cy="32"
                r={radius}
                className="stroke-[#A6BCC9]/40"
                strokeWidth="5"
                fill="transparent"
              />
              <circle
                cx="32"
                cy="32"
                r={radius}
                className={`transition-all duration-1000 ease-out ${scoreColor}`}
                strokeWidth="5"
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <span className={`absolute text-xs font-extrabold ${scoreColor}`}>
              {overall_health_score}%
            </span>
          </div>
          <div>
            <div className="text-[10px] uppercase font-extrabold text-[#3D1534]/60 tracking-wider">
              Health Score
            </div>
            <div className="text-sm font-extrabold text-[#3D1534]">
              {overall_health_score >= 80
                ? "Optimal Status"
                : overall_health_score >= 60
                ? "Review Required"
                : "Critical Anomalies"}
            </div>
          </div>
        </div>

        {/* Right — Telemetry Panels (Powder Blue Secondary Surface #A6BCC9/30) */}
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2.5 bg-[#A6BCC9]/25 border border-[#A6BCC9] px-4 py-2.5 rounded-xl">
            <Database className="w-4 h-4 text-[#3E4B8E]" />
            <div>
              <div className="text-[10px] text-[#3D1534]/60 font-bold uppercase tracking-wider">Records Scanned</div>
              <div className="text-sm font-extrabold text-[#3D1534]">
                {total_records_scanned.toLocaleString()}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 bg-[#A6BCC9]/25 border border-[#A6BCC9] px-4 py-2.5 rounded-xl">
            <Clock className="w-4 h-4 text-[#3E4B8E]" />
            <div>
              <div className="text-[10px] text-[#3D1534]/60 font-bold uppercase tracking-wider">Execution Time</div>
              <div className="text-sm font-extrabold text-[#3D1534]">
                {execution_duration_ms} ms
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 bg-[#A6BCC9]/25 border border-[#A6BCC9] px-4 py-2.5 rounded-xl">
            <FileText className="w-4 h-4 text-[#3E4B8E]" />
            <div>
              <div className="text-[10px] text-[#3D1534]/60 font-bold uppercase tracking-wider">Tables Analyzed</div>
              <div className="flex flex-wrap gap-1 mt-1">
                {scanned_tables.map((tbl) => (
                  <span
                    key={tbl}
                    className="px-2 py-0.5 text-[9px] font-mono font-bold bg-[#3E4B8E] text-[#FFF4EB] rounded"
                  >
                    {tbl}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
