import React from "react";
import { clsx } from "clsx";
import { Tone, toneOf } from "./tone";

/** Muted, dashed empty/informational state with optional action. */
export function EmptyState({
  icon,
  title,
  detail,
  tone = "muted",
  action,
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  detail?: string;
  tone?: Tone;
  action?: React.ReactNode;
  className?: string;
}) {
  const t = toneOf(tone);
  return (
    <div className={clsx("flex flex-col items-start gap-2 rounded-md border border-dashed border-[#A6BCC9]/40 bg-[#FFF4EB] px-4 py-5", className)}>
      <div className="flex items-center gap-2">
        {icon && <span className={clsx(t.ring)}>{icon}</span>}
        <span className="obs-section">{title}</span>
      </div>
      {detail && <p className="obs-sub">{detail}</p>}
      {action}
    </div>
  );
}