/**
 * API service for communicating with the backend.
 * TODO: Implement all API methods.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Base fetch wrapper with common configuration.
 * TODO: Add authentication headers, error handling, etc.
 */
async function fetchAPI(endpoint: string, options?: RequestInit) {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      // TODO: Add Authorization header
    },
    ...options,
  });

  if (!response.ok) {
    // TODO: Implement proper error handling
    throw new Error(`API Error: ${response.status}`);
  }

  return response.json();
}

// Health check
export const healthCheck = () => fetchAPI("/health");

// TODO: Auth endpoints
// export const login = (email: string, password: string) => { ... }
// export const register = (email: string, password: string, name: string) => { ... }

// TODO: Trading endpoints
// export const getMarkets = (searchTerm: string) => { ... }
// export const getMarketDetails = (epic: string) => { ... }
// export const openPosition = (epic: string, direction: string, size: number) => { ... }
// export const closePosition = (dealId: string) => { ... }

// TODO: Watchlist endpoints
// export const getWatchlists = () => { ... }
// export const createWatchlist = (name: string) => { ... }
// export const addToWatchlist = (watchlistId: number, epic: string) => { ... }
