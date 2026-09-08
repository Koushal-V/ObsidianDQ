import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import { clsx } from "clsx";

/** Collapsible technical section. Use to surface technical details on demand. */
export function ExpandableSection({
  title,
  eyebrow,
  subtitle,
  defaultOpen = false,
  badge,
  children,
  className,
}: {
  title: React.ReactNode;
  eyebrow?: string;
  subtitle?: string;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={clsx("obs-panel overflow-hidden", className)}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-[#F6E0B6]/30"
      >
        <div className="min-w-0 text-left">
          {eyebrow && <div className="obs-label">{eyebrow}</div>}
          <div className={clsx("obs-section", eyebrow ? "mt-0.5" : "")}>{title}</div>
          {subtitle && <div className="obs-sub mt-0.5">{subtitle}</div>}
        </div>
        <span className="flex items-center gap-2 shrink-0">
          {badge}
          <ChevronDown size={16} className={clsx("text-[#3E4B8E] transition-transform", open && "rotate-180")} />
        </span>
      </button>
      {open && <div className="border-t border-[#A6BCC9]/30 px-3 py-3">{children}</div>}
    </section>
  );
}