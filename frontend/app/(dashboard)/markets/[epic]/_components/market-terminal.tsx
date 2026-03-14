import Link from "next/link";

import { MarketChartCard } from "./market-chart-card";

const watchlist = [
  "CS.D.EURUSD.CFD.IP",
  "CS.D.GBPUSD.CFD.IP",
  "IX.D.DAX.IFD.IP",
  "CS.D.GOLD.CFD.IP",
];

export function MarketTerminal({ epic }: { epic: string }) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-6 md:px-6 lg:px-8">
      <section className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="rounded-[28px] border border-border bg-surface/80 p-5 shadow-soft backdrop-blur">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent">PUETTRADE</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight">Market Board</h1>
            </div>
            <div className="rounded-full bg-accent-soft px-3 py-1 font-mono text-xs text-accent-strong">
              preview
            </div>
          </div>

          <div className="space-y-3">
            <p className="font-mono text-xs uppercase tracking-[0.26em] text-foreground/55">Watchlist</p>
            <div className="space-y-2">
              {watchlist.map((item) => {
                const active = item === epic;

                return (
                  <Link
                    key={item}
                    href={`/markets/${encodeURIComponent(item)}`}
                    className={`block rounded-2xl border px-4 py-3 transition ${
                      active
                        ? "border-accent bg-accent text-white shadow-lg"
                        : "border-border bg-white/70 hover:border-accent/40 hover:bg-accent-soft/40"
                    }`}
                  >
                    <div className="font-mono text-[11px] uppercase tracking-[0.22em] opacity-75">Epic</div>
                    <div className="mt-1 break-all text-sm font-medium">{item}</div>
                  </Link>
                );
              })}
            </div>
          </div>
        </aside>

        <section className="flex flex-col gap-4">
          <div className="rounded-[28px] border border-border bg-surface p-5 shadow-soft">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent">Candlestick View</p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight">{epic}</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-foreground/70">
                  Vista inicial para explorar velas OHLC desde el backend. Si no existe sesion activa en FastAPI,
                  la pantalla entra en modo preview con datos simulados para trabajar la UI mientras llega el login.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
                <StatCard label="Source" value="FastAPI / IG" />
                <StatCard label="Chart" value="Candles" />
                <StatCard label="Mode" value="Preview ready" />
              </div>
            </div>
          </div>

          <MarketChartCard epic={epic} />
        </section>
      </section>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-white/70 px-4 py-3">
      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-foreground/55">{label}</p>
      <p className="mt-2 text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}
