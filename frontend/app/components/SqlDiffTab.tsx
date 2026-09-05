"use client";

import React from "react";
import { Code, CheckCircle2, ArrowRight, Sparkles, AlertCircle } from "lucide-react";

interface TokenReplacement {
  original_token: string;
  corrected_token: string;
  reason: string;
}

interface SqlDiffTabProps {
  sqlDiagnostics: {
    has_error: boolean;
    original_sql: string;
    repaired_sql: string;
    tokens_replaced: TokenReplacement[];
  };
}

export const SqlDiffTab: React.FC<SqlDiffTabProps> = ({ sqlDiagnostics }) => {
  const { has_error, original_sql, repaired_sql, tokens_replaced } = sqlDiagnostics;

  return (
    <div className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl shadow-sm overflow-hidden">
      {/* Header Banner (Midnight Violet #3D1534 bg, Seashell #FFF4EB text) */}
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-[#3E4B8E] rounded-xl text-[#FFF4EB]">
            <Code className="w-5 h-5 text-[#F6E0B6]" />
          </div>
          <div>
            <h3 className="font-extrabold text-base text-[#FFF4EB]">AST-Grounded SQL Self-Healing</h3>
            <p className="text-xs text-[#A6BCC9] mt-0.5">
              Zero-hallucination query repair via sqlglot AST parsing &amp; DuckDB active schema matching
            </p>
          </div>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-extrabold rounded-full border ${
            has_error
              ? "bg-emerald-500 text-white border-emerald-600"
              : "bg-[#F6E0B6] text-[#3D1534] border-[#E4CA97]"
          }`}
        >
          {has_error ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              AST HEALED &amp; VALIDATED
            </>
          ) : (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              SYNTAX CONFORMANT
            </>
          )}
        </span>
      </div>

      <div className="p-6 space-y-6">
        {/* Side-by-side SQL Diff */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Original Query */}
          <div className="bg-rose-50/80 border-2 border-rose-200 rounded-2xl overflow-hidden flex flex-col">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-rose-200 bg-white">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              <span className="text-xs font-extrabold uppercase tracking-wider text-rose-800">
                Original Query (With Errors)
              </span>
            </div>
            <pre className="font-mono text-xs text-[#3D1534] p-4 overflow-x-auto whitespace-pre-wrap leading-relaxed flex-1">
              <code>{original_sql}</code>
            </pre>
          </div>

          {/* Repaired Query */}
          <div className="bg-emerald-50/80 border-2 border-emerald-200 rounded-2xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-emerald-200 bg-white">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-800">
                  AST-Repaired &amp; Validated Query
                </span>
              </div>
            </div>
            <pre className="font-mono text-xs text-emerald-900 font-bold p-4 overflow-x-auto whitespace-pre-wrap leading-relaxed flex-1">
              <code>{repaired_sql}</code>
            </pre>
          </div>
        </div>

        {/* Token Transformations (Wheat #F6E0B6 Surface) */}
        {tokens_replaced && tokens_replaced.length > 0 && (
          <div className="bg-[#F6E0B6] border-2 border-[#E4CA97] rounded-2xl p-5 shadow-sm">
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#3D1534] mb-3.5 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#3E4B8E]" />
              Deterministic AST Token Transformations
            </h4>
            <div className="space-y-3">
              {tokens_replaced.map((token, idx) => (
                <div
                  key={idx}
                  className="bg-[#FFF4EB] border border-[#A6BCC9] rounded-xl px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm"
                >
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono text-xs px-2.5 py-1 rounded-lg bg-rose-100 text-rose-800 border border-rose-300 font-bold line-through">
                      {token.original_token}
                    </span>
                    <ArrowRight className="w-4 h-4 text-[#3E4B8E] shrink-0" />
                    <span className="font-mono text-xs px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-900 border border-emerald-300 font-extrabold">
                      {token.corrected_token}
                    </span>
                  </div>
                  <p className="text-xs text-[#3D1534]/80 sm:text-right max-w-sm font-medium">
                    {token.reason}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
