export type Resolution =
  | "SECOND"
  | "MINUTE"
  | "MINUTE_2"
  | "MINUTE_3"
  | "MINUTE_5"
  | "MINUTE_10"
  | "MINUTE_15"
  | "MINUTE_30"
  | "HOUR"
  | "HOUR_2"
  | "HOUR_3"
  | "HOUR_4"
  | "DAY"
  | "WEEK"
  | "MONTH";

export type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
};

export type CandlesResponse = {
  epic: string;
  resolution: Resolution;
  candles: Candle[];
  allowance_remaining: number | null;
  allowance_total: number | null;
};

export type MarketDetailsResponse = {
  epic: string;
  instrument_name: string;
  expiry: string | null;
  instrument_type: string;
  market_status: string;
  bid: number | null;
  offer: number | null;
  high: number | null;
  low: number | null;
  net_change: number | null;
  percentage_change: number | null;
  scaling_factor: number | null;
  streaming_prices_available: boolean;
  delay_time: number | null;
};

export type WatchlistItemResponse = {
  epic: string;
};
