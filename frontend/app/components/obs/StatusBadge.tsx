import React from "react";
import { clsx } from "clsx";
import { Tone, toneOf } from "./tone";

/** Compact operational status pill. Use for healthy/warning/critical/active/blocked states. */
export function StatusBadge({
  tone = "muted",
  dot = true,
  pulse = false,
  label,
  children,
  className,
}: {
  tone?: Tone;
  dot?: boolean;
  pulse?: boolean;
  label?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const t = toneOf(tone);
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-bold leading-none",
        t.bg,
        t.text,
        t.border,
        className
      )}
    >
      {dot && <span className={clsx("h-1.5 w-1.5 rounded-full", t.dot, pulse && "animate-pulse")} />}
      {label ?? children}
    </span>
  );
}