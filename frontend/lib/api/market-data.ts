import type {
  CandlesResponse,
  MarketDetailsResponse,
  Resolution,
  WatchlistItemResponse,
} from "@/types/market-data";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type GetCandlesParams = {
  epic: string;
  resolution: Resolution;
  max: number;
};

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const json = (await response.json()) as { detail?: string };
    if (json.detail) {
      return json.detail;
    }
  } catch {
    // Ignore parse errors and use status text fallback.
  }

  return response.statusText || "Request failed";
}

export async function getCandles({
  epic,
  resolution,
  max,
}: GetCandlesParams): Promise<CandlesResponse> {
  const baseUrl = apiBaseUrl();
  const url = new URL(
    `/api/v1/market-data/${encodeURIComponent(epic)}/candles`,
    baseUrl,
  );
  url.searchParams.set("resolution", resolution);
  url.searchParams.set("max", String(max));

  const response = await fetch(url.toString(), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return (await response.json()) as CandlesResponse;
}

export async function getMarketDetails(epic: string): Promise<MarketDetailsResponse> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/markets/${encodeURIComponent(epic)}`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return (await response.json()) as MarketDetailsResponse;
}

export async function getWatchlist(): Promise<WatchlistItemResponse[]> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/markets/watchlist`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return (await response.json()) as WatchlistItemResponse[];
}

export type { MarketDetailsResponse };
