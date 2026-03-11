export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="rounded-xl bg-trading-card p-6 border border-gray-800">
          <p className="text-sm text-gray-400">Portfolio Value</p>
          <p className="text-2xl font-bold mt-2 text-trading-green">
            — (Coming Soon)
          </p>
        </div>
        <div className="rounded-xl bg-trading-card p-6 border border-gray-800">
          <p className="text-sm text-gray-400">Open Positions</p>
          <p className="text-2xl font-bold mt-2">— (Coming Soon)</p>
        </div>
        <div className="rounded-xl bg-trading-card p-6 border border-gray-800">
          <p className="text-sm text-gray-400">Today&apos;s P&amp;L</p>
          <p className="text-2xl font-bold mt-2">— (Coming Soon)</p>
        </div>
      </div>

      {/* Placeholder sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl bg-trading-card p-6 border border-gray-800 min-h-[300px]">
          <h2 className="text-lg font-semibold mb-4">Recent Trades</h2>
          <p className="text-gray-500">
            {/* TODO: Implement trade history list */}
            Trade history will appear here.
          </p>
        </div>
        <div className="rounded-xl bg-trading-card p-6 border border-gray-800 min-h-[300px]">
          <h2 className="text-lg font-semibold mb-4">Watchlist</h2>
          <p className="text-gray-500">
            {/* TODO: Implement watchlist component */}
            Your watchlist will appear here.
          </p>
        </div>
      </div>
    </div>
  );
}
