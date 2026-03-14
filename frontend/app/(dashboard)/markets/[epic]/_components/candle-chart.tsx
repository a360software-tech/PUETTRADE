"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { Candle } from "@/types/market-data";

type CandleChartProps = {
  candles: Candle[];
  loading: boolean;
};

export function CandleChart({ candles, loading }: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#0b1220" },
        textColor: "rgba(247, 243, 235, 0.72)",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.06)" },
        horzLines: { color: "rgba(255, 255, 255, 0.06)" },
      },
      crosshair: {
        vertLine: { color: "rgba(15, 118, 110, 0.4)" },
        horzLine: { color: "rgba(15, 118, 110, 0.4)" },
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.12)",
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.12)",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#f97316",
      wickUpColor: "#10b981",
      wickDownColor: "#f97316",
      borderVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const resizeObserver = new ResizeObserver(() => {
      chart.timeScale().fitContent();
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) {
      return;
    }

    const data = candles
      .filter((candle) => Boolean(candle.time))
      .map((candle) => ({
        time: toUtcTimestamp(candle.time),
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }));

    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  return (
    <div className="relative h-[460px] w-full overflow-hidden rounded-[18px]">
      <div ref={containerRef} className="h-full w-full" />
      {loading ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[#0b1220]/70 backdrop-blur-sm">
          <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 font-mono text-xs uppercase tracking-[0.24em] text-white/60">
            loading candles
          </div>
        </div>
      ) : null}
    </div>
  );
}

function toUtcTimestamp(value: string): UTCTimestamp {
  const date = new Date(value);
  return Math.floor(date.getTime() / 1000) as UTCTimestamp;
}
