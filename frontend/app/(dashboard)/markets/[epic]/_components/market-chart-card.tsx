"use client";

import { useMemo, useState } from "react";

import { useCandles } from "../_hooks/use-candles";
import { CandleChart } from "./candle-chart";

const resolutions = ["MINUTE", "MINUTE_5", "HOUR", "DAY"] as const;

export function MarketChartCard({ epic }: { epic: string }) {
  const [resolution, setResolution] = useState<(typeof resolutions)[number]>("MINUTE");
  const { data, isLoading, error, isPreview } = useCandles({ epic, resolution, max: 200 });

  const latest = useMemo(() => data?.candles.at(-1), [data]);

  return (
    <section className="rounded-[30px] border border-border bg-panel text-panel-foreground shadow-panel">
      <div className="flex flex-col gap-4 border-b border-white/10 px-5 py-5 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.32em] text-white/45">Market Data</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h3 className="text-2xl font-semibold tracking-tight">Candles</h3>
            {isPreview ? (
              <span className="rounded-full bg-white/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.24em] text-[#f6c177]">
                preview fallback
              </span>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {resolutions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setResolution(item)}
              className={`rounded-full px-4 py-2 font-mono text-xs tracking-[0.24em] transition ${
                resolution === item
                  ? "bg-accent text-white"
                  : "bg-white/8 text-white/65 hover:bg-white/12 hover:text-white"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_290px]">
        <div className="overflow-hidden rounded-[24px] border border-white/10 bg-[#0b1220] p-3">
          <CandleChart candles={data?.candles ?? []} loading={isLoading} />
        </div>

        <aside className="space-y-4">
          <Metric label="Resolution" value={resolution} />
          <Metric label="Candles" value={String(data?.candles.length ?? 0)} />
          <Metric label="Last close" value={latest ? latest.close.toFixed(5) : "-"} />
          <Metric label="Allowance" value={formatAllowance(data?.allowance_remaining, data?.allowance_total)} />

          {error ? (
            <div className="rounded-3xl border border-[#f6c177]/30 bg-[#f6c177]/10 p-4 text-sm leading-6 text-[#fde8cf]">
              <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#f6c177]">Backend notice</p>
              <p className="mt-2">{error}</p>
            </div>
          ) : (
            <div className="rounded-3xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-white/72">
              <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-white/45">Ready for next step</p>
              <p className="mt-2">
                Cuando conectemos login real desde el frontend, esta misma vista podra leer velas live desde la sesion
                activa del backend sin cambiar el contrato del chart.
              </p>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 px-4 py-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-white/45">{label}</p>
      <p className="mt-3 text-lg font-medium text-white">{value}</p>
    </div>
  );
}

function formatAllowance(remaining?: number | null, total?: number | null) {
  if (remaining == null || total == null) {
    return "-";
  }

  return `${remaining} / ${total}`;
}
