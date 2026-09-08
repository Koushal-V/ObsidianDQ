import React from "react";
import { clsx } from "clsx";

/** CSS-driven tooltip shown on hover and focus. Wrap any trigger element. */
export function Tooltip({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx("obs-tip-wrap", className)}
      tabIndex={0}
      role="note"
      aria-label={label}
    >
      {children}
      <span className="obs-tip" role="tooltip">
        {label}
      </span>
    </span>
  );
}