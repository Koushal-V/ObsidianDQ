"use client";

import React from "react";
import { Ticket, ArrowLeft, Play, Database, FileCode, GitBranch, ShieldCheck, CheckCircle2, Zap } from "lucide-react";
import { motion } from "framer-motion";

interface ConfirmationTicketStepProps {
  config: {
    input_file?: string;
    sql_file?: string;
    lineage_file?: string;
    isPreset?: boolean;
  };
  onBack: () => void;
  onLaunch: () => void;
  loading: boolean;
}

export const ConfirmationTicketStep: React.FC<ConfirmationTicketStepProps> = ({
  config,
  onBack,
  onLaunch,
  loading,
}) => {
  const { input_file, sql_file, lineage_file, isPreset } = config;

  const ticketId = React.useMemo(
    () => `OBS-DQ-${Math.floor(100000 + Math.random() * 900000)}`,
    []
  );

  const ticketRows = [
    {
      icon: <Database className="w-4 h-4 text-[#3E4B8E]" />,
      label: "Dataset Source",
      value: input_file || "data/raw/stg_orders.parquet (default)",
    },
    {
      icon: <FileCode className="w-4 h-4 text-[#3E4B8E]" />,
      label: "Transformation Query",
      value: sql_file || "data/queries/fct_sales.sql (default)",
    },
    {
      icon: <GitBranch className="w-4 h-4 text-[#3E4B8E]" />,
      label: "Lineage Topology",
      value: lineage_file || "data/lineage/lineage.json (default)",
    },
  ];

  const modules = [
    "In-Memory Profiling (Pandas / DuckDB)",
    "AST-Grounded SQL Repair (sqlglot)",
    "Upstream Lineage RCA",
    "Auto-Quarantine Remediation",
    "Guardrail Schema Validation",
    "LangGraph Agentic Orchestration",
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="max-w-3xl mx-auto py-6 space-y-8"
    >
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#F6E0B6] border border-[#E4CA97] text-[#3D1534] text-xs font-bold shadow-sm">
          <Ticket className="w-3.5 h-3.5 text-[#3E4B8E]" />
          Step 2 of 3 — Job Confirmation Ticket
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-[#3D1534]">
          Review &amp; Launch Data Quality Run
        </h1>
        <p className="text-sm text-[#3D1534]/70 max-w-md mx-auto">
          Verify configuration ticket details before initializing LangGraph agent execution.
        </p>
      </div>

      {/* Ticket Card Container */}
      <div className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl shadow-md overflow-hidden">
        {/* Ticket Header Banner (Midnight Violet #3D1534 bg, Seashell #FFF4EB text) */}
        <div className="bg-[#3D1534] px-6 py-5 flex items-center justify-between text-[#FFF4EB]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-[#3E4B8E] rounded-xl text-[#FFF4EB]">
              <ShieldCheck className="w-5 h-5 text-[#F6E0B6]" />
            </div>
            <div>
              <span className="text-[10px] font-mono text-[#A6BCC9] uppercase tracking-wider">
                Job Ticket Reference
              </span>
              <div className="font-mono font-bold text-[#FFF4EB] text-base">{ticketId}</div>
            </div>
          </div>
          <span
            className={`px-3 py-1 text-[10px] font-extrabold rounded-full border uppercase tracking-wider ${
              isPreset
                ? "bg-[#F6E0B6] text-[#3D1534] border-[#E4CA97]"
                : "bg-white/10 text-[#FFF4EB] border-white/20"
            }`}
          >
            {isPreset ? "FEATURED DEMO" : "CUSTOM UPLOAD"}
          </span>
        </div>

        {/* Configuration Rows (Seashell bg, Powder Blue border) */}
        <div className="divide-y divide-[#A6BCC9]/30 px-6 py-2">
          {ticketRows.map((row, i) => (
            <div key={i} className="flex items-center justify-between py-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white rounded-lg border border-[#A6BCC9]/40 shadow-sm">
                  {row.icon}
                </div>
                <div>
                  <div className="text-[10px] text-[#3D1534]/60 font-bold uppercase tracking-wider">{row.label}</div>
                  <div className="text-xs font-mono font-bold text-[#3D1534] truncate max-w-xs sm:max-w-md mt-0.5">
                    {row.value}
                  </div>
                </div>
              </div>
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            </div>
          ))}
        </div>

        {/* Enabled Agentic Modules (Wheat #F6E0B6 surface) */}
        <div className="bg-[#F6E0B6]/60 border-t border-[#E4CA97] px-6 py-5">
          <div className="text-[10px] font-extrabold text-[#3D1534] uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-[#3E4B8E]" />
            Enabled Agentic Workflow Modules
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {modules.map((mod) => (
              <div key={mod} className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#3E4B8E] shrink-0" />
                <span className="text-xs font-semibold text-[#3D1534]">{mod}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between">
        {/* Secondary Button: Wheat bg, Midnight Violet text */}
        <button
          onClick={onBack}
          className="px-5 py-2.5 text-sm font-bold rounded-xl border border-[#E4CA97] bg-[#F6E0B6] hover:bg-[#FFF4EB] text-[#3D1534] transition-all flex items-center gap-2 shadow-sm"
        >
          <ArrowLeft className="w-4 h-4 text-[#3E4B8E]" />
          Back to Source Upload
        </button>

        {/* Primary Button: French Blue bg, Seashell text */}
        <button
          onClick={onLaunch}
          disabled={loading}
          className="px-7 py-3 text-sm font-extrabold rounded-xl bg-[#3E4B8E] hover:bg-[#2F396E] text-[#FFF4EB] transition-all shadow-md active:scale-95 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-[#FFF4EB]/40 border-t-[#FFF4EB] rounded-full animate-spin" />
              Running Agent Pipeline…
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-[#F6E0B6] text-[#F6E0B6]" />
              Launch Pipeline
            </>
          )}
        </button>
      </div>
    </motion.div>
  );
};
