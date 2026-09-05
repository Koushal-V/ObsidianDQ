"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X, AlertTriangle, ShieldAlert } from "lucide-react";
import { Issue, RunData, pct, titleForIssue } from "@/app/lib/runState";

export function IssueDetailDrawer({
  issue,
  run,
  close,
}: {
  issue: Issue | null;
  run: RunData;
  close: () => void;
}) {
  const records = run.data_snapshot.rows
    .filter((row) =>
      issue?.column
        ? issue.rule === "NOT_NULL"
          ? row[issue.column] == null
          : issue.rule === "PRICE_NON_NEGATIVE"
          ? Number(row[issue.column]) < 0
          : issue.rule === "VALID_STATUS"
          ? !["COMPLETED", "PENDING", "CANCELLED"].includes(String(row[issue.column]))
          : false
        : false
    )
    .slice(0, 5);

  return (
    <AnimatePresence>
      {issue && (
        <>
          <motion.button
            aria-label="Close issue details"
            className="fixed inset-0 z-40 bg-[#3D1534]/50 backdrop-blur-sm"
            onClick={close}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            className="fixed inset-y-0 right-0 z-50 w-full max-w-xl overflow-y-auto border-l-2 border-[#F6E0B6] bg-[#FFF4EB] p-6 shadow-2xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 280 }}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow text-[#3E4B8E]">ISSUE DETAILS</p>
                <h2 className="mt-2 text-2xl font-extrabold text-[#3D1534]">{titleForIssue(issue)}</h2>
              </div>
              <button
                aria-label="Close"
                onClick={close}
                className="rounded-xl p-2 text-[#3D1534] hover:bg-[#F6E0B6] transition-colors"
              >
                <X />
              </button>
            </div>

            <div className="mt-6 grid grid-cols-3 gap-3">
              <Metric label="Severity" value={issue.severity} />
              <Metric label="Affected Count" value={`${issue.count} rows`} />
              <Metric label="Share of Records" value={pct(issue.count, run.pipeline_health.total_records_scanned)} />
            </div>

            <section className="mt-6 rounded-2xl border-2 border-[#F6E0B6] bg-white p-5 shadow-sm">
              <h3 className="text-sm font-extrabold text-[#3D1534]">Rule Violation Evidence</h3>
              <ul className="mt-3 space-y-2.5 text-xs text-[#3D1534] font-medium">
                <li className="flex items-center gap-2">
                  <ShieldAlert size={16} className="shrink-0 text-rose-600" />
                  <span>
                    {issue.count} records violate rule{" "}
                    <code className="bg-[#3E4B8E] text-[#FFF4EB] px-2 py-0.5 rounded font-mono font-bold">
                      {issue.rule}
                    </code>
                  </span>
                </li>
                <li>
                  Target Column:{" "}
                  <code className="bg-[#F6E0B6] text-[#3D1534] px-2 py-0.5 rounded font-mono font-bold">
                    {issue.column ?? "whole row"}
                  </code>
                </li>
                <li>Blast Radius: <span className="font-bold text-rose-700">{run.root_cause_analysis.blast_radius}</span></li>
              </ul>
            </section>

            <section className="mt-5">
              <h3 className="text-sm font-extrabold text-[#3D1534]">Offending Sample Rows</h3>
              {records.length ? (
                <pre className="mt-3 overflow-x-auto rounded-2xl border-2 border-[#A6BCC9] bg-[#3D1534] p-4 text-xs font-mono text-[#FFF4EB] shadow-inner leading-relaxed">
                  <code>{JSON.stringify(records, null, 2)}</code>
                </pre>
              ) : (
                <p className="mt-2 text-xs text-[#3D1534]/70 font-medium">
                  No matching rows are present in the available preview.
                </p>
              )}
            </section>

            <section className="mt-5 rounded-2xl border-2 border-[#E4CA97] bg-[#F6E0B6] p-5 shadow-sm">
              <h3 className="text-sm font-extrabold text-[#3D1534]">AI Triage Recommendation</h3>
              <p className="mt-1.5 text-xs text-[#3D1534] font-medium leading-relaxed">
                {run.root_cause_analysis.agent_proposed_actions.find((p) => p.issue_id.includes(issue.rule))?.reasoning ??
                  "No AI recommendation was returned for this issue."}
              </p>
            </section>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[#A6BCC9] bg-[#F6E0B6]/40 p-3 shadow-sm">
      <div className="text-[10px] font-extrabold tracking-wider text-[#3D1534]/60 uppercase">{label}</div>
      <div className="mt-1 text-sm font-extrabold text-[#3D1534]">{value}</div>
    </div>
  );
}
