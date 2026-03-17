"use client";

import { useEffect, useState } from "react";

import { getCandles } from "@/lib/api/market-data";
import type { CandlesResponse, Resolution } from "@/types/market-data";

type UseCandlesParams = {
  epic: string;
  resolution: Resolution;
  max: number;
};

type UseCandlesState = {
  data: CandlesResponse | null;
  isLoading: boolean;
  error: string | null;
  isLiveOnly: boolean;
};

export function useCandles({ epic, resolution, max }: UseCandlesParams): UseCandlesState {
  const [state, setState] = useState<UseCandlesState>({
    data: null,
    isLoading: true,
    error: null,
    isLiveOnly: false,
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState((current) => ({ ...current, isLoading: true, error: null }));

      try {
        const data = await getCandles({ epic, resolution, max });
        if (cancelled) {
          return;
        }

        setState({ data, isLoading: false, error: null, isLiveOnly: false });
      } catch (error) {
        if (cancelled) {
          return;
        }

        const detail = error instanceof Error ? error.message : "Unable to load candles";

        setState({
          data: null,
          isLoading: false,
          error: detail,
          isLiveOnly: true,
        });
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [epic, resolution, max]);

  return state;
}
