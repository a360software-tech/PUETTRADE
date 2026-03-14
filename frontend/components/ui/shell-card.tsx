import type { ReactNode } from "react";

export function ShellCard({ children }: { children: ReactNode }) {
  return <div className="rounded-[28px] border border-border bg-surface p-5 shadow-soft">{children}</div>;
}
