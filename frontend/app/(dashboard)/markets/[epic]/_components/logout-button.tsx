"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { logout } from "@/lib/api/auth";

export function LogoutButton() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    if (isLoading) {
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await logout();
      router.push("/login");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to close session");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      {error ? (
        <span className="font-mono text-[10px] uppercase tracking-wide text-danger">
          {error}
        </span>
      ) : null}
      <button
        type="button"
        onClick={handleLogout}
        disabled={isLoading}
        className="rounded-sm border border-border bg-surface-strong px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-gray-200 transition hover:border-white/35 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? "Closing..." : "Logout"}
      </button>
    </div>
  );
}
