/* Semantic status tones.
   Color is reserved for operational meaning only — healthy, warning,
   critical, active, blocked, selected, muted — drawn from the existing
   ObsidianDQ palette + the Tailwind status colors already in the app. */

export type Tone =
  | "healthy"
  | "warning"
  | "critical"
  | "active"
  | "blocked"
  | "selected"
  | "muted";

export interface ToneSpec {
  label: string;
  text: string;
  bg: string;
  border: string;
  dot: string;
  ring: string;
}

export const TONES: Record<Tone, ToneSpec> = {
  healthy: { label: "Healthy", text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-300", dot: "bg-emerald-500", ring: "text-emerald-600" },
  warning: { label: "Warning", text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-300", dot: "bg-amber-500", ring: "text-amber-600" },
  critical: { label: "Critical", text: "text-rose-700", bg: "bg-rose-50", border: "border-rose-300", dot: "bg-rose-500", ring: "text-rose-600" },
  active: { label: "Active", text: "text-[#3E4B8E]", bg: "bg-[#3E4B8E]/10", border: "border-[#3E4B8E]/30", dot: "bg-[#3E4B8E]", ring: "text-[#3E4B8E]" },
  blocked: { label: "Blocked", text: "text-rose-800", bg: "bg-rose-100", border: "border-rose-300", dot: "bg-rose-600", ring: "text-rose-700" },
  selected: { label: "Selected", text: "text-[#3E4B8E]", bg: "bg-[#3E4B8E]/15", border: "border-[#3E4B8E]/40", dot: "bg-[#3E4B8E]", ring: "text-[#3E4B8E]" },
  muted: { label: "Muted", text: "text-[#5f7180]", bg: "bg-[#A6BCC9]/15", border: "border-[#A6BCC9]/40", dot: "bg-[#A6BCC9]", ring: "text-[#5f7180]" },
};

export function toneOf(tone: Tone | null | undefined): ToneSpec {
  return tone ? TONES[tone] : TONES.muted;
}

/** Map a 0..100 health score to an operational tone. */
export function scoreTone(score: number): Tone {
  if (score >= 80) return "healthy";
  if (score >= 60) return "warning";
  return "critical";
}