"use client";

import { RunData } from "@/app/lib/runState";
import { AlertTriangle } from "lucide-react";
import { DataTable, EmptyState, SectionHeader, StatusBadge, type Tone, type Column } from "@/app/components/obs";

type Row = Record<string, unknown>;

function invalid(value: unknown, column: string, run: RunData, duplicateOrderIds?: Set<string>): boolean {
  return run.issues.some(
    (issue) =>
      issue.column === column &&
      ((issue.rule === "NOT_NULL" && (value == null || value === "")) ||
        (issue.rule === "PRICE_NON_NEGATIVE" && Number(value) < 0) ||
        (issue.rule === "VALID_STATUS" && !["COMPLETED", "PENDING", "CANCELLED"].includes(String(value))) ||
        (issue.rule === "UNIQUE_ORDER_ID" && column === "order_id" && duplicateOrderIds?.has(String(value))))
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

  if (!s.available || !s.rows) {
    return (
      <EmptyState
        title="Data preview unavailable"
        detail={s.error ?? "The backend did not provide a readable dataset preview."}
      />
    );
  }

  const columns: Column<Row>[] = s.columns.map((c) => ({
    key: c,
    label: c,
    className: "font-mono whitespace-nowrap",
    tone: (row) => (invalid(row[c], c, run, duplicateOrderIds) ? "critical" : (null as Tone | null)),
    render: (row) => (row[c] != null && row[c] !== "" ? String(row[c]) : <span className="text-[#A6BCC9]">∅</span>),
  }));

  return (
    <div className="obs-panel overflow-hidden">
      <div className="border-b border-[#A6BCC9]/30 px-3 py-2.5">
        <SectionHeader
          eyebrow="Data snapshot"
          title={s.file_name ?? "Dataset"}
          meta={<span className="obs-mono">{s.row_count} rows × {s.column_count} columns</span>}
        />
      </div>

      {hasRowDuplicates && (
        <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
          <AlertTriangle size={14} className="shrink-0 text-amber-700" />
          Row-level anomaly: duplicate records detected across the dataset.
        </div>
      )}

      <DataTable columns={columns} rows={s.rows} rowKey={(_r, i) => String(i)} empty="No preview rows available." />
    </div>
  );
}

export function QualityTable({ run }: { run: RunData }) {
  const columns: Column<RunData["profiling_metrics"][number]>[] = [
    {
      key: "column",
      label: "Column",
      className: "font-mono",
      render: (m) => <span className="font-semibold text-[#3D1534]">{m.column_name}</span>,
    },
    {
      key: "complete",
      label: "Completeness",
      render: (m) => {
        const complete = 100 - m.null_percentage;
        return (
          <span className="inline-flex items-center gap-2 font-semibold text-[#3D1534]">
            <span className="h-1.5 w-24 overflow-hidden rounded-full bg-[#A6BCC9]/40">
              <span className={complete < 100 ? "bg-rose-500" : "bg-emerald-500"} style={{ width: `${complete}%` }} />
            </span>
            <span className="font-mono text-xs">{complete.toFixed(1)}%</span>
          </span>
        );
      },
    },
    { key: "distinct", label: "Distinct", align: "right", className: "font-mono", render: (m) => m.distinct_count },
    {
      key: "type",
      label: "Type",
      render: (m) => (
        <span className="rounded bg-[#3E4B8E]/10 px-2 py-0.5 font-mono text-[10.5px] font-semibold text-[#3E4B8E]">
          {m.data_type}
        </span>
      ),
    },
    {
      key: "status",
      label: "Expectation",
      align: "right",
      render: (m) => (
        <StatusBadge tone={m.status === "PASSED" ? "healthy" : "critical"} label={m.status === "PASSED" ? "PASSED" : "ATTENTION REQUIRED"} />
      ),
    },
  ];

  return (
    <div className="obs-panel overflow-hidden">
      <div className="border-b border-[#A6BCC9]/30 px-3 py-2.5">
        <SectionHeader eyebrow="Profiling" title="Column-level expectation checks" meta={`${run.profiling_metrics.length} columns`} />
      </div>
      <DataTable
        columns={columns}
        rows={run.profiling_metrics}
        rowKey={(m) => m.column_name}
        rowTone={(m) => (m.status === "PASSED" ? (null as Tone | null) : "critical")}
        empty="No profiling metrics returned."
      />
    </div>
  );
}

export function Unavailable({ title, detail }: { title: string; detail: string }) {
  return <EmptyState title={title} detail={detail} />;
}