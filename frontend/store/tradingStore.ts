/**
 * Trading store using Zustand.
 * TODO: Implement state management for trading data.
 */
import { create } from "zustand";

// TODO: Define proper types for market data, positions, etc.
interface TradingState {
  // Market data
  markets: unknown[];
  setMarkets: (markets: unknown[]) => void;

  // Watchlist
  watchlist: unknown[];
  setWatchlist: (watchlist: unknown[]) => void;

  // Positions
  positions: unknown[];
  setPositions: (positions: unknown[]) => void;

  // Selected market
  selectedEpic: string | null;
  setSelectedEpic: (epic: string | null) => void;

  // Loading state
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const useTradingStore = create<TradingState>((set) => ({
  // Market data
  markets: [],
  setMarkets: (markets) => set({ markets }),

  // Watchlist
  watchlist: [],
  setWatchlist: (watchlist) => set({ watchlist }),

  // Positions
  positions: [],
  setPositions: (positions) => set({ positions }),

  // Selected market
  selectedEpic: null,
  setSelectedEpic: (epic) => set({ selectedEpic: epic }),

  // Loading state
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
