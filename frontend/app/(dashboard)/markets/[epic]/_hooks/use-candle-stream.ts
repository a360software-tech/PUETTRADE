"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { Candle, Resolution } from "@/types/market-data";

type CandleUpdate = {
  type: "candle_update";
  epic: string;
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  completed: boolean;
};

type UseCandleStreamParams = {
  epic: string;
  resolution: Resolution;
  initialCandles: Candle[];
};

type UseCandleStreamState = {
  candles: Candle[];
  isStreaming: boolean;
  error: string | null;
};

export function useCandleStream({
  epic,
  resolution,
  initialCandles,
}: UseCandleStreamParams): UseCandleStreamState {
  const [candles, setCandles] = useState<Candle[]>(initialCandles);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const lastCandleRef = useRef<Candle | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    const url = new URL(`/api/v1/market-data/${encodeURIComponent(epic)}/stream`, baseUrl);
    url.searchParams.set("resolution", resolution);

    const eventSource = new EventSource(url.toString());
    eventSourceRef.current = eventSource;

    setIsStreaming(true);
    setError(null);

    eventSource.addEventListener("connected", () => {
      console.log("Streaming connected for", epic);
    });

    eventSource.addEventListener("error", (event) => {
      console.error("Streaming error:", event);
      setError("Connection lost");
      setIsStreaming(false);
    });

    eventSource.onmessage = (event) => {
      try {
        const data: CandleUpdate = JSON.parse(event.data);

        if (data.type === "candle_update") {
          const updateCandle: Candle = {
            time: data.time,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
            volume: data.volume,
          };

          setCandles((current) => {
            if (current.length === 0) {
              return [updateCandle];
            }

            const lastCandle = current[current.length - 1];

            if (data.completed) {
              if (lastCandle && lastCandle.time === data.time) {
                return [...current.slice(0, -1), updateCandle];
              }
              return [...current, updateCandle];
            }

            if (lastCandle && lastCandle.time === data.time) {
              return [...current.slice(0, -1), updateCandle];
            }

            return [...current, updateCandle];
          });

          lastCandleRef.current = updateCandle;
        }
      } catch (err) {
        console.error("Error parsing SSE message:", err);
      }
    };

    eventSource.onerror = () => {
      console.error("SSE connection error");
      setError("Connection lost");
      setIsStreaming(false);
      eventSource.close();
    };
  }, [epic, resolution]);

  const initializedRef = useRef(false);

  useEffect(() => {
    if (!initializedRef.current && initialCandles.length > 0) {
      setCandles(initialCandles);
      initializedRef.current = true;
    }
  }, [initialCandles]);

  useEffect(() => {
    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setIsStreaming(false);
    };
  }, [connect]);

  return {
    candles,
    isStreaming,
    error,
  };
}
