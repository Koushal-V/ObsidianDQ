import React from "react";
import { clsx } from "clsx";

/** Consistent panel/section header: optional eyebrow, semibold title, subtitle, trailing meta/actions. */
export function SectionHeader({
  eyebrow,
  title,
  subtitle,
  meta,
  action,
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  meta?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("flex items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        {eyebrow && <div className="obs-label">{eyebrow}</div>}
        <h2 className={clsx("obs-section", eyebrow ? "mt-0.5" : "")}>{title}</h2>
        {subtitle && <div className="obs-sub mt-0.5">{subtitle}</div>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {meta && <div className="obs-sub">{meta}</div>}
        {action}
      </div>
    </div>
  );
}