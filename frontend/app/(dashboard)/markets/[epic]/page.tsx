import { MarketTerminal } from "./_components/market-terminal";

type MarketPageProps = {
  params: Promise<{
    epic: string;
  }>;
};

export default async function MarketPage({ params }: MarketPageProps) {
  const { epic } = await params;

  return <MarketTerminal epic={decodeURIComponent(epic)} />;
}
