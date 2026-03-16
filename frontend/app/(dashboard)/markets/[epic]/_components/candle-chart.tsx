"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

import type { Candle } from "@/types/market-data";

type CandleChartProps = {
  candles: Candle[];
  loading: boolean;
};

type HoveredCandle = {
  timeLabel: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  change: number;
  changePercent: number;
};

export function CandleChart({ candles, loading }: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const candlesRef = useRef<Candle[]>([]);
  const [hoveredCandle, setHoveredCandle] = useState<HoveredCandle | null>(
    null,
  );

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
        vertLine: {
          color: "rgba(255, 255, 255, 0.4)",
          width: 1,
          style: 3,
          labelBackgroundColor: "#ffffff",
        },
        horzLine: {
          color: "rgba(255, 255, 255, 0.4)",
          width: 1,
          style: 3,
          labelBackgroundColor: "#ffffff",
        },
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

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      const point = param.point;

      if (
        !seriesRef.current ||
        !point ||
        !param.time ||
        point.x < 0 ||
        point.y < 0 ||
        point.x > container.clientWidth ||
        point.y > container.clientHeight
      ) {
        setHoveredCandle(null);
        return;
      }

      const seriesData = param.seriesData.get(seriesRef.current);
      if (
        !seriesData ||
        typeof seriesData !== "object" ||
        !("open" in seriesData)
      ) {
        setHoveredCandle(null);
        return;
      }

      const open = Number(seriesData.open);
      const high = Number(seriesData.high);
      const low = Number(seriesData.low);
      const close = Number(seriesData.close);
      const change = close - open;
      const changePercent = open === 0 ? 0 : (change / open) * 100;

      setHoveredCandle({
        timeLabel: formatCrosshairTime(param.time),
        open,
        high,
        low,
        close,
        volume: resolveVolumeFromTime(param.time, candlesRef.current),
        change,
        changePercent,
      });
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);

    const resizeObserver = new ResizeObserver(() => {
      chart.timeScale().fitContent();
    });

    resizeObserver.observe(container);

    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
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

    candlesRef.current = candles;

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

      {hoveredCandle ? (
        <div className="pointer-events-none absolute left-3 top-3 z-20 rounded-md border border-border/70 bg-surface/90 px-3 py-2 shadow-[0_8px_30px_rgba(0,0,0,0.45)] backdrop-blur-md">
          <p className="font-mono text-[10px] uppercase tracking-widest text-gray-400">
            {hoveredCandle.timeLabel}
          </p>
          <div className="mt-2 grid grid-cols-[auto_auto] gap-x-4 gap-y-1 font-mono text-[11px] leading-none">
            <span className="text-gray-500">Open</span>
            <span className="text-right text-white">
              {formatPrice(hoveredCandle.open)}
            </span>

            <span className="text-gray-500">High</span>
            <span className="text-right text-trade-up">
              {formatPrice(hoveredCandle.high)}
            </span>

            <span className="text-gray-500">Low</span>
            <span className="text-right text-trade-down">
              {formatPrice(hoveredCandle.low)}
            </span>

            <span className="text-gray-500">Close</span>
            <span className="text-right text-white">
              {formatPrice(hoveredCandle.close)}
            </span>

            <span className="text-gray-500">Change</span>
            <span
              className={`text-right ${hoveredCandle.change >= 0 ? "text-trade-up" : "text-trade-down"}`}
            >
              {formatSigned(hoveredCandle.change, 5)} (
              {formatSigned(hoveredCandle.changePercent, 2)}%)
            </span>

            <span className="text-gray-500">Volume</span>
            <span className="text-right text-white">
              {formatVolume(hoveredCandle.volume)}
            </span>
          </div>
        </div>
      ) : null}

      {loading ? (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-white" />
          <span className="mt-4 font-mono text-[10px] uppercase tracking-widest text-white">
            Loading Data
          </span>
        </div>
      ) : null}
    </div>
  );
}

function toUtcTimestamp(value: string): UTCTimestamp {
  const date = new Date(value);
  return Math.floor(date.getTime() / 1000) as UTCTimestamp;
}

function toUtcTimestampFromTime(value: Time): UTCTimestamp | null {
  if (typeof value === "number") {
    return value as UTCTimestamp;
  }

  if (typeof value === "string") {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return Math.floor(parsed.getTime() / 1000) as UTCTimestamp;
  }

  if (
    value &&
    typeof value === "object" &&
    "year" in value &&
    "month" in value &&
    "day" in value
  ) {
    const parsed = Date.UTC(value.year, value.month - 1, value.day);
    return Math.floor(parsed / 1000) as UTCTimestamp;
  }

  return null;
}

function resolveVolumeFromTime(time: Time, candles: Candle[]): number | null {
  const timestamp = toUtcTimestampFromTime(time);
  if (timestamp === null) {
    return null;
  }

  const match = candles.find(
    (candle) => toUtcTimestamp(candle.time) === timestamp,
  );
  return match?.volume ?? null;
}

function formatCrosshairTime(time: Time): string {
  const timestamp = toUtcTimestampFromTime(time);
  if (timestamp === null) {
    return "-";
  }

  return new Date(timestamp * 1000).toLocaleString("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatPrice(value: number): string {
  return value.toFixed(5);
}

function formatSigned(value: number, decimals: number): string {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value).toFixed(decimals)}`;
}

function formatVolume(value: number | null): string {
  if (value === null) {
    return "-";
  }

  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }

  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }

  return value.toFixed(0);
}
