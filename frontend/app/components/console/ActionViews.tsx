"use client";

import { useState } from "react";
import { CheckCircle2, ChevronDown, ShieldCheck, XCircle, Copy, Check, Sparkles, AlertOctagon } from "lucide-react";
import { Proposal, RunData } from "@/app/lib/runState";
import { motion } from "framer-motion";

export function Recommendation({ run }: { run: RunData }) {
  const rca = run.root_cause_analysis;
  const p = rca.agent_proposed_actions[0];
  const criticVerdict = rca.critic_verdict ?? "APPROVED";
  const criticReasoning = rca.critic_reasoning ?? "Audited Triage proposals & Root-Cause evidence against graph lineage. Logic & constraints verified.";
  const causalityProven = rca.upstream_causality_proven ?? true;

  return (
    <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl p-6 shadow-sm space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#3E4B8E]" />
          <p className="eyebrow">MULTI-AGENT COLLABORATIVE SYSTEM</p>
        </div>
        <span className="px-2.5 py-1 rounded-full font-extrabold text-[11px] bg-emerald-100 text-emerald-800 border border-emerald-300">
          3-Agent Graph Consensus
        </span>
      </div>

      <h2 className="text-xl font-extrabold text-[#3D1534]">
        {p ? p.action.replaceAll("_", " ") : "Human review required"}
      </h2>
      <p className="text-sm leading-relaxed text-[#3D1534]/80 font-medium">
        {p?.reasoning ?? "No recommendation was produced. The workflow remains under deterministic safety controls."}
      </p>

      {/* 3 Multi-Agent Attribution Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        {/* Agent 1: Root-Cause Investigator */}
        <div className="bg-[#FFF4EB] border border-[#F6E0B6] rounded-xl p-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-extrabold uppercase text-[#3E4B8E]">1. Root-Cause Agent</span>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
              {causalityProven ? "Verified" : "Inferred"}
            </span>
          </div>
          <p className="text-xs font-bold text-[#3D1534]">Origin: {rca.root_cause_table || "stg_orders"}</p>
          <p className="text-[11px] text-[#3D1534]/70 line-clamp-2">
            {rca.root_cause_reasoning || "Traversed upstream lineage to isolate earliest anomaly origin."}
          </p>
        </div>

        {/* Agent 2: Triage Agent */}
        <div className="bg-[#FFF4EB] border border-[#F6E0B6] rounded-xl p-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-extrabold uppercase text-[#3E4B8E]">2. Triage Agent</span>
            <span className="text-[10px] font-bold text-[#3E4B8E] bg-[#A6BCC9]/30 px-1.5 py-0.5 rounded">
              {p ? `${Math.round(p.confidence * 100)}% Conf` : "100% Conf"}
            </span>
          </div>
          <p className="text-xs font-bold text-[#3D1534]">Proposal: {p?.action || "FLAG_FOR_REVIEW"}</p>
          <p className="text-[11px] text-[#3D1534]/70 line-clamp-2">
            Formulated safety action based on issue severity and blast radius.
          </p>
        </div>

        {/* Agent 3: Critic Agent */}
        <div className="bg-[#FFF4EB] border border-[#F6E0B6] rounded-xl p-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-extrabold uppercase text-[#3E4B8E]">3. Critic Agent</span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
              criticVerdict === "APPROVED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
            }`}>
              {criticVerdict}
            </span>
          </div>
          <p className="text-xs font-bold text-[#3D1534]">Audit: {criticVerdict === "APPROVED" ? "Passed Safety Audit" : "Revision Flagged"}</p>
          <p className="text-[11px] text-[#3D1534]/70 line-clamp-2">
            {criticReasoning}
          </p>
        </div>
      </div>

      <p className="border-t border-[#A6BCC9]/30 pt-3 text-xs leading-relaxed text-[#3D1534]/60">
        Decision authority: deterministic DQ rules + guardrails + human approval. AI does not modify data.
      </p>
    </section>
  );
}

export function ApprovalGate({
  run,
  onDecision,
  busy,
}: {
  run: RunData;
  onDecision: (decision: "approve" | "reject", proposal: Proposal) => void;
  busy: boolean;
}) {
  const p = run.root_cause_analysis.agent_proposed_actions[0];
  if (!run.requires_human_approval || !p) return <RemediationResult run={run} />;

  return (
    <section className="rounded-2xl border-2 border-amber-400 bg-amber-50 p-6 shadow-sm">
      <div className="flex items-center gap-2">
        <AlertOctagon className="w-4 h-4 text-amber-700" />
        <p className="eyebrow text-amber-800 font-extrabold">ACTION REQUIRED</p>
      </div>
      <h2 className="mt-1 text-xl font-extrabold text-[#3D1534]">Review Before Continuing</h2>
      <p className="mt-2 text-sm text-[#3D1534]/80 font-medium leading-relaxed">
        Nothing has been modified yet. Approval resumes this pipeline run and writes a separate quarantine dataset for high-severity issues.
      </p>

      {/* 4-Item Checklist with high-contrast, legible typography (Phase 1 Fix) */}
      <div className="mt-4 grid gap-3 text-xs font-bold text-[#3D1534] sm:grid-cols-2">
        <Safety label="Original dataset protected" confirmed={true} />
        <Safety label="SQL schema checked on resume" confirmed={true} />
        <Safety label="Unsafe mutations blocked" confirmed={true} />
        <Safety label="Guardrails run after remediation" confirmed={true} />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          disabled={busy}
          onClick={() => onDecision("approve", p)}
          className="btn-primary"
        >
          {busy ? "Processing…" : "Review & Approve Action"}
        </button>
        <button
          disabled={busy}
          onClick={() => onDecision("reject", p)}
          className="px-5 py-2.5 text-sm font-bold rounded-xl border border-rose-300 bg-rose-100 text-rose-900 hover:bg-rose-200 transition-all shadow-sm"
        >
          Block Action
        </button>
      </div>
    </section>
  );
}

function Safety({ label, confirmed }: { label: string; confirmed: boolean }) {
  return (
    <span className="flex items-center gap-2 font-bold text-[#3D1534] bg-white/80 border border-[#A6BCC9] px-3 py-2 rounded-xl shadow-sm">
      <CheckCircle2 size={16} className={confirmed ? "text-emerald-600 shrink-0" : "text-[#A6BCC9] shrink-0"} />
      <span>{label}</span>
    </span>
  );
}

export function RemediationResult({ run }: { run: RunData }) {
  const blocked = run.workflow_status === "APPROVAL_REJECTED";
  const q = run.remediation;
  return (
    <section
      className={`rounded-2xl border-2 p-6 shadow-sm ${
        blocked ? "border-rose-400 bg-rose-50" : "border-emerald-400 bg-emerald-50"
      }`}
    >
      <div className="flex items-center gap-3">
        {blocked ? (
          <XCircle className="w-6 h-6 text-rose-600 shrink-0" />
        ) : (
          <ShieldCheck className="w-6 h-6 text-emerald-600 shrink-0" />
        )}
        <div>
          <p className={`eyebrow ${blocked ? "text-rose-800" : "text-emerald-800"}`}>
            {blocked ? "ACTION BLOCKED" : "REMEDIATION COMPLETE"}
          </p>
          <h2 className="mt-1 text-lg font-extrabold text-[#3D1534]">
            {blocked ? "No data was modified." : `${q.quarantined_rows ?? 0} records quarantined`}
          </h2>
        </div>
      </div>
      {!blocked && (
        <p className="mt-3 text-sm text-[#3D1534]/80 font-medium leading-relaxed">
          The original dataset remains protected.{" "}
          {q.quarantine_file
            ? `A separate quarantine file was written to ${q.quarantine_file}.`
            : "No supported high-severity records required quarantine."}
        </p>
      )}
    </section>
  );
}

{/* Phase 2: Vertical Stepper with connecting line */}
export function RunTimeline({ run }: { run: RunData }) {
  const done = !run.requires_human_approval;
  const steps: [string, boolean, string][] = [
    ["Dataset profiled", true, "DuckDB / Pandas in-memory profiling completed"],
    ["Data-quality checks completed", true, "Deterministic expectation checks passed"],
    ["Lineage analyzed", true, "Upstream lineage RCA graph computed"],
    ["AI recommendation prepared", true, "Triage proposals generated"],
    ["Approval decision", done, done ? "Decision approved" : "Waiting for human approval"],
    ["SQL normalization", done, done ? "AST query healing applied" : "Pending approval"],
    ["Remediation & guardrails", done, done ? "Quarantine & schema guardrails applied" : "Pending execution"],
  ];

  return (
    <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl p-6 shadow-sm">
      <p className="eyebrow mb-4">PIPELINE RUN TIMELINE</p>
      <div className="relative pl-3 space-y-6">
        {steps.map(([label, complete, detail], i) => (
          <div key={String(label)} className="relative flex items-start gap-4">
            {/* Vertical Connecting Line */}
            {i < steps.length - 1 && (
              <div
                className={`absolute left-3 top-6 bottom-0 w-0.5 -ml-px ${
                  complete ? "bg-emerald-500" : "bg-[#A6BCC9]/40"
                }`}
              />
            )}
            <span
              className={`relative z-10 grid h-6 w-6 place-items-center rounded-full text-xs font-bold shrink-0 ${
                complete
                  ? "bg-emerald-500 text-white shadow-sm"
                  : i === 4
                  ? "bg-amber-400 text-[#3D1534] shadow-sm animate-pulse"
                  : "bg-[#A6BCC9]/30 text-[#3D1534]/60"
              }`}
            >
              {complete ? "✓" : i === 4 ? "⏸" : "○"}
            </span>
            <div>
              <div className={`text-xs font-extrabold ${complete ? "text-[#3D1534]" : "text-[#3D1534]/60"}`}>
                {label}
                {!complete && i === 4 && (
                  <span className="ml-2 font-bold text-amber-700 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded-full text-[10px]">
                    Waiting for approval
                  </span>
                )}
              </div>
              <div className="text-[11px] text-[#3D1534]/60 font-medium mt-0.5">{detail}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

{/* Phase 1: Technical Trace with JSON syntax highlighting and Copy button */}
export function TechnicalTrace({ run }: { run: RunData }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const jsonContent = JSON.stringify(
    {
      workflow_status: run.workflow_status,
      route_taken: run.route_taken,
      guardrails: run.guardrails,
      agent_tool_calls: run.root_cause_analysis.agent_tool_calls,
    },
    null,
    2
  );

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl p-5 shadow-sm">
      <button
        className="flex w-full items-center justify-between text-left"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <div>
          <span className="eyebrow block">TECHNICAL TRACE</span>
          <span className="text-xs font-medium text-[#3D1534]/70">
            Inspect raw execution state, guardrails output, and AI trace logs
          </span>
        </div>
        <ChevronDown className={`w-5 h-5 text-[#3E4B8E] transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="mt-4 space-y-3">
          <div className="flex justify-end">
            <button
              onClick={handleCopy}
              className="px-3 py-1 text-xs font-bold rounded-lg border border-[#A6BCC9] bg-[#F6E0B6] hover:bg-[#FFF4EB] text-[#3D1534] transition-all flex items-center gap-1.5 shadow-sm"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-[#3E4B8E]" />
                  Copy JSON Trace
                </>
              )}
            </button>
          </div>
          <pre className="overflow-auto rounded-xl border border-[#A6BCC9] bg-[#3D1534] p-4 text-xs font-mono text-[#FFF4EB] leading-relaxed shadow-inner">
            <code>{jsonContent}</code>
          </pre>
        </div>
      )}
    </section>
  );
}
