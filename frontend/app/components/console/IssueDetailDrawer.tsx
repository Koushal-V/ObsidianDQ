"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ShieldAlert, X } from "lucide-react";
import { Issue, RunData, pct, titleForIssue } from "@/app/lib/runState";
import { DetailPanel, Metric, StatusBadge } from "@/app/components/obs";

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
            className="fixed inset-0 z-40 bg-[#3D1534]/50"
            onClick={close}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            className="fixed inset-y-0 right-0 z-50 w-full max-w-xl overflow-y-auto border-l border-[#A6BCC9] bg-[#FFF4EB]"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 280 }}
          >
            <div className="px-4 py-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="obs-label">Issue details</div>
                  <h2 className="obs-page-title mt-1">{titleForIssue(issue)}</h2>
                </div>
                <button
                  onClick={close}
                  aria-label="Close"
                  className="rounded-md p-1.5 text-[#3D1534] transition-colors hover:bg-[#F6E0B6]/50"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <Metric label="Severity" value={issue.severity} tone={issue.severity === "HIGH" ? "critical" : "warning"} />
                <Metric label="Affected count" value={`${issue.count} rows`} />
                <Metric label="Share of records" value={pct(issue.count, run.pipeline_health.total_records_scanned)} />
              </div>

              <DetailPanel
                eyebrow="Rule"
                title="Violation evidence"
                meta={<StatusBadge tone={issue.severity === "HIGH" ? "critical" : "warning"} label={issue.severity} dot={false} />}
              >
                <ul className="space-y-2.5 text-[13px] text-[#3D1534]">
                  <li className="flex items-center gap-2">
                    <ShieldAlert size={15} className="shrink-0 text-rose-600" />
                    <span>
                      {issue.count} records violate <span className="obs-kbd">{issue.rule}</span>
                    </span>
                  </li>
                  <li>
                    Target column: <span className="obs-kbd">{issue.column ?? "whole row"}</span>
                  </li>
                  <li>
                    Blast radius: <span className="font-semibold text-rose-700">{run.root_cause_analysis.blast_radius}</span>
                  </li>
                </ul>
              </DetailPanel>

              <DetailPanel eyebrow="Sample" title="Offending rows" className="mt-4">
                {records.length ? (
                  <pre className="obs-monoblock">
                    <code>{JSON.stringify(records, null, 2)}</code>
                  </pre>
                ) : (
                  <p className="obs-sub">No matching rows are present in the available preview.</p>
                )}
              </DetailPanel>

              <DetailPanel eyebrow="AI triage" title="Recommendation" className="mt-4">
                <p className="obs-lede">
                  {run.root_cause_analysis.agent_proposed_actions.find((p) => p.issue_id.includes(issue.rule))?.reasoning ??
                    "No AI recommendation was returned for this issue."}
                </p>
              </DetailPanel>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}