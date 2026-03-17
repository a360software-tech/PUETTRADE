"use client";

import { useState } from "react";

import { useCandles } from "../_hooks/use-candles";
import { useCandleStream } from "../_hooks/use-candle-stream";
import { CandleChart } from "./candle-chart";

const resolutions = [
  { value: "MINUTE", label: "1m" },
  { value: "MINUTE_5", label: "5m" },
  { value: "HOUR", label: "1H" },
  { value: "DAY", label: "1D" },
] as const;

export function MarketChartCard({ epic }: { epic: string }) {
  const [resolution, setResolution] =
    useState<(typeof resolutions)[number]["value"]>("MINUTE");
  const { data, isLoading, error, isLiveOnly } = useCandles({
    epic,
    resolution,
    max: 200,
  });

  const {
    candles: streamingCandles,
    isStreaming,
    error: streamError,
  } = useCandleStream({
    epic,
    resolution,
    initialCandles: data?.candles ?? [],
  });

  const candles =
    streamingCandles.length > 0 ? streamingCandles : (data?.candles ?? []);
  const latest = candles.at(-1);

  return (
    <div className="flex h-full w-full flex-col">
      {/* Chart Toolbar */}
      <div className="flex items-center justify-between border-b border-border/40 px-2 py-1 bg-surface-strong/30">
        <div className="flex items-center gap-1">
          {resolutions.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setResolution(item.value)}
              className={`rounded px-2.5 py-1 font-mono text-xs font-medium transition ${
                resolution === item.value
                  ? "bg-accent text-accent-foreground"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              {item.label}
            </button>
          ))}
          <div className="ml-2 h-4 w-px bg-border/60" />
          <button className="px-2 text-xs text-gray-400 hover:text-white">
            Indicadores
          </button>
          <button className="px-2 text-xs text-gray-400 hover:text-white">
            Compare
          </button>
        </div>

        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex items-center gap-1.5 rounded-full border border-trade-up/30 bg-trade-up/10 px-2 py-0.5 font-mono text-[10px] uppercase text-trade-up">
              <span className="h-1.5 w-1.5 rounded-full bg-trade-up animate-pulse" />
              Live
            </span>
          )}
          {isLiveOnly && (
            <span className="flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] uppercase text-amber-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
              Solo en vivo
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Main Chart */}
        <div className="flex-1 border-r border-border/40 relative">
          <CandleChart
            candles={candles}
            loading={isLoading}
            emptyMessage={
              isLiveOnly
                ? "Datos históricos no disponibles. Esperando velas en vivo desde el stream de IG."
                : "Sin datos de velas disponibles aún."
            }
          />
        </div>

        {/* Right Panel - Order / Details */}
        <aside className="w-[300px] shrink-0 bg-surface flex flex-col">
          <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
            <span className="font-sans text-sm font-semibold">Libro de órdenes</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <span className="font-mono text-2xl font-bold text-white">
                {latest ? latest.close.toFixed(5) : "—"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button className="flex flex-col items-center justify-center rounded-sm bg-trade-up/10 border border-trade-up/30 py-3 transition hover:bg-trade-up/20">
                <span className="font-sans text-sm font-bold text-trade-up">
                  BUY
                </span>
              </button>
              <button className="flex flex-col items-center justify-center rounded-sm bg-trade-down/10 border border-trade-down/30 py-3 transition hover:bg-trade-down/20">
                <span className="font-sans text-sm font-bold text-trade-down">
                  SELL
                </span>
              </button>
            </div>

            <div className="mt-auto space-y-3">
              <div className="rounded-lg border border-border/40 bg-surface-strong p-3">
                <h4 className="font-sans text-xs font-semibold text-gray-400 mb-2">
                  Estadísticas
                </h4>
                <div className="space-y-2">
                  <div className="flex justify-between font-mono text-xs">
                    <span className="text-gray-500">Res</span>
                    <span className="text-white">{resolution}</span>
                  </div>
                  <div className="flex justify-between font-mono text-xs">
                    <span className="text-gray-500">Velas</span>
                    <span className="text-white">{candles.length}</span>
                  </div>
                  <div className="flex justify-between font-mono text-xs">
                    <span className="text-gray-500">Llamadas API</span>
                    <span className="text-white">
                      {formatAllowance(
                        data?.allowance_remaining,
                        data?.allowance_total,
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between font-mono text-xs">
                    <span className="text-gray-500">Stream</span>
                    <span
                      className={
                        isStreaming ? "text-trade-up" : "text-gray-500"
                      }
                    >
                      {isStreaming ? "Activo" : "Inactivo"}
                    </span>
                  </div>
                </div>
              </div>

              {(error || streamError) && (
                <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
                  <p className="font-semibold">Aviso de datos</p>
                  <p className="mt-1">{error || streamError}</p>
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function formatAllowance(remaining?: number | null, total?: number | null) {
  if (remaining == null || total == null) {
    return "-";
  }
  return `${remaining}/${total}`;
}
