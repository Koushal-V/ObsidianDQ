import React from "react";
import { clsx } from "clsx";
import { Tone, toneOf } from "./tone";

/** Vertical timeline step: toned node with a connector line to the next step. */
export function TimelineStep({
  index,
  label,
  tone = "muted",
  detail,
  meta,
  last = false,
  pulse = false,
}: {
  index?: number;
  label: string;
  tone?: Tone;
  detail?: string;
  meta?: React.ReactNode;
  last?: boolean;
  pulse?: boolean;
}) {
  const t = toneOf(tone);
  return (
    <div className="flex items-center gap-3">
      <div className="flex w-6 flex-col items-center shrink-0">
        <span
          className={clsx(
            "grid h-4 w-4 place-items-center rounded-full",
            t.dot,
            pulse && "animate-pulse"
          )}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-white" />
        </span>
        {!last && <span className={clsx("mt-0.5 h-px w-px flex-1", t.dot)} aria-hidden />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-xs font-bold min-w-0 truncate">
          <span className={tone === "muted" ? "" : t.text}>
            {index != null && <span className="text-[#3D1534]/45">{index}. </span>}
            <span>{label}</span>
          </span>
          {meta && <span className="obs-sub shrink-0 ml-auto">{meta}</span>}
        </div>
        {detail && <div className="obs-sub mt-0.5">{detail}</div>}
      </div>
    </div>
  );
}