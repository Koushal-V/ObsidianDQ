"use client";
import { Activity, Database, FileSearch, GitBranch, ListChecks, PlayCircle, ShieldCheck } from "lucide-react";
import { clsx } from "clsx";
import { PresentState } from "@/app/lib/runState";
import { StatusBadge, Tooltip, type Tone } from "@/app/components/obs";

const items = [
  ["overview", "Overview", Activity],
  ["issues", "Issues", ListChecks],
  ["lineage", "Lineage", GitBranch],
  ["data", "Data", Database],
  ["actions", "Actions", ShieldCheck],
  ["details", "Run details", FileSearch],
] as const;

const STATE_TONE: Record<PresentState, Tone> = {
  HEALTHY: "healthy",
  COMPLETED: "healthy",
  REVIEW_REQUIRED: "warning",
  ANALYZING: "active",
  BLOCKED: "blocked",
  FAILED: "critical",
};

export function AppShell({
  active,
  onNavigate,
  state,
  children,
  apiOnline,
  llmAvailable,
  llmProvider,
  agentExecution,
}: {
  active: string;
  onNavigate: (id: string) => void;
  state: PresentState;
  children: React.ReactNode;
  apiOnline: boolean;
  llmAvailable: boolean | null;
  llmProvider: string | null;
  agentExecution?: { mode: string; llm_used: boolean; fallback_used: boolean };
}) {
  void llmAvailable;
  return (
    <div className="flex min-h-screen flex-col bg-[#FFF4EB] text-[#3D1534]">
      {/* ── Top status bar ─────────────────────────────────────── */}
      <header className="flex h-12 items-center justify-between border-b border-[#2A0E24] bg-[#3D1534] px-4 text-[#FFF4EB] lg:px-6">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 place-items-center rounded-md bg-[#3E4B8E] text-sm font-black text-white">O</div>
          <div className="leading-tight">
            <div className="text-sm font-bold tracking-[.14em]">OBSIDIANDQ</div>
            <div className="text-[10px] font-medium uppercase tracking-[.12em] text-[#A6BCC9]">Data Observability</div>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <Tooltip label={apiOnline ? "Backend reachable on :8000" : "Backend unreachable on :8000"}>
            <span className={clsx("flex items-center gap-1.5 font-mono", apiOnline ? "text-emerald-300" : "text-rose-300")}>
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              API {apiOnline ? "ONLINE" : "OFFLINE"}
            </span>
          </Tooltip>
          {agentExecution && (
            <Tooltip label={agentExecution.llm_used ? "Reasoning delegated to the configured LLM." : "Deterministic fallback active."}>
              <span className={clsx("flex items-center gap-1.5 font-mono", agentExecution.llm_used ? "text-emerald-300" : "text-amber-300")}>
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                {agentExecution.llm_used ? "LLM AGENT" : "FALLBACK"}
              </span>
            </Tooltip>
          )}
          {llmProvider && <span className="hidden font-mono text-[#A6BCC9] lg:inline">LLM {llmProvider}</span>}
          <StatusBadge tone={STATE_TONE[state]} label={state.replaceAll("_", " ")} />
        </div>
      </header>

      <div className="flex">
        {/* ── Left rail navigation ─────────────────────────────── */}
        <aside className="sticky top-0 hidden h-[calc(100vh-3rem)] w-52 shrink-0 self-start border-r border-[#A6BCC9] bg-white lg:block">
          <div className="flex items-center gap-1.5 px-3 pt-4 text-[10px] font-bold uppercase tracking-widest text-[#5f7180]">
            <PlayCircle size={12} className="text-[#3E4B8E]" /> Current run
          </div>
          {items.map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className={clsx(
                "mb-0.5 flex w-full items-center gap-2.5 rounded-md border px-3 py-2 text-left text-sm transition-colors",
                active === id
                  ? "border-[#3E4B8E]/40 bg-[#3E4B8E]/10 text-[#3E4B8E]"
                  : "border-transparent text-[#3D1534] hover:bg-[#F6E0B6]/40"
              )}
            >
              <Icon size={15} className={active === id ? "text-[#3E4B8E]" : "text-[#5f7180]"} />
              {label}
            </button>
          ))}
          <p className="mt-6 border-t border-[#A6BCC9] px-3 pb-4 pt-3 text-xs leading-relaxed text-[#3D1534]/70">
            Agent proposals drive action; tools, guardrails and approval keep execution safe.
          </p>
        </aside>

        {/* ── Content region ───────────────────────────────────── */}
        <main className="min-w-0 flex-1 px-4 py-5 lg:px-6">{children}</main>
      </div>
    </div>
  );
}