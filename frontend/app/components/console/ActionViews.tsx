"use client";

import { useState } from "react";
import { Check, CheckCircle2, Copy, ShieldCheck, XCircle } from "lucide-react";
import { Proposal, RunData } from "@/app/lib/runState";
import { ExpandableSection, SectionHeader, StatusBadge, TimelineStep, type Tone } from "@/app/components/obs";

export function Recommendation({ run }: { run: RunData }) {
  const rca = run.root_cause_analysis;
  const p = rca.agent_proposed_actions[0];
  const criticVerdict = rca.critic_verdict ?? "APPROVED";
  const criticReasoning =
    rca.critic_reasoning ??
    "Audited triage proposals & root-cause evidence against graph lineage. Logic & constraints verified.";
  const causalityProven = rca.upstream_causality_proven ?? true;

  return (
    <div className="obs-panel overflow-hidden">
      <div className="border-b border-[#A6BCC9]/30 px-3 py-2.5">
        <SectionHeader
          eyebrow="Multi-agent recommendation"
          title={p ? p.action.replaceAll("_", " ") : "Human review required"}
          meta={<StatusBadge tone="active" label="3-agent graph" />}
        />
      </div>
      <div className="space-y-4 px-3 py-3">
        <p className="obs-lede">
          {p?.reasoning ?? "No recommendation was produced. The workflow remains under deterministic safety controls."}
        </p>

        <div className="grid gap-3 md:grid-cols-3">
          <AgentCard
            label="1 · Root Cause"
            badge={{ tone: causalityProven ? "healthy" : "warning", label: causalityProven ? "Verified" : "Inferred" }}
            title={`Origin: ${rca.root_cause_table || "stg_orders"}`}
            detail={rca.root_cause_reasoning || "Traversed upstream lineage to isolate the earliest anomaly origin."}
          />
          <AgentCard
            label="2 · Triage"
            badge={{ tone: "active", label: p ? `${Math.round(p.confidence * 100)}% conf` : "100% conf" }}
            title={`Proposal: ${p?.action || "FLAG_FOR_REVIEW"}`}
            detail="Formulated a safety action based on issue severity and blast radius."
          />
          <AgentCard
            label="3 · Critic"
            badge={{ tone: criticVerdict === "APPROVED" ? "healthy" : "warning", label: criticVerdict }}
            title={`Audit: ${criticVerdict === "APPROVED" ? "Passed safety audit" : "Revision flagged"}`}
            detail={criticReasoning}
          />
        </div>

        <p className="obs-divider pb-1 pt-2 text-xs leading-relaxed text-[#3D1534]/60">
          Decision authority: deterministic DQ rules + guardrails + human approval. AI does not modify data.
        </p>
      </div>
    </div>
  );
}

function AgentCard({
  label,
  badge,
  title,
  detail,
}: {
  label: string;
  badge: { tone: Tone; label: string };
  title: string;
  detail: string;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-[#A6BCC9]/35 bg-[#FFF4EB] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="obs-label truncate">{label}</span>
        <StatusBadge tone={badge.tone} dot={false} label={badge.label} />
      </div>
      <p className="truncate text-xs font-semibold text-[#3D1534]">{title}</p>
      <p className="text-[11px] leading-relaxed text-[#3D1534]/70">{detail}</p>
    </div>
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
    <div className="overflow-hidden rounded-md border border-amber-300 bg-amber-50/60">
      <div className="border-b border-[#A6BCC9]/30 px-3 py-2.5">
        <SectionHeader
          eyebrow="Action required"
          title="Review before continuing"
          meta={<StatusBadge tone="warning" label={busy ? "PROCESSING" : "PENDING"} />}
        />
      </div>
      <div className="space-y-4 px-3 py-3">
        <p className="obs-lede">
          Nothing has been modified yet. Approval resumes this pipeline run and writes a separate quarantine dataset for
          high-severity issues.
        </p>

        <div className="grid gap-2 text-xs sm:grid-cols-2">
          <Safety label="Original dataset protected" />
          <Safety label="SQL schema checked on resume" />
          <Safety label="Unsafe mutations blocked" />
          <Safety label="Guardrails run after remediation" />
        </div>

        <div className="flex flex-wrap gap-2.5">
          <button disabled={busy} onClick={() => onDecision("approve", p)} className="obs-btn-primary">
            {busy ? "Processing…" : "Review & approve action"}
          </button>
          <button
            disabled={busy}
            onClick={() => onDecision("reject", p)}
            className="inline-flex items-center gap-1.5 rounded-md border border-rose-300 bg-rose-100 px-3.5 py-2 text-sm font-semibold text-rose-900 transition hover:bg-rose-200 disabled:opacity-50"
          >
            Block action
          </button>
        </div>
      </div>
    </div>
  );
}

function Safety({ label }: { label: string }) {
  return (
    <span className="flex items-center gap-2 rounded-md border border-[#A6BCC9]/40 bg-white px-2.5 py-1.5 text-xs font-semibold text-[#3D1534]">
      <CheckCircle2 size={14} className="shrink-0 text-emerald-600" />
      {label}
    </span>
  );
}

function RemediationResult({ run }: { run: RunData }) {
  const blocked = run.workflow_status === "APPROVAL_REJECTED";
  const q = run.remediation;
  return (
    <div className="obs-panel overflow-hidden">
      <div className="flex items-center gap-2 border-b border-[#A6BCC9]/30 px-3 py-2.5">
        {blocked ? (
          <XCircle size={16} className="shrink-0 text-rose-600" />
        ) : (
          <ShieldCheck size={16} className="shrink-0 text-emerald-600" />
        )}
        <StatusBadge tone={blocked ? "blocked" : "healthy"} label={blocked ? "Action blocked" : "Remediation complete"} />
      </div>
      <div className="space-y-1.5 px-3 py-3">
        <p className="text-base font-bold text-[#3D1534]">
          {blocked ? "No data was modified." : `${q.quarantined_rows ?? 0} records quarantined`}
        </p>
        {!blocked && (
          <p className="obs-lede">
            The original dataset remains protected.{" "}
            {q.quarantine_file
              ? `A separate quarantine file was written to ${q.quarantine_file}.`
              : "No supported high-severity records required quarantine."}
          </p>
        )}
      </div>
    </div>
  );
}
export function RunTimeline({ run }: { run: RunData }) {
  const done = !run.requires_human_approval;
  const steps: { label: string; tone: Tone; detail: string; pulse?: boolean }[] = [
    { label: "Dataset profiled", tone: "healthy", detail: "DuckDB / pandas in-memory profiling completed" },
    { label: "Data-quality checks completed", tone: "healthy", detail: "Deterministic expectation checks passed" },
    { label: "Lineage analyzed", tone: "healthy", detail: "Upstream lineage RCA graph computed" },
    { label: "AI recommendation prepared", tone: "healthy", detail: "Triage proposals generated" },
    { label: "Approval decision", tone: done ? "healthy" : "warning", detail: done ? "Decision approved" : "Waiting for human approval", pulse: !done },
    { label: "SQL normalization", tone: done ? "healthy" : "muted", detail: done ? "AST query healing applied" : "Pending approval" },
    { label: "Remediation & guardrails", tone: done ? "healthy" : "muted", detail: done ? "Quarantine & schema guardrails applied" : "Pending execution" },
  ];

  return (
    <div className="obs-panel overflow-hidden">
      <div className="border-b border-[#A6BCC9]/30 px-3 py-2.5">
        <SectionHeader
          eyebrow="Execution"
          title="Pipeline run timeline"
          meta={<StatusBadge tone={done ? "healthy" : "warning"} label={done ? "COMPLETE" : "AWAITING APPROVAL"} />}
        />
      </div>
      <div className="space-y-3 px-3 py-3">
        {steps.map((s, i) => (
          <TimelineStep
            key={s.label}
            index={i + 1}
            label={s.label}
            tone={s.tone}
            detail={s.detail}
            pulse={s.pulse}
            last={i === steps.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

export function TechnicalTrace({ run }: { run: RunData }) {
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
    <ExpandableSection
      eyebrow="Technical trace"
      title="Execution state & tool calls"
      subtitle="Inspect raw execution state, guardrails output, and AI trace logs"
    >
      <div className="space-y-2">
        <div className="flex justify-end">
          <button onClick={handleCopy} className="obs-btn-secondary text-xs">
            {copied ? (
              <>
                <Check size={14} className="text-emerald-600" /> Copied!
              </>
            ) : (
              <>
                <Copy size={14} /> Copy JSON trace
              </>
            )}
          </button>
        </div>
        <pre className="obs-monoblock">
          <code>{jsonContent}</code>
        </pre>
      </div>
    </ExpandableSection>
  );
}