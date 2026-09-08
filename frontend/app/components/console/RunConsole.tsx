"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, ArrowRight, Check, CheckCircle2, Copy } from "lucide-react";
import { AppShell } from "./AppShell";
import { ApprovalGate, Recommendation, RunTimeline, TechnicalTrace } from "./ActionViews";
import { DataPreviewTable, QualityTable } from "./DataViews";
import { IssueDetailDrawer } from "./IssueDetailDrawer";
import { LineageView } from "./LineageView";
import { Issue, PresentState, Proposal, RunData, duration, pct, presentState, titleForIssue } from "@/app/lib/runState";
import { DataTable, DetailPanel, EmptyState, Metric, SectionHeader, StatusBadge, Tooltip, scoreTone, type Tone } from "@/app/components/obs";

const base = typeof window === "undefined" ? "http://localhost:8000" : `http://${window.location.hostname}:8000`;

const RUN_TONE: Record<PresentState, Tone> = {
  HEALTHY: "healthy",
  COMPLETED: "healthy",
  REVIEW_REQUIRED: "warning",
  ANALYZING: "active",
  BLOCKED: "blocked",
  FAILED: "critical",
};

const issueTone = (i: Issue): Tone => (i.severity === "HIGH" ? "critical" : "warning");

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
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}>
        {active === "overview" && <Overview run={run} openIssue={setIssue} navigate={setActive} onDecision={decide} busy={busy} />}
        {active === "issues" && <Issues run={run} openIssue={setIssue} />}
        {active === "lineage" && <LineageView run={run} />}
        {active === "data" && (
          <div className="space-y-5">
            <DataPreviewTable run={run} />
            <QualityTable run={run} />
          </div>
        )}
        {active === "actions" && (
          <div className="grid items-start gap-5 lg:grid-cols-2">
            <div className="space-y-4">
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
/* ── Overview ─────────────────────────────────────────────────── */
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
  const h = run.pipeline_health;
  const score = h.overall_health_score;
  const st = presentState(run);
  return (
    <div className="space-y-5">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="obs-label">Pipeline run</div>
          <h1 className="obs-page-title mt-1">{run.pipeline_name ?? "Data quality run"}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Tooltip label={run.run_id}>
            <span className="obs-mono">{run.run_id.slice(0, 8)}…</span>
          </Tooltip>
          <StatusBadge tone={RUN_TONE[st]} label={st.replaceAll("_", " ")} />
          <button className="obs-btn-primary" onClick={() => navigate("issues")}>
            Review issues <ArrowRight size={15} />
          </button>
          <button className="obs-btn-secondary" onClick={() => navigate("lineage")}>
            Lineage impact
          </button>
        </div>
      </div>

      {/* Key metrics strip */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Health score" value={score} unit="/ 100" tone={scoreTone(score)} />
        <Metric
          label="Records scanned"
          value={h.total_records_scanned.toLocaleString()}
          hint={h.scanned_tables.length ? h.scanned_tables.join(" · ") : undefined}
        />
        <Metric label="Data quality issues" value={run.issues.length} tone={run.issues.length ? "critical" : "healthy"} />
        <Metric
          label="Blast radius"
          value={run.root_cause_analysis.blast_radius}
          hint={`${run.root_cause_analysis.severity_score ?? "—"}/10 severity`}
          icon={<Activity size={15} />}
        />
      </div>

      {/* Summary */}
      <DetailPanel
        eyebrow="Summary"
        title={
          run.issues.length
            ? `${run.issues.length} data-quality issue${run.issues.length === 1 ? "" : "s"} in ${run.root_cause_analysis.failing_table}`
            : "No data-quality issues detected"
        }
        meta={<StatusBadge tone={RUN_TONE[st]} label={st.replaceAll("_", " ")} />}
      >
        <p className="obs-lede">{run.root_cause_analysis.summary_explanation}</p>
      </DetailPanel>

      <Issues run={run} openIssue={openIssue} compact />

      {/* Investigate & act */}
      <div className="grid items-start gap-5 lg:grid-cols-2">
        <LineageView run={run} />
        <div className="space-y-4">
          <Recommendation run={run} />
          <ApprovalGate run={run} onDecision={onDecision} busy={busy} />
        </div>
      </div>
    </div>
  );
}

/* ── Issues (DataTable) ───────────────────────────────────────── */
function Issues({ run, openIssue, compact = false }: { run: RunData; openIssue: (i: Issue) => void; compact?: boolean }) {
  if (!run.issues.length) {
    return (
      <EmptyState
        icon={<CheckCircle2 size={16} />}
        tone="healthy"
        title="No issues detected"
        detail="All configured schema and value checks passed."
      />
    );
  }

  const rows = compact ? run.issues.slice(0, 4) : run.issues;
  const columns = [
    {
      key: "issue",
      label: "Issue",
      render: (i: Issue) => (
        <div>
          <div className="text-[13px] font-bold text-[#3D1534]">{titleForIssue(i)}</div>
          <div className="obs-sub">
            {i.count} rows · {pct(i.count, run.pipeline_health.total_records_scanned)} · field {i.column ?? "row-level"}
          </div>
        </div>
      ),
    },
    {
      key: "rule",
      label: "Rule",
      render: (i: Issue) => <span className="obs-kbd">{i.rule}</span>,
    },
    {
      key: "severity",
      label: "Severity",
      align: "right" as const,
      render: (i: Issue) => <StatusBadge tone={issueTone(i)} label={i.severity} />,
    },
  ];

  return (
    <div className="obs-panel overflow-hidden">
      <div className="px-3 py-2.5">
        <SectionHeader
          eyebrow={compact ? "Issues summary" : "Issues"}
          title={compact ? "What needs attention" : "Detected data-quality issues"}
          meta={compact ? `${run.issues.length} total · select to inspect` : `${run.issues.length} total`}
        />
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(i) => `${i.rule}-${i.column}-${i.count}`}
        rowTone={issueTone}
        onRowClick={openIssue}
        empty="No issues to display."
      />
    </div>
  );
}
/* ── Details ──────────────────────────────────────────────────── */
function Details({ run }: { run: RunData }) {
  const [copied, setCopied] = useState(false);
  const truncatedId = run.run_id ? `${run.run_id.slice(0, 8)}...` : "Unavailable";

  const copyId = () => {
    if (!run.run_id) return;
    navigator.clipboard.writeText(run.run_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      <DetailPanel
        eyebrow="Pipeline run"
        title="Run details"
        meta={<span className="obs-mono">{run.run_id.slice(0, 8)}…</span>}
      >
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <D
            label="Run ID"
            value={
              <span className="inline-flex items-center gap-1.5 font-mono font-bold text-[#3D1534]">
                {truncatedId}
                <button
                  onClick={copyId}
                  className="rounded border border-[#E4CA97] bg-[#F6E0B6] p-0.5 text-[#3D1534] transition hover:bg-[#FFF4EB]"
                  aria-label="Copy full run ID"
                >
                  {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                </button>
              </span>
            }
          />
          <D label="Workflow" value={run.pipeline_name ?? "ObsidianDQ"} />
          <D label="Execution status" value={run.pipeline_status ?? run.workflow_status} />
          <D label="Duration" value={duration(run.pipeline_health.execution_duration_ms)} />
          <D label="Dataset" value={run.data_snapshot.file_name ?? "stg_orders.parquet"} />
          <D label="Guardrails" value={run.guardrails.action ?? "PASS"} />
        </dl>
      </DetailPanel>

      <Sql run={run} />
      <TechnicalTrace run={run} />
    </div>
  );
}

function D({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="obs-label">{label}</dt>
      <dd className="mt-1 truncate text-sm font-semibold text-[#3D1534]">{value}</dd>
    </div>
  );
}

function Sql({ run }: { run: RunData }) {
  const s = run.sql_diagnostics;
  if (!s.sql_healing_ran && !s.original_sql) {
    return <EmptyState title="SQL diagnostics unavailable" detail="SQL normalization runs after approval." />;
  }
  return (
    <DetailPanel
      eyebrow="SQL diagnostics"
      title={s.sql_healing_ran ? "AST normalization & healing" : "Awaiting approval"}
      meta={<StatusBadge tone={s.sql_healing_ran ? "healthy" : "warning"} label={s.sql_healing_ran ? "APPLIED" : "REVIEW"} />}
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="min-w-0">
          <div className="obs-label mb-1">Original</div>
          <pre className="obs-monoblock"><code>{s.original_sql || "Original SQL not available before approval."}</code></pre>
        </div>
        <div className="min-w-0">
          <div className="obs-label mb-1">Repaired</div>
          <pre className="obs-monoblock"><code>{s.repaired_sql || "Normalized SQL will appear after approval."}</code></pre>
        </div>
      </div>
    </DetailPanel>
  );
}