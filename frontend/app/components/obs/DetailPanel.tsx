import React from "react";
import { clsx } from "clsx";

/** Framed panel with a labeled header band and a body. Use for technical detail sections. */
export function DetailPanel({
  eyebrow,
  title,
  meta,
  children,
  footer,
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  meta?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("obs-panel overflow-hidden", className)}>
      <header className="flex items-start justify-between gap-3 border-b border-[#A6BCC9]/30 px-3 py-2.5">
        <div className="min-w-0">
          {eyebrow && <div className="obs-label">{eyebrow}</div>}
          <h3 className={clsx("obs-section", eyebrow ? "mt-0.5" : "")}>{title}</h3>
        </div>
        <div className="obs-sub shrink-0">{meta}</div>
      </header>
      <div className="px-3 py-3">{children}</div>
      {footer && (
        <footer className="obs-divider px-3 py-2 text-xs text-[#3D1534]/60">{footer}</footer>
      )}
    </section>
  );
}