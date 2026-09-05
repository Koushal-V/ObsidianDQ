"use client";

import React, { useState } from "react";
import { AlertOctagon, ShieldAlert, Zap, Check, ArrowRight, Database, Activity } from "lucide-react";

interface RootCauseTabProps {
  rca: {
    failing_table: string;
    root_cause_table: string;
    upstream_path: string[];
    summary_explanation: string;
    severity_score: number;
    blast_radius: string;
    auto_quarantine_sql: string;
  };
  onExecuteQuarantine?: () => void;
}

export const RootCauseTab: React.FC<RootCauseTabProps> = ({ rca, onExecuteQuarantine }) => {
  const [quarantined, setQuarantined] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    failing_table,
    root_cause_table,
    upstream_path,
    summary_explanation,
    severity_score,
    blast_radius,
    auto_quarantine_sql,
  } = rca;

  const handleQuarantine = async () => {
    setLoading(true);
    try {
      if (onExecuteQuarantine) {
        await onExecuteQuarantine();
      } else {
        await fetch("http://localhost:8000/api/pipeline/quarantine", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input_file: null }),
        });
      }
      setQuarantined(true);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const severityColor =
    severity_score >= 8
      ? { bg: "bg-rose-600", text: "text-white" }
      : severity_score >= 5
      ? { bg: "bg-amber-400", text: "text-[#3D1534]" }
      : { bg: "bg-emerald-600", text: "text-white" };

  return (
    <div className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl shadow-sm overflow-hidden">
      {/* Header Banner (Midnight Violet #3D1534 bg, Seashell #FFF4EB text) */}
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-rose-600 rounded-xl text-white shadow-sm">
            <AlertOctagon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-extrabold text-base text-[#FFF4EB]">Root Cause Diagnostics &amp; Auto-Quarantine</h3>
            <p className="text-xs text-[#A6BCC9] mt-0.5">
              Graph-based lineage traversal pinpointing origin table &amp; remediation vector
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#A6BCC9] font-medium">Impact Severity:</span>
          <span
            className={`px-3 py-1.5 text-xs font-extrabold rounded-xl shadow-sm ${severityColor.bg} ${severityColor.text}`}
          >
            {severity_score} / 10
          </span>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* 3 Impact Cards (Wheat Surface #F6E0B6) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {/* Downstream Affected */}
          <div className="bg-[#F6E0B6] border-2 border-[#E4CA97] rounded-2xl p-4 space-y-1.5 shadow-sm">
            <div className="text-[10px] uppercase font-extrabold text-[#3D1534]/60 tracking-wider">
              Downstream Affected
            </div>
            <div className="flex items-center gap-2 font-mono font-extrabold text-base text-rose-700">
              <Database className="w-4 h-4 text-rose-600" />
              {failing_table}
            </div>
          </div>

          {/* Root Cause Origin */}
          <div className="bg-[#F6E0B6] border-2 border-[#E4CA97] rounded-2xl p-4 space-y-1.5 shadow-sm">
            <div className="text-[10px] uppercase font-extrabold text-[#3D1534]/60 tracking-wider">
              Root Cause Origin
            </div>
            <div className="flex items-center gap-2 font-mono font-extrabold text-base text-[#3D1534]">
              <ShieldAlert className="w-4 h-4 text-[#3E4B8E]" />
              {root_cause_table}
            </div>
          </div>

          {/* Blast Radius */}
          <div className="bg-[#F6E0B6] border-2 border-[#E4CA97] rounded-2xl p-4 space-y-1.5 shadow-sm">
            <div className="text-[10px] uppercase font-extrabold text-[#3D1534]/60 tracking-wider">
              Blast Radius Impact
            </div>
            <div className="flex items-center gap-2 font-extrabold text-sm text-[#3D1534]">
              <Activity className="w-4 h-4 text-rose-600" />
              {blast_radius}
            </div>
          </div>
        </div>

        {/* Upstream Dependency Chain (Powder Blue Secondary Panel #A6BCC9/30) */}
        <div className="bg-[#A6BCC9]/25 border-2 border-[#A6BCC9] rounded-2xl p-5 shadow-sm">
          <div className="text-[10px] uppercase font-extrabold text-[#3D1534] tracking-wider mb-3">
            Upstream Dependency Vector
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {upstream_path.map((step, idx) => (
              <React.Fragment key={idx}>
                <span className="px-3.5 py-1.5 font-mono text-xs font-extrabold bg-white border border-[#A6BCC9] text-[#3D1534] rounded-xl shadow-sm">
                  {step}
                </span>
                {idx < upstream_path.length - 1 && (
                  <ArrowRight className="w-4 h-4 text-[#3E4B8E]" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Summary Explanation (Wheat #F6E0B6 Surface) */}
        <div className="bg-[#F6E0B6] border-2 border-[#E4CA97] rounded-2xl p-5 shadow-sm">
          <div className="text-[10px] font-extrabold uppercase text-[#3E4B8E] tracking-wider mb-1.5">
            Root Cause Narrative Explanation (Gemini LLM)
          </div>
          <p className="text-sm font-medium text-[#3D1534] leading-relaxed">{summary_explanation}</p>
        </div>

        {/* Auto-Quarantine Section */}
        <div className="bg-[#FFF4EB] border-2 border-[#A6BCC9] rounded-2xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h4 className="font-extrabold text-sm text-[#3D1534] flex items-center gap-2">
                <Zap className="w-4 h-4 text-[#3E4B8E]" />
                Auto-Generated SQL Quarantine Action
              </h4>
              <p className="text-xs text-[#3D1534]/70 mt-0.5">
                Isolates corrupted rows into staging quarantine before downstream pipeline execution
              </p>
            </div>

            {/* Action Button (French Blue #3E4B8E bg + Seashell #FFF4EB text) */}
            <button
              onClick={handleQuarantine}
              disabled={quarantined || loading}
              className={`flex items-center gap-2 px-5 py-2.5 text-xs font-extrabold rounded-xl transition-all shadow-md ${
                quarantined
                  ? "bg-emerald-600 text-[#FFF4EB] cursor-default"
                  : "bg-[#3E4B8E] hover:bg-[#2F396E] text-[#FFF4EB] active:scale-95 disabled:opacity-50"
              }`}
            >
              {quarantined ? (
                <>
                  <Check className="w-4 h-4 text-[#FFF4EB]" />
                  Quarantine Executed
                </>
              ) : loading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-[#FFF4EB]/40 border-t-[#FFF4EB] rounded-full animate-spin" />
                  Executing…
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-[#F6E0B6]" />
                  1-Click Execute Quarantine
                </>
              )}
            </button>
          </div>

          <pre className="font-mono text-xs font-bold text-[#3D1534] bg-white border border-[#A6BCC9] p-4 rounded-xl overflow-x-auto shadow-sm">
            <code>{auto_quarantine_sql}</code>
          </pre>
        </div>
      </div>
    </div>
  );
};
