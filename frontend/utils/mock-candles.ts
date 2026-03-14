import type { CandlesResponse, Resolution } from "@/types/market-data";

type BuildMockCandlesParams = {
  epic: string;
  resolution: Resolution;
  max: number;
};

export function buildMockCandles({ epic, resolution, max }: BuildMockCandlesParams): CandlesResponse {
  const candles = Array.from({ length: max }, (_, index) => {
    const time = new Date(Date.now() - (max - index) * 60_000);
    const drift = Math.sin(index / 9) * 0.0035;
    const base = 1.09 + drift + index * 0.00004;
    const open = base + Math.sin(index / 4) * 0.0008;
    const close = open + Math.cos(index / 3) * 0.0009;
    const high = Math.max(open, close) + 0.0007;
    const low = Math.min(open, close) - 0.0007;

    return {
      time: time.toISOString(),
      open: round(open),
      high: round(high),
      low: round(low),
      close: round(close),
      volume: 100 + index * 3,
    };
  });

  return {
    epic,
    resolution,
    candles,
    allowance_remaining: null,
    allowance_total: null,
  };
}

function round(value: number) {
  return Number(value.toFixed(5));
}
