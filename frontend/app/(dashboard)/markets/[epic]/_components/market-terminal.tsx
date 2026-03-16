import Link from "next/link";

import { MarketChartCard } from "./market-chart-card";
import { LogoutButton } from "./logout-button";

const watchlist = [
  {
    epic: "CS.D.EURUSD.CFD.IP",
    name: "EUR/USD",
    type: "Forex",
    change: "+0.12%",
  },
  {
    epic: "CS.D.GBPUSD.CFD.IP",
    name: "GBP/USD",
    type: "Forex",
    change: "-0.04%",
  },
  {
    epic: "IX.D.DAX.IFD.IP",
    name: "Germany 40",
    type: "Index",
    change: "+0.85%",
  },
  {
    epic: "CS.D.GOLD.CFD.IP",
    name: "Spot Gold",
    type: "Commodity",
    change: "+1.20%",
  },
];

export function MarketTerminal({ epic }: { epic: string }) {
  const currentAsset = watchlist.find((w) => w.epic === epic) || {
    name: epic,
    type: "Unknown",
    change: "0.00%",
  };
  const isPositive = currentAsset.change.startsWith("+");

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background text-foreground">
      {/* Top Navigation Bar */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/60 bg-surface px-4 shadow-sm">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-sm bg-accent shadow-[0_0_15px_rgba(255,255,255,0.4)]" />
            <span className="font-sans text-lg font-bold tracking-widest text-white">
              PUET<span className="text-gray-400">TRADE</span>
            </span>
          </div>
          <nav className="hidden space-x-1 md:flex">
            {["Trade", "Markets", "Portfolio", "Analytics"].map((item, i) => (
              <button
                key={item}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${i === 0 ? "bg-white/10 text-white" : "text-gray-400 hover:bg-white/5 hover:text-white"}`}
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
          <div className="h-8 w-8 rounded-full bg-surface-muted border border-border" />
        </div>
      </header>

      {/* Main Terminal Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Watchlist */}
        <aside className="flex w-[280px] shrink-0 flex-col border-r border-border/60 bg-surface-strong">
          <div className="flex items-center justify-between border-b border-border/60 p-3">
            <h2 className="font-sans text-xs font-bold uppercase tracking-widest text-gray-400">
              Watchlist
            </h2>
            <button className="text-gray-400 hover:text-white">+</button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {watchlist.map((item) => {
              const active = item.epic === epic;
              const itemPositive = item.change.startsWith("+");

              return (
                <Link
                  key={item.epic}
                  href={`/markets/${encodeURIComponent(item.epic)}`}
                  className={`group relative flex items-center justify-between rounded-lg border px-3 py-2.5 transition-all ${
                    active
                      ? "border-accent/30 bg-white/5 shadow-[inset_0_0_20px_rgba(255,255,255,0.02)]"
                      : "border-transparent hover:bg-white/5"
                  }`}
                >
                  {active && (
                    <div className="absolute left-0 top-1/2 h-1/2 w-1 -translate-y-1/2 rounded-r-md bg-accent" />
                  )}
                  <div className="flex flex-col">
                    <span
                      className={`font-sans text-sm font-semibold ${active ? "text-white" : "text-gray-300"}`}
                    >
                      {item.name}
                    </span>
                    <span className="font-mono text-[10px] text-gray-500">
                      {item.epic.split(".")[2] || item.epic}
                    </span>
                  </div>
                  <div className="flex flex-col items-end">
                    <span
                      className={`font-mono text-xs font-bold ${itemPositive ? "text-trade-up" : "text-trade-down"}`}
                    >
                      {item.change}
                    </span>
                    <span className="font-mono text-[10px] text-gray-500">
                      {item.type}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </aside>

        {/* Center - Chart Area */}
        <main className="flex min-w-0 flex-1 flex-col bg-background">
          {/* Asset Header */}
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-border/60 px-4 bg-surface/50 backdrop-blur-md">
            <div className="flex items-center gap-4">
              <h1 className="font-sans text-xl font-bold text-white">
                {currentAsset.name}
              </h1>
              <span className="font-mono text-sm text-gray-400">{epic}</span>
              <div
                className={`flex items-center gap-1 rounded bg-surface px-2 py-0.5 font-mono text-sm font-bold ${isPositive ? "text-trade-up" : "text-trade-down"}`}
              >
                {isPositive ? "▲" : "▼"} {currentAsset.change}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <StatItem label="24h High" value="-" />
              <div className="h-4 w-px bg-border/80" />
              <StatItem label="24h Low" value="-" />
              <div className="h-4 w-px bg-border/80" />
              <StatItem label="Vol" value="-" />
            </div>
          </div>

          {/* Chart Wrapper */}
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
      <span className="font-mono text-xs font-medium text-gray-300">
        {value}
      </span>
    </div>
  );
}
