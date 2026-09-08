import React from "react";
import { clsx } from "clsx";
import { Tone, toneOf } from "./tone";

export type Align = "left" | "right" | "center";

export interface Column<T> {
  key: string;
  label: string;
  align?: Align;
  className?: string;
  headerClassName?: string;
  render: (row: T) => React.ReactNode;
  /** Per-cell operational tone. */
  tone?: (row: T) => Tone | null;
}

const alignClass: Record<Align, string> = { left: "text-left", right: "text-right", center: "text-center" };

/** Dense, information-first data table with subtle row separators and hover feedback. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  rowTone,
  empty,
  onRowClick,
  className,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
  /** Whole-row operational tone (shades the row). */
  rowTone?: (row: T) => Tone | null;
  empty?: string;
  onRowClick?: (row: T) => void;
  className?: string;
}) {
  if (!rows.length) {
    return empty ? (
      <div className="rounded-md border border-dashed border-[#A6BCC9]/40 bg-[#FFF4EB] px-3 py-6 text-xs text-[#3D1534]/60 text-center">
        {empty}
      </div>
    ) : null;
  }

  return (
    <div className={clsx("overflow-x-auto", className)}>
      <table className="obs-table min-w-full">
        <thead className="obs-thead">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={clsx("obs-th", alignClass[c.align ?? "left"], c.headerClassName)}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#A6BCC9]/15">
          {rows.map((row, i) => {
            const t = rowTone ? rowTone(row) : null;
            const spec = t ? toneOf(t) : null;
            return (
              <tr
                key={rowKey(row, i)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={clsx("obs-row", onRowClick && "cursor-pointer", spec && spec.bg)}
              >
                {columns.map((c) => {
                  const cellTone = c.tone ? c.tone(row) : null;
                  const textTone = cellTone
                    ? toneOf(cellTone).text
                    : spec
                    ? spec.text
                    : "";
                  return (
                    <td key={c.key} className={clsx("obs-td", alignClass[c.align ?? "left"], textTone, c.className)}>
                      {c.render(row)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}