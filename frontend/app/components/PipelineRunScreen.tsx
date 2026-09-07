"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  Loader2,
  Circle,
  Database,
  Search,
  GitBranch,
  Code2,
  Wrench,
  ShieldCheck,
} from "lucide-react";

const PIPELINE_STAGES = [
  {
    id: "profiling",
    node: "NODE 1",
    label: "Stage Profiling",
    detail: "Scanning dataset schema, row counts, and column statistics…",
    icon: Database,
    durationMs: 1800,
  },
  {
    id: "dq",
    node: "NODE 2",
    label: "DQ Detection",
    detail: "Running rule-based checks — nulls, type violations, out-of-range values…",
    icon: Search,
    durationMs: 2200,
  },
  {
    id: "lineage",
    node: "NODE 3",
    label: "Lineage & Root Cause",
    detail: "Agent investigating upstream lineage graph to find origin of failures…",
    icon: GitBranch,
    durationMs: 3400,
  },
  {
    id: "sql",
    node: "NODE 4",
    label: "SQL Healing",
    detail: "Applying AST-validated SQL repairs to transformation queries…",
    icon: Code2,
    durationMs: 2000,
  },
  {
    id: "remediation",
    node: "NODE 5",
    label: "Remediation",
    detail: "Quarantining bad rows, applying approved containment actions…",
    icon: Wrench,
    durationMs: 2500,
  },
  {
    id: "guardrails",
    node: "NODE 6",
    label: "Guardrails & Verification",
    detail: "Re-running DQ checks on cleaned artifact, persisting incident memory…",
    icon: ShieldCheck,
    durationMs: 1600,
  },
];

type StageStatus = "pending" | "running" | "done";

interface PipelineRunScreenProps {
  ticketId: string;
  inputFile?: string;
  sqlFile?: string;
  /** Called after animation completes so the parent can transition to the results console */
  onComplete?: () => void;
}

export function PipelineRunScreen({
  ticketId,
  inputFile,
  sqlFile,
  onComplete,
}: PipelineRunScreenProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [statuses, setStatuses] = useState<StageStatus[]>(
    PIPELINE_STAGES.map((_, i) => (i === 0 ? "running" : "pending"))
  );

  useEffect(() => {
    let idx = 0;

    function advance() {
      if (idx >= PIPELINE_STAGES.length) return;
      const duration = PIPELINE_STAGES[idx].durationMs;
      setTimeout(() => {
        setStatuses((prev) => {
          const next = [...prev];
          next[idx] = "done";
          if (idx + 1 < PIPELINE_STAGES.length) next[idx + 1] = "running";
          return next;
        });
        setCurrentIndex(idx + 1);
        idx++;
        if (idx < PIPELINE_STAGES.length) {
          advance();
        } else {
          // All done — wait a beat then hand off
          setTimeout(() => onComplete?.(), 900);
        }
      }, duration);
    }

    advance();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeStage = PIPELINE_STAGES[Math.min(currentIndex, PIPELINE_STAGES.length - 1)];
  const allDone = statuses.every((s) => s === "done");

  return (
    <div className="min-h-screen bg-[#FFF4EB] flex flex-col items-center justify-start py-12 px-4">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center mb-10"
      >
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#3E4B8E]/10 border border-[#3E4B8E]/20 text-[#3E4B8E] text-xs font-bold mb-4">
          <span className="w-2 h-2 rounded-full bg-[#3E4B8E] animate-pulse" />
          PIPELINE EXECUTING — {ticketId}
        </div>
        <h1 className="text-3xl font-extrabold text-[#3D1534] tracking-tight">
          ObsidianDQ is investigating your data
        </h1>
        <p className="mt-2 text-sm text-[#3D1534]/60 font-medium max-w-md mx-auto">
          The autonomous agent pipeline is running. Each step completes before the next begins.
        </p>
      </motion.div>

      {/* Stage list */}
      <div className="w-full max-w-2xl space-y-3">
        {PIPELINE_STAGES.map((stage, i) => {
          const status = statuses[i];
          const Icon = stage.icon;
          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.06 }}
            >
              <div
                className={`flex items-center gap-4 rounded-xl border-2 px-5 py-3.5 transition-all duration-300 ${
                  status === "done"
                    ? "border-emerald-300 bg-emerald-50"
                    : status === "running"
                    ? "border-[#3E4B8E] bg-white shadow-md"
                    : "border-[#A6BCC9]/30 bg-white/50 opacity-50"
                }`}
              >
                {/* Icon */}
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                    status === "done"
                      ? "bg-emerald-100"
                      : status === "running"
                      ? "bg-[#3E4B8E]/10"
                      : "bg-[#A6BCC9]/10"
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 ${
                      status === "done"
                        ? "text-emerald-700"
                        : status === "running"
                        ? "text-[#3E4B8E]"
                        : "text-[#3D1534]/30"
                    }`}
                  />
                </div>

                {/* Label */}
                <div className="flex-1 min-w-0">
                  <div
                    className={`text-[10px] font-extrabold uppercase tracking-widest ${
                      status === "done"
                        ? "text-emerald-600"
                        : status === "running"
                        ? "text-[#3E4B8E]"
                        : "text-[#3D1534]/30"
                    }`}
                  >
                    {stage.node}
                  </div>
                  <div
                    className={`text-sm font-extrabold mt-0.5 ${
                      status === "done"
                        ? "text-emerald-800"
                        : status === "running"
                        ? "text-[#3D1534]"
                        : "text-[#3D1534]/40"
                    }`}
                  >
                    {stage.label}
                  </div>
                </div>

                {/* Status icon */}
                <div className="shrink-0">
                  {status === "done" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  ) : status === "running" ? (
                    <Loader2 className="w-5 h-5 text-[#3E4B8E] animate-spin" />
                  ) : (
                    <Circle className="w-5 h-5 text-[#A6BCC9]/40" />
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Active stage context card */}
      <AnimatePresence mode="wait">
        {!allDone && (
          <motion.div
            key={activeStage.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="mt-8 max-w-lg w-full bg-[#3D1534] text-[#FFF4EB] rounded-2xl px-6 py-4 flex items-start gap-3 shadow-lg"
          >
            <Loader2 className="w-4 h-4 mt-0.5 shrink-0 animate-spin text-[#F6E0B6]" />
            <div>
              <div className="text-[10px] font-extrabold uppercase tracking-widest text-[#A6BCC9] mb-0.5">
                {activeStage.node} · ACTIVE
              </div>
              <div className="text-sm font-bold text-[#FFF4EB]">{activeStage.label}</div>
              <div className="mt-1 text-xs text-[#FFF4EB]/60 font-medium leading-relaxed">
                {activeStage.detail}
              </div>
            </div>
          </motion.div>
        )}

        {allDone && (
          <motion.div
            key="done"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
            className="mt-8 max-w-lg w-full bg-emerald-700 text-white rounded-2xl px-6 py-4 flex items-center gap-3 shadow-lg"
          >
            <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-200" />
            <div>
              <div className="text-sm font-extrabold">All Stages Complete</div>
              <div className="text-xs text-white/70 font-medium mt-0.5">
                Preparing incident console…
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File context */}
      <div className="mt-10 flex flex-wrap items-center justify-center gap-4 text-xs text-[#3D1534]/40 font-mono font-bold">
        {inputFile && (
          <span>
            Dataset:{" "}
            {inputFile.split(/[/\\]/).pop()}
          </span>
        )}
        {sqlFile && (
          <span>
            SQL:{" "}
            {sqlFile.split(/[/\\]/).pop()}
          </span>
        )}
      </div>
    </div>
  );
}
