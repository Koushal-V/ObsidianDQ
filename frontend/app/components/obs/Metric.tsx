import React from "react";
import { clsx } from "clsx";
import { Tone, toneOf } from "./tone";

/** Compact metric block: muted label on top, bold tabular value, optional hint. */
export function Metric({
  label,
  value,
  unit,
  hint,
  tone = "muted",
  icon,
  className,
}: {
  label: string;
  value: React.ReactNode;
  unit?: string;
  hint?: string;
  tone?: Tone;
  icon?: React.ReactNode;
  className?: string;
}) {
  const t = toneOf(tone);
  return (
    <div className={clsx("flex flex-col gap-1 rounded-md border border-[#A6BCC9]/35 bg-white px-3 py-2.5 min-w-0", className)}>
      <div className="flex items-center gap-1.5 obs-label">
        {icon && <span className={clsx("shrink-0", t.ring)}>{icon}</span>}
        <span className="truncate">{label}</span>
      </div>
      <div className={clsx("flex items-baseline gap-1.5 text-lg font-bold tabular-nums", t.text)}>
        <span className="truncate">{value}</span>
        {unit && <span className="text-xs font-semibold text-[#3D1534]/60">{unit}</span>}
      </div>
      {hint && <div className="obs-sub truncate">{hint}</div>}
    </div>
  );
}