"use client";

import { useEffect, useState } from "react";

import { getCandles } from "@/lib/api/market-data";
import { buildMockCandles } from "@/utils/mock-candles";
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
  isPreview: boolean;
};

export function useCandles({ epic, resolution, max }: UseCandlesParams): UseCandlesState {
  const [state, setState] = useState<UseCandlesState>({
    data: null,
    isLoading: true,
    error: null,
    isPreview: false,
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

        setState({ data, isLoading: false, error: null, isPreview: false });
      } catch (error) {
        if (cancelled) {
          return;
        }

        const detail = error instanceof Error ? error.message : "Unable to load candles";

        setState({
          data: buildMockCandles({ epic, resolution, max }),
          isLoading: false,
          error: detail,
          isPreview: true,
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
