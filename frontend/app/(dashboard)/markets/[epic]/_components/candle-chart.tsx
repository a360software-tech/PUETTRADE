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
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(237, 237, 237, 0.6)",
        attributionLogo: false,
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.05)" },
        horzLines: { color: "rgba(255, 255, 255, 0.05)" },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: "rgba(255, 255, 255, 0.4)", width: 1, style: 3, labelBackgroundColor: "#ffffff" },
        horzLine: { color: "rgba(255, 255, 255, 0.4)", width: 1, style: 3, labelBackgroundColor: "#ffffff" },
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.1)",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.1)",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#00e59b",
      downColor: "#ff3358",
      wickUpColor: "#00e59b",
      wickDownColor: "#ff3358",
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
    <div className="relative h-full w-full bg-background overflow-hidden">
      <div ref={containerRef} className="h-full w-full" />
      {loading ? (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
           <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-white" />
           <span className="mt-4 font-mono text-[10px] uppercase tracking-widest text-white">Loading Data</span>
        </div>
      ) : null}
    </div>
  );
}

function toUtcTimestamp(value: string): UTCTimestamp {
  const date = new Date(value);
  return Math.floor(date.getTime() / 1000) as UTCTimestamp;
}
