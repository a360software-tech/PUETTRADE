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
