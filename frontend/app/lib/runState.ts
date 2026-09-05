export type Severity = "HIGH" | "MEDIUM" | "LOW";

export type Issue = { rule: string; column: string | null; issue: string; count: number; severity: Severity };
export type RunData = {
  pipeline_health: { status: string; overall_health_score: number; total_records_scanned: number; execution_duration_ms: number; scanned_tables: string[] };
  lineage_graph: { nodes: { id: string; label: string; status: string }[]; edges: { source: string; target: string }[] };
  sql_diagnostics: { sql_healing_ran: boolean; has_error: boolean; original_sql: string; repaired_sql: string; tokens_replaced: { original_token: string; corrected_token: string; reason: string }[] };
  root_cause_analysis: { failing_table: string; root_cause_table: string; upstream_path: string[]; summary_explanation: string; severity_score: number; blast_radius: string; auto_quarantine_sql: string; agent_reasoning: Trace[]; agent_proposed_actions: Proposal[]; agent_tool_calls: ToolCall[]; requires_human_approval: boolean; route_taken: string[]; run_id: string; root_cause_evidence?: Record<string, unknown>[]; root_cause_reasoning?: string; upstream_causality_proven?: boolean; critic_verdict?: string; critic_reasoning?: string; critic_retry_count?: number };
  agent_execution?: { mode: string; llm_used: boolean; fallback_used: boolean; llm_agents: { root_cause: boolean; triage: boolean; critic: boolean } };
  profiling_metrics: { column_name: string; null_percentage: number; distinct_count: number; data_type: string; status: string }[];
  data_snapshot: { available: boolean; file_name?: string; row_count?: number; column_count?: number; columns: string[]; rows: Record<string, unknown>[]; error?: string };
  remediation: { actions?: { severity: string; rule: string; column: string | null; action: string; rows_affected: number }[]; quarantined_rows?: number; quarantine_file?: string | null };
  guardrails: { approved?: boolean; action?: string; errors?: string[]; warnings?: string[] };
  issues: Issue[]; run_id: string; requires_human_approval: boolean; route_taken: string[]; workflow_status: string; pipeline_name?: string; pipeline_status?: string;
};
export type Trace = { type: string; text: string; result?: unknown; debug_detail?: string };
export type ToolCall = { name: string; arguments: Record<string, unknown>; result: unknown };
export type Proposal = { issue_id: string; action: string; confidence: number; reasoning: string };

export type PresentState = "REVIEW_REQUIRED" | "COMPLETED" | "BLOCKED" | "HEALTHY" | "ANALYZING" | "FAILED";
export function presentState(run: Partial<RunData>): PresentState {
  if (run.workflow_status === "APPROVAL_REJECTED") return "BLOCKED";
  if (run.requires_human_approval) return "REVIEW_REQUIRED";
  if (run.workflow_status === "APPROVED" || run.remediation?.quarantine_file || run.guardrails?.approved) return "COMPLETED";
  if (run.pipeline_health?.status === "HEALTHY") return "HEALTHY";
  return "ANALYZING";
}
export const titleForIssue = (issue: Issue) => ({ NOT_NULL: `Missing ${issue.column?.replaceAll("_", " ") ?? "values"}`, PRICE_NON_NEGATIVE: "Negative prices", VALID_STATUS: "Invalid statuses", NO_DUPLICATES: "Duplicate rows", UNIQUE_ORDER_ID: "Duplicate order IDs" }[issue.rule] ?? issue.issue);
export const pct = (count: number, total: number) => total ? `${((count / total) * 100).toFixed(1)}%` : "Unavailable";
export const duration = (ms: number) => ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
