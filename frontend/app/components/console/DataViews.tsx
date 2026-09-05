"use client";

import { RunData } from "@/app/lib/runState";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

function invalid(value: unknown, column: string, run: RunData, duplicateOrderIds?: Set<string>) {
  return run.issues.some(
    (issue) =>
      issue.column === column &&
      ((issue.rule === "NOT_NULL" && (value == null || value === "")) ||
        (issue.rule === "PRICE_NON_NEGATIVE" && Number(value) < 0) ||
        (issue.rule === "VALID_STATUS" &&
          !["COMPLETED", "PENDING", "CANCELLED"].includes(String(value))) ||
        (issue.rule === "UNIQUE_ORDER_ID" &&
          column === "order_id" &&
          duplicateOrderIds?.has(String(value))))
  );
}

export function DataPreviewTable({ run }: { run: RunData }) {
  const s = run.data_snapshot;
  const hasRowDuplicates = run.issues.some((issue) => issue.rule === "NO_DUPLICATES");

  const duplicateOrderIds = new Set<string>();
  if (s.available && s.rows && run.issues.some((i) => i.rule === "UNIQUE_ORDER_ID")) {
    const counts = new Map<string, number>();
    for (const r of s.rows) {
      if (r.order_id != null) {
        const val = String(r.order_id);
        counts.set(val, (counts.get(val) ?? 0) + 1);
      }
    }
    counts.forEach((count, val) => {
      if (count > 1) duplicateOrderIds.add(val);
    });
  }

  if (!s.available)
    return (
      <Unavailable
        title="Data preview unavailable"
        detail={s.error ?? "The backend did not provide a readable dataset preview."}
      />
    );

  return (
    <section className="bg-white border-2 border-[#F6E0B6] rounded-2xl overflow-hidden shadow-sm">
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB] flex items-center justify-between">
        <div>
          <p className="eyebrow text-[#A6BCC9]">DATA SNAPSHOT</p>
          <h2 className="text-base font-extrabold text-[#FFF4EB] mt-0.5">{s.file_name ?? "Dataset"}</h2>
        </div>
        <span className="text-xs font-mono font-bold bg-[#F6E0B6] text-[#3D1534] px-3 py-1 rounded-full">
          {s.row_count} rows × {s.column_count} columns
        </span>
      </div>

      {hasRowDuplicates && (
        <div className="px-6 py-2.5 bg-amber-50 border-b border-amber-200 text-amber-900 text-xs font-bold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
          <span>Row-Level Anomaly: Duplicate records detected across dataset.</span>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-xs">
          <thead>
            <tr className="border-b border-[#A6BCC9] bg-[#FFF4EB] text-[10px] uppercase font-extrabold tracking-wider text-[#3D1534]">
              {s.columns.map((c) => (
                <th key={c} className="px-4 py-3 font-extrabold">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#A6BCC9]/30">
            {s.rows.map((row, i) => (
              <tr key={i} className="hover:bg-[#F6E0B6]/30 transition-colors">
                {s.columns.map((c) => {
                  const bad = invalid(row[c], c, run, duplicateOrderIds);
                  return (
                    <td
                      key={c}
                      className={`whitespace-nowrap px-4 py-3 font-mono text-xs transition-colors ${
                        bad
                          ? "bg-rose-100/90 text-rose-900 font-extrabold border-b border-rose-300"
                          : "text-[#3D1534] font-medium"
                      }`}
                    >
                      {row[c] == null ? "NULL" : String(row[c])}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function QualityTable({ run }: { run: RunData }) {
  return (
    <section className="bg-[#FFF4EB] border-2 border-[#F6E0B6] rounded-2xl overflow-hidden shadow-sm">
      <div className="px-6 py-4 bg-[#3D1534] text-[#FFF4EB]">
        <p className="eyebrow text-[#A6BCC9]">DATA QUALITY BREAKDOWN</p>
        <h2 className="text-base font-extrabold text-[#FFF4EB] mt-0.5">Column-Level Expectation Checks</h2>
      </div>

      <div className="overflow-x-auto p-4">
        <table className="w-full min-w-[640px] text-xs">
          <thead>
            <tr className="border-b border-[#A6BCC9] text-left text-[10px] uppercase font-extrabold tracking-wider text-[#3D1534]">
              <th className="px-4 py-3 font-extrabold">Column</th>
              <th className="px-4 py-3 font-extrabold">Completeness Ratio</th>
              <th className="px-4 py-3 font-extrabold">Distinct Count</th>
              <th className="px-4 py-3 font-extrabold">Data Type</th>
              <th className="px-4 py-3 font-extrabold">Expectation Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#A6BCC9]/30">
            {run.profiling_metrics.map((m) => {
              const complete = 100 - m.null_percentage;
              return (
                <tr key={m.column_name} className="hover:bg-white transition-colors">
                  <td className="px-4 py-3 font-mono font-extrabold text-[#3D1534]">
                    {m.column_name}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 font-bold text-[#3D1534]">
                      <div className="h-2 w-24 overflow-hidden rounded-full bg-[#A6BCC9]/40 border border-[#A6BCC9]">
                        <div
                          className={`h-full ${
                            complete < 100 ? "bg-rose-500" : "bg-emerald-500"
                          }`}
                          style={{ width: `${complete}%` }}
                        />
                      </div>
                      {complete.toFixed(1)}%
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono font-bold text-[#3D1534]">{m.distinct_count}</td>
                  <td className="px-4 py-3 font-mono">
                    <span className="px-2 py-0.5 rounded bg-[#3E4B8E] text-[#FFF4EB] font-bold text-[10px]">
                      {m.data_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {m.status === "PASSED" ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-extrabold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        PASSED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-extrabold rounded-full bg-rose-100 text-rose-800 border border-rose-300">
                        <XCircle className="w-3 h-3 text-rose-600" />
                        ATTENTION REQUIRED
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function Unavailable({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="bg-white border-2 border-rose-300 rounded-2xl p-6 shadow-sm">
      <p className="eyebrow text-rose-700">UNAVAILABLE</p>
      <h2 className="mt-1 text-lg font-extrabold text-[#3D1534]">{title}</h2>
      <p className="mt-2 text-sm text-[#3D1534]/70 font-medium">{detail}</p>
    </section>
  );
}
