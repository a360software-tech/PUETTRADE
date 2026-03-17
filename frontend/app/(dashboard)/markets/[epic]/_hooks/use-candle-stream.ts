"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

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

type StreamAction =
  | { type: "sync_initial"; candles: Candle[]; mergeCandles: MergeCandles }
  | { type: "reset"; candles: Candle[] }
  | { type: "connected" }
  | { type: "connection_error"; error: string }
  | { type: "candle_update"; candle: Candle; completed: boolean; mergeCandles: MergeCandles; initialCandles: Candle[] };

type MergeCandles = (base: Candle[], incoming: Candle[]) => Candle[];

export function useCandleStream({
  epic,
  resolution,
  initialCandles,
}: UseCandleStreamParams): UseCandleStreamState {
  const [state, dispatch] = useReducer(streamReducer, {
    candles: initialCandles,
    isStreaming: false,
    error: null,
  });
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const connectRef = useRef<() => void>(() => undefined);
  const initialCandlesRef = useRef(initialCandles);
  const initialSnapshotRef = useRef<string>(buildCandlesSnapshot(initialCandles));

  const mergeCandles = useCallback((base: Candle[], incoming: Candle[]) => {
    const merged = new Map<number, Candle>();

    for (const candle of base) {
      const timestamp = toTimestamp(candle.time);
      if (timestamp !== null) {
        merged.set(timestamp, candle);
      }
    }

    for (const candle of incoming) {
      const timestamp = toTimestamp(candle.time);
      if (timestamp !== null) {
        merged.set(timestamp, candle);
      }
    }

    return Array.from(merged.entries())
      .sort(([left], [right]) => left - right)
      .map(([, candle]) => candle);
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current !== null) {
      return;
    }

    const attempt = reconnectAttemptsRef.current;
    const delay = Math.min(1000 * 2 ** attempt, 5000);
    reconnectAttemptsRef.current += 1;

    reconnectTimeoutRef.current = window.setTimeout(() => {
      reconnectTimeoutRef.current = null;
      connectRef.current();
    }, delay);
  }, []);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    if (reconnectTimeoutRef.current !== null) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    const baseUrl =
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    const url = new URL(
      `/api/v1/market-data/${encodeURIComponent(epic)}/stream`,
      baseUrl,
    );
    url.searchParams.set("resolution", resolution);

    const eventSource = new EventSource(url.toString());
    eventSourceRef.current = eventSource;

    eventSource.addEventListener("connected", () => {
      reconnectAttemptsRef.current = 0;
      dispatch({ type: "connected" });
    });

    eventSource.onmessage = (event) => {
      try {
        const data: CandleUpdate = JSON.parse(event.data);

        if (data.type === "candle_update") {
          if (data.epic !== epic) {
            console.warn("Ignoring candle update for mismatched epic", {
              expected: epic,
              received: data.epic,
            });
            return;
          }

          const updateCandle: Candle = {
            time: data.time,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
            volume: data.volume,
          };

          dispatch({
            type: "candle_update",
            candle: updateCandle,
            completed: data.completed,
            mergeCandles,
            initialCandles: initialCandlesRef.current,
          });
        }
      } catch (err) {
        console.error("Error parsing SSE message:", err);
      }
    };

    eventSource.onerror = () => {
      dispatch({ type: "connection_error", error: "Connection lost" });
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
      scheduleReconnect();
    };
  }, [epic, mergeCandles, resolution, scheduleReconnect]);

  useEffect(() => {
    const nextSnapshot = buildCandlesSnapshot(initialCandles);
    if (nextSnapshot === initialSnapshotRef.current) {
      initialCandlesRef.current = initialCandles;
      return;
    }

    initialSnapshotRef.current = nextSnapshot;
    initialCandlesRef.current = initialCandles;
    dispatch({ type: "sync_initial", candles: initialCandles, mergeCandles });
  }, [initialCandles, mergeCandles]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    reconnectAttemptsRef.current = 0;
    dispatch({ type: "reset", candles: initialCandlesRef.current });
  }, [epic, resolution]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current !== null) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [connect]);

  return {
    candles: state.candles,
    isStreaming: state.isStreaming,
    error: state.error,
  };
}

function streamReducer(
  state: UseCandleStreamState,
  action: StreamAction,
): UseCandleStreamState {
  switch (action.type) {
    case "sync_initial":
      return mergeStateCandles(state, action.mergeCandles(action.candles, state.candles));
    case "reset":
      return {
        candles: action.candles,
        isStreaming: false,
        error: null,
      };
    case "connected":
      return {
        ...state,
        isStreaming: true,
        error: null,
      };
    case "connection_error":
      return {
        ...state,
        isStreaming: false,
        error: action.error,
      };
    case "candle_update": {
      const currentCandles =
        state.candles.length === 0
          ? action.mergeCandles(action.initialCandles, [action.candle])
          : state.candles;
      const lastCandle = currentCandles[currentCandles.length - 1];
      const sameBucket =
        lastCandle && areSameCandleTime(lastCandle.time, action.candle.time);

      if (action.completed) {
        return {
          ...mergeStateCandles(
            state,
            sameBucket
              ? [...currentCandles.slice(0, -1), action.candle]
              : [...currentCandles, action.candle],
          ),
        };
      }

      return mergeStateCandles(
        state,
        sameBucket
          ? [...currentCandles.slice(0, -1), action.candle]
          : [...currentCandles, action.candle],
      );
    }
  }
}

function mergeStateCandles(
  state: UseCandleStreamState,
  candles: Candle[],
): UseCandleStreamState {
  if (haveSameCandles(state.candles, candles)) {
    return state;
  }

  return {
    ...state,
    candles,
  };
}

function haveSameCandles(left: Candle[], right: Candle[]): boolean {
  if (left.length !== right.length) {
    return false;
  }

  for (let index = 0; index < left.length; index += 1) {
    const leftCandle = left[index];
    const rightCandle = right[index];

    if (
      leftCandle.time !== rightCandle.time ||
      leftCandle.open !== rightCandle.open ||
      leftCandle.high !== rightCandle.high ||
      leftCandle.low !== rightCandle.low ||
      leftCandle.close !== rightCandle.close ||
      leftCandle.volume !== rightCandle.volume
    ) {
      return false;
    }
  }

  return true;
}

function buildCandlesSnapshot(candles: Candle[]): string {
  if (candles.length === 0) {
    return "0";
  }

  const first = candles[0];
  const last = candles[candles.length - 1];
  return [candles.length, first.time, first.close, last.time, last.close].join("|");
}

function toTimestamp(value: string): number | null {
  const parsed = new Date(value);
  const timestamp = parsed.getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
}

function areSameCandleTime(left: string, right: string): boolean {
  const leftTimestamp = toTimestamp(left);
  const rightTimestamp = toTimestamp(right);

  if (leftTimestamp === null || rightTimestamp === null) {
    return left === right;
  }

  return leftTimestamp === rightTimestamp;
}
