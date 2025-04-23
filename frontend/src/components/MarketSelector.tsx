import { Market } from '../types';

interface MarketSelectorProps {
  markets: Market[];
  selectedMarket: Market | null;
  onMarketChange: (market: Market) => void;
}

export default function MarketSelector({ 
  markets, 
  selectedMarket, 
  onMarketChange 
}: MarketSelectorProps) {
  
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const marketId = e.target.value;
    const market = markets.find(m => m.id === marketId);
    if (market) {
      onMarketChange(market);
    }
  };
  
  return (
    <div className="bg-white shadow rounded-lg p-4">
      <label htmlFor="market-select" className="block text-sm font-medium text-gray-700 mb-2">
        Select Market
      </label>
      <select
        id="market-select"
        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
        value={selectedMarket?.id || ''}
        onChange={handleChange}
      >
        <option value="" disabled>Select a market</option>
        {markets.map(market => (
          <option key={market.id} value={market.id}>
            {market.name}
          </option>
        ))}
      </select>
      
      {selectedMarket && selectedMarket.description && (
        <p className="mt-2 text-sm text-gray-500">
          {selectedMarket.description}
        </p>
      )}
    </div>
  );
} 