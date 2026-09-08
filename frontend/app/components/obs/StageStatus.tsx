import React from "react";
import { clsx } from "clsx";
import { Tone, toneOf } from "./tone";

/** Single status row: status dot + label + optional detail + trailing meta. Use inside lists/stages. */
export function StageStatus({
  label,
  tone = "muted",
  detail,
  meta,
  pulse = false,
}: {
  label: string;
  tone?: Tone;
  detail?: string;
  meta?: React.ReactNode;
  pulse?: boolean;
}) {
  const t = toneOf(tone);
  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <span className={clsx("h-2 w-2 rounded-full shrink-0", t.dot, pulse && "animate-pulse")} />
      <span className={clsx("text-xs font-bold min-w-0 truncate", t.text)}>{label}</span>
      {detail && <span className="obs-sub min-w-0 truncate">· {detail}</span>}
      {meta && <span className="obs-sub shrink-0 ml-auto">{meta}</span>}
    </div>
  );
}