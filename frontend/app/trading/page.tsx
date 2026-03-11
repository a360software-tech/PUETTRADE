import TradingChart from "@/components/TradingChart";
import MarketList from "@/components/MarketList";
import Watchlist from "@/components/Watchlist";

export default function TradingPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold mb-8">Trading</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart - takes 2 columns */}
        <div className="lg:col-span-2">
          <TradingChart />
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Watchlist />
          <MarketList />
        </div>
      </div>
    </div>
  );
}
