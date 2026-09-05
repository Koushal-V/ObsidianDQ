"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  Database,
  RefreshCw,
  Copy,
  Check,
  Activity,
  FileText,
} from "lucide-react";
import { AppShell } from "./AppShell";
import { ApprovalGate, Recommendation, RunTimeline, TechnicalTrace } from "./ActionViews";
import { DataPreviewTable, QualityTable, Unavailable } from "./DataViews";
import { IssueDetailDrawer } from "./IssueDetailDrawer";
import { LineageView } from "./LineageView";
import { Issue, Proposal, RunData, duration, pct, presentState, titleForIssue } from "@/app/lib/runState";

const base = typeof window === "undefined" ? "http://localhost:8000" : `http://${window.location.hostname}:8000`;

export function RunConsole({ initial }: { initial: RunData }) {
  const [run, setRun] = useState(initial);
  const [active, setActive] = useState("overview");
  const [issue, setIssue] = useState<Issue | null>(null);
  const [busy, setBusy] = useState(false);
  const [api, setApi] = useState(true);
  const [llmAvailable, setLlmAvailable] = useState<boolean | null>(null);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${base}/api/health`)
      .then((r) => r.json())
      .then((v) => {
        setApi(true);
        setLlmAvailable(Boolean(v.llm_available ?? v.gemini_available));
        setLlmProvider(v.llm_provider ?? (v.gemini_available ? "gemini" : null));
      })
      .catch(() => setApi(false));
  }, []);

  async function decide(decision: "approve" | "reject", proposal: Proposal) {
    setBusy(true);
    try {
      const res = await fetch(`${base}/api/pipeline/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: run.run_id,
          issue_id: proposal.issue_id,
          decision,
          action: proposal.action,
        }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.detail ?? "Unable to update the workflow.");
      setRun(payload);
      setActive("actions");
    } catch (error) {
      alert(error instanceof Error ? error.message : "Approval could not be processed.");
    } finally {
      setBusy(false);
    }
  }

  const state = presentState(run);

  return (
    <AppShell
      active={active}
      onNavigate={setActive}
      state={state}
      apiOnline={api}
      llmAvailable={llmAvailable}
      llmProvider={llmProvider}
      agentExecution={run.agent_execution}
    >
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
        {active === "overview" && (
          <Overview run={run} openIssue={setIssue} navigate={setActive} onDecision={decide} busy={busy} />
        )}
        {active === "issues" && <Issues run={run} openIssue={setIssue} />}
        {active === "lineage" && <LineageView run={run} />}
        {active === "data" && (
          <div className="space-y-5">
            <DataPreviewTable run={run} />
            <QualityTable run={run} />
          </div>
        )}
        {active === "actions" && (
          <div className="grid gap-5 xl:grid-cols-2">
            <div className="space-y-5">
              <Recommendation run={run} />
              <ApprovalGate run={run} onDecision={decide} busy={busy} />
            </div>
            <RunTimeline run={run} />
          </div>
        )}
        {active === "details" && <Details run={run} />}
      </motion.div>
      <IssueDetailDrawer issue={issue} run={run} close={() => setIssue(null)} />
    </AppShell>
  );
}

function Overview({
  run,
  openIssue,
  navigate,
  onDecision,
  busy,
}: {
  run: RunData;
  openIssue: (i: Issue) => void;
  navigate: (id: string) => void;
  onDecision: (d: "approve" | "reject", p: Proposal) => void;
  busy: boolean;
}) {
  return (
    <div className="space-y-6">
      <section className="grid gap-5 xl:grid-cols-[1.1fr_1.9fr]">
        <Health run={run} />
        <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <p className="eyebrow">WHAT HAPPENED?</p>
            <h1 className="mt-2 text-2xl font-extrabold text-[#3D1534] sm:text-3xl">
              {run.issues.length
                ? `${run.issues.length} data-quality issues detected in ${run.root_cause_analysis.failing_table}.`
                : "No data-quality issues were detected."}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#3D1534]/80 font-medium">
              {run.root_cause_analysis.summary_explanation}
            </p>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <button className="btn-primary" onClick={() => navigate("issues")}>
              Review Issues <ArrowRight size={15} className="text-[#F6E0B6]" />
            </button>
            <button
              className="px-5 py-2.5 text-sm font-bold rounded-xl border border-[#A6BCC9] bg-[#F6E0B6] hover:bg-[#FFF4EB] text-[#3D1534] transition-all shadow-sm"
              onClick={() => navigate("lineage")}
            >
              View Lineage Impact
            </button>
          </div>
        </section>
      </section>

      <Issues run={run} openIssue={openIssue} compact />

      <section className="grid gap-5 xl:grid-cols-2">
        <LineageView run={run} />
        <div className="space-y-5">
          <Recommendation run={run} />
          <ApprovalGate run={run} onDecision={onDecision} busy={busy} />
        </div>
      </section>
    </div>
  );
}

{/* Phase 2: Pipeline Health Gauge Re-use */}
function Health({ run }: { run: RunData }) {
  const h = run.pipeline_health;
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (h.overall_health_score / 100) * circumference;

  const scoreColor =
    h.overall_health_score >= 80
      ? "stroke-emerald-500 text-emerald-700"
      : h.overall_health_score >= 60
      ? "stroke-amber-500 text-amber-700"
      : "stroke-rose-500 text-rose-700";

  return (
    <section className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl p-6 shadow-sm flex flex-col justify-between">
      <div>
        <p className="eyebrow">PIPELINE HEALTH</p>
        <div className="mt-4 flex items-center gap-4">
          <div className="relative w-16 h-16 flex items-center justify-center shrink-0">
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
            <span className={`absolute text-sm font-extrabold ${scoreColor}`}>
              {h.overall_health_score}
            </span>
          </div>

          <div>
            <span className="text-4xl font-extrabold text-[#3D1534] tracking-tight">
              {h.overall_health_score}
            </span>
            <span className="text-sm font-bold text-[#3D1534]/60 ml-1">/ 100</span>
            <p className={`mt-1 text-xs font-extrabold tracking-wider uppercase ${
              h.status === "HEALTHY" ? "text-emerald-700" : "text-rose-700"
            }`}>
              {h.status.replaceAll("_", " ")}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-2 border-t border-[#A6BCC9]/40 pt-4 text-xs font-bold text-[#3D1534]">
        <Stat value={h.total_records_scanned} label="Records Scanned" />
        <Stat value={run.issues.length} label="DQ Issues" />
        <Stat value={run.root_cause_analysis.blast_radius} label="Blast Radius" />
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: string | number; label: string }) {
  return (
    <div>
      <div className="font-extrabold text-[#3D1534]">{value}</div>
      <div className="mt-0.5 text-[10px] text-[#3D1534]/60 font-bold uppercase">{label}</div>
    </div>
  );
}

{/* Phase 1 & 2: High Contrast Action Pills and Icon Consistency */}
function Issues({
  run,
  openIssue,
  compact = false,
}: {
  run: RunData;
  openIssue: (i: Issue) => void;
  compact?: boolean;
}) {
  if (!run.issues.length)
    return (
      <section className="bg-white border-2 border-emerald-400 rounded-2xl p-6 shadow-sm">
        <CheckCircle2 className="w-8 h-8 text-emerald-600 mb-2" />
        <p className="eyebrow text-emerald-800">NO ISSUES DETECTED</p>
        <h2 className="mt-1 text-base font-extrabold text-[#3D1534]">
          Your dataset passed all configured schema and value checks.
        </h2>
      </section>
    );

  const shown = compact ? run.issues.slice(0, 4) : run.issues;

  return (
    <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl overflow-hidden shadow-sm">
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex items-center justify-between">
        <div>
          <p className="eyebrow text-[#A6BCC9]">{compact ? "ISSUE SUMMARY" : "DETECTED ISSUES"}</p>
          <h2 className="text-base font-extrabold text-[#FFF4EB] mt-0.5">
            {compact ? "What Needs Attention" : "All Detected Data-Quality Issues"}
          </h2>
        </div>
        {compact && (
          <span className="text-xs text-[#A6BCC9] font-medium">Select an issue for evidence</span>
        )}
      </div>

      <div className="divide-y divide-[#A6BCC9]/30">
        {shown.map((i, index) => {
          const isHigh = i.severity === "HIGH";
          return (
            <button
              key={`${i.rule}-${i.column}-${index}`}
              onClick={() => openIssue(i)}
              className="flex w-full items-center gap-4 p-4 text-left hover:bg-[#F6E0B6]/30 transition-colors"
            >
              {/* Icon Consistency: AlertOctagon for HIGH, AlertTriangle for MEDIUM/LOW */}
              {isHigh ? (
                <AlertOctagon size={20} className="text-rose-600 shrink-0" />
              ) : (
                <AlertTriangle size={20} className="text-amber-600 shrink-0" />
              )}

              <div className="min-w-0 flex-1">
                <div className="font-extrabold text-sm text-[#3D1534]">{titleForIssue(i)}</div>
                <div className="mt-0.5 text-xs text-[#3D1534]/70 font-medium">
                  {i.count} affected rows · {pct(i.count, run.pipeline_health.total_records_scanned)} · Field: {i.column ?? "row-level"}
                </div>
              </div>

              {/* High-Contrast Action Pill (Phase 1 Fix: WCAG AA contrast) */}
              <span
                className={`px-3 py-1 text-xs font-extrabold rounded-full border shadow-sm ${
                  isHigh
                    ? "bg-rose-100 text-rose-900 border-rose-300"
                    : "bg-[#F6E0B6] text-[#3D1534] border-[#E4CA97]"
                }`}
              >
                {i.severity} SEVERITY
              </span>
              <ArrowRight size={16} className="text-[#3E4B8E] shrink-0" />
            </button>
          );
        })}
      </div>
    </section>
  );
}

{/* Phase 1: Run ID Truncation, Copy Button, and Correct Workflow/Status Labeling */}
function Details({ run }: { run: RunData }) {
  const [copied, setCopied] = useState(false);
  const truncatedId = run.run_id ? `${run.run_id.slice(0, 8)}...` : "Unavailable";

  const handleCopyId = () => {
    if (run.run_id) {
      navigator.clipboard.writeText(run.run_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl p-6 shadow-sm">
        <p className="eyebrow mb-3">PIPELINE RUN DETAILS</p>
        <dl className="grid gap-5 text-sm sm:grid-cols-2 md:grid-cols-3">
          {/* Truncated Run ID with copy button */}
          <div>
            <dt className="eyebrow">Run ID</dt>
            <dd className="mt-1 flex items-center gap-2 font-mono font-bold text-[#3D1534]">
              <span title={run.run_id}>{truncatedId}</span>
              <button
                onClick={handleCopyId}
                className="p-1 rounded bg-[#F6E0B6] hover:bg-[#FFF4EB] border border-[#E4CA97] text-[#3D1534] transition-all"
                title="Copy Full Run ID"
              >
                {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
              </button>
            </dd>
          </div>

          {/* Workflow Name */}
          <D label="Workflow Name" value={run.pipeline_name ?? "ObsidianDQ"} />

          {/* Execution Status */}
          <D label="Execution Status" value={run.pipeline_status ?? run.workflow_status} />

          <D label="Duration" value={duration(run.pipeline_health.execution_duration_ms)} />
          <D label="Dataset File" value={run.data_snapshot.file_name ?? "stg_orders.parquet"} />
          <D label="Guardrails Action" value={run.guardrails.action ?? "PASS"} />
        </dl>
      </section>

      <Sql run={run} />
      <TechnicalTrace run={run} />
    </div>
  );
}

function D({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="eyebrow">{label}</dt>
      <dd className="mt-1 font-extrabold text-[#3D1534] text-sm break-all">{value}</dd>
    </div>
  );
}

function Sql({ run }: { run: RunData }) {
  const s = run.sql_diagnostics;
  if (!s.sql_healing_ran && !s.original_sql)
    return (
      <Unavailable
        title="SQL diagnostics unavailable"
        detail="SQL normalization has not run; it is performed after approval."
      />
    );

  return (
    <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl overflow-hidden shadow-sm">
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex items-center justify-between">
        <div>
          <p className="eyebrow text-[#A6BCC9]">SQL DIAGNOSTICS</p>
          <h2 className="text-base font-extrabold text-[#FFF4EB] mt-0.5">
            {s.sql_healing_ran ? "AST SQL Normalization & Healing" : "Awaiting Approval"}
          </h2>
        </div>
      </div>
      <div className="grid divide-y divide-[#A6BCC9] lg:grid-cols-2 lg:divide-x lg:divide-y-0 bg-[#FFF4EB]">
        <pre className="overflow-auto p-5 text-xs font-mono text-[#3D1534] leading-relaxed">
          <code>{s.original_sql || "Original SQL not available before approval."}</code>
        </pre>
        <pre className="overflow-auto p-5 text-xs font-mono font-bold text-emerald-900 bg-emerald-50/60 leading-relaxed">
          <code>{s.repaired_sql || "Normalized SQL will appear after approval."}</code>
        </pre>
      </div>
    </section>
  );
}
