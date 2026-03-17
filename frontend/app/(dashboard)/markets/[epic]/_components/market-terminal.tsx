"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getMarketDetails, type MarketDetailsResponse } from "@/lib/api/market-data";

import { MarketChartCard } from "./market-chart-card";
import { LogoutButton } from "./logout-button";

type WatchlistItem = {
  epic: string;
};

type WatchlistMarket = WatchlistItem & {
  detail: MarketDetailsResponse | null;
};

const watchlist: WatchlistItem[] = [
  {
    epic: "CS.D.EURUSD.CFD.IP",
  },
  {
    epic: "CS.D.GBPUSD.CFD.IP",
  },
  {
    epic: "IX.D.DAX.IFD.IP",
  },
  {
    epic: "CS.D.GOLD.CFD.IP",
  },
];

export function MarketTerminal({ epic }: { epic: string }) {
  const [marketDetails, setMarketDetails] = useState<Record<string, MarketDetailsResponse | null>>({});

  useEffect(() => {
    let cancelled = false;

    async function loadWatchlistDetails() {
      const results = await Promise.all(
        watchlist.map(async (item) => {
          try {
            const detail = await getMarketDetails(item.epic);
            return [item.epic, detail] as const;
          } catch {
            return [item.epic, null] as const;
          }
        }),
      );

      if (cancelled) {
        return;
      }

      setMarketDetails(Object.fromEntries(results));
    }

    void loadWatchlistDetails();

    return () => {
      cancelled = true;
    };
  }, []);

  const watchlistMarkets = useMemo<WatchlistMarket[]>(() => {
    return watchlist.map((item) => ({
      ...item,
      detail: marketDetails[item.epic] ?? null,
    }));
  }, [marketDetails]);

  const currentAsset = watchlistMarkets.find((item) => item.epic === epic) ?? {
    epic,
    detail: null,
  };

  const percentageChange = currentAsset.detail?.percentage_change ?? null;
  const isPositive = percentageChange == null ? false : percentageChange >= 0;

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background text-foreground">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/60 bg-surface px-4 shadow-sm">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-sm bg-accent shadow-[0_0_15px_rgba(255,255,255,0.4)]" />
            <span className="font-sans text-lg font-bold tracking-widest text-white">
              PUET<span className="text-gray-400">TRADE</span>
            </span>
          </div>
          <nav className="hidden space-x-1 md:flex">
            {['Trade', 'Markets', 'Portfolio', 'Analytics'].map((item, index) => (
              <button
                key={item}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${index === 0 ? 'bg-white/10 text-white' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
              >
                {item}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-full border border-border bg-surface-strong px-3 py-1">
            <div className="h-2 w-2 animate-pulse rounded-full bg-accent" />
            <span className="font-mono text-xs font-medium uppercase tracking-wider text-white">
              Live Preview
            </span>
          </div>
          <LogoutButton />
          <div className="h-8 w-8 rounded-full border border-border bg-surface-muted" />
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="flex w-[280px] shrink-0 flex-col border-r border-border/60 bg-surface-strong">
          <div className="flex items-center justify-between border-b border-border/60 p-3">
            <h2 className="font-sans text-xs font-bold uppercase tracking-widest text-gray-400">
              Watchlist
            </h2>
            <button className="text-gray-400 hover:text-white">+</button>
          </div>

          <div className="flex-1 space-y-1 overflow-y-auto p-2">
            {watchlistMarkets.map((item) => {
              const active = item.epic === epic;
              const instrumentName = item.detail?.instrument_name || formatInstrumentName(item.epic);
              const instrumentType = item.detail?.instrument_type || "";
              const itemPositive = (item.detail?.percentage_change ?? 0) >= 0;

              return (
                <Link
                  key={item.epic}
                  href={`/markets/${encodeURIComponent(item.epic)}`}
                  className={`group relative flex items-center justify-between rounded-lg border px-3 py-2.5 transition-all ${
                    active
                      ? 'border-accent/30 bg-white/5 shadow-[inset_0_0_20px_rgba(255,255,255,0.02)]'
                      : 'border-transparent hover:bg-white/5'
                  }`}
                >
                  {active ? (
                    <div className="absolute left-0 top-1/2 h-1/2 w-1 -translate-y-1/2 rounded-r-md bg-accent" />
                  ) : null}
                  <div className="flex flex-col">
                    <span className={`font-sans text-sm font-semibold ${active ? 'text-white' : 'text-gray-300'}`}>
                      {instrumentName}
                    </span>
                    <span className="font-mono text-[10px] text-gray-500">
                      {item.epic.split(".")[2] || item.epic}
                    </span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className={`font-mono text-xs font-bold ${itemPositive ? 'text-trade-up' : 'text-trade-down'}`}>
                      {formatPercentage(item.detail?.percentage_change)}
                    </span>
                    <span className="font-mono text-[10px] text-gray-500">
                      {instrumentTypeLabel(instrumentType)}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col bg-background">
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-border/60 bg-surface/50 px-4 backdrop-blur-md">
            <div className="flex items-center gap-4">
              <h1 className="font-sans text-xl font-bold text-white">
                {currentAsset.detail?.instrument_name || formatInstrumentName(currentAsset.epic)}
              </h1>
              <span className="font-mono text-sm text-gray-400">{epic}</span>
              <div
                className={`flex items-center gap-1 rounded bg-surface px-2 py-0.5 font-mono text-sm font-bold ${
                  percentageChange == null ? 'text-gray-400' : isPositive ? 'text-trade-up' : 'text-trade-down'
                }`}
              >
                {percentageChange == null ? '—' : `${isPositive ? '▲' : '▼'} ${formatPercentage(percentageChange)}`}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <StatItem label="24h High" value={formatPrice(currentAsset.detail?.high)} />
              <div className="h-4 w-px bg-border/80" />
              <StatItem label="24h Low" value={formatPrice(currentAsset.detail?.low)} />
              <div className="h-4 w-px bg-border/80" />
              <StatItem label="Net" value={formatSignedChange(currentAsset.detail?.net_change)} />
            </div>
          </div>

          <div className="flex-1 p-1">
            <MarketChartCard epic={epic} />
          </div>
        </main>
      </div>
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-end">
      <span className="font-sans text-[10px] uppercase tracking-wider text-gray-500">
        {label}
      </span>
      <span className="font-mono text-xs font-medium text-gray-300">{value}</span>
    </div>
  );
}

function formatPercentage(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }

  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value).toFixed(2)}%`;
}

function formatSignedChange(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }

  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value).toFixed(2)}`;
}

function formatPrice(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }

  return value >= 100 ? value.toFixed(1) : value.toFixed(5);
}

function instrumentTypeLabel(value: string): string {
  switch (value) {
    case "CURRENCIES":
      return "Forex";
    case "INDICES":
      return "Index";
    case "COMMODITIES":
      return "Commodity";
    default:
      return value || "Unknown";
  }
}

function formatInstrumentName(epic: string): string {
  const code = epic.split(".")[2] || epic;

  if (code.endsWith("USD") && code.length === 6) {
    return `${code.slice(0, 3)}/${code.slice(3)}`;
  }

  return code.replaceAll("_", " ");
}
