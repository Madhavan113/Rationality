import { useState } from 'react';
import { 
  fetchActiveRationality, 
  fetchHistoricalRationality 
} from '../services/rationalityClient';
import { RationalityMetrics } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface MarketRationalityProps {
  marketId: string;
}

export default function MarketRationality({ marketId }: MarketRationalityProps) {
  const [mode, setMode] = useState<'active' | 'historical'>('active');
  const [data, setData] = useState<RationalityMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const loadRationality = async () => {
    if (!marketId) {
      setError('Please select a market first');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const fn = mode === 'active' ? fetchActiveRationality : fetchHistoricalRationality;
      const result = await fn(marketId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setData(null);
    } finally {
      setLoading(false);
    }
  };
  
  // Transform trader scores to chart data
  const chartData = data ? Object.entries(data.perTraderScore).map(([trader, score]) => ({
    trader: trader.slice(0, 8) + '...', // Truncate long addresses
    score: parseFloat(score.toFixed(3))
  })).sort((a, b) => b.score - a.score).slice(0, 10) : []; // Top 10 traders by score
  
  return (
    <div className="bg-white shadow overflow-hidden rounded-lg">
      <div className="px-4 py-5 sm:px-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900">Market Rationality</h3>
        <p className="mt-1 max-w-2xl text-sm text-gray-500">
          Analyze trader behavior and rationality in this market
        </p>
      </div>
      
      <div className="border-t border-gray-200 px-4 py-5 sm:p-6">
        <div className="flex flex-wrap gap-4 mb-4">
          <div>
            <select
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
              value={mode}
              onChange={(e) => setMode(e.target.value as 'active' | 'historical')}
            >
              <option value="active">Active Rationality</option>
              <option value="historical">Historical Rationality</option>
            </select>
          </div>
          
          <div>
            <button
              type="button"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              onClick={loadRationality}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Compute Rationality'}
            </button>
          </div>
        </div>
        
        {error && (
          <div className="rounded-md bg-red-50 p-4 mb-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="text-sm text-red-700">{error}</div>
              </div>
            </div>
          </div>
        )}
        
        {data && (
          <div>
            <div className="mb-4">
              <h4 className="text-md font-medium text-gray-900">Overall Score</h4>
              <div className="text-3xl font-bold text-indigo-600">
                {data.overallScore.toFixed(3)}
              </div>
              <div className="text-sm text-gray-500">
                Computed at {new Date(data.computedAt).toLocaleString()}
              </div>
            </div>
            
            {chartData.length > 0 && (
              <div className="mt-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">Top Trader Scores</h4>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={chartData}
                      margin={{ top: 5, right: 30, left: 20, bottom: 70 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="trader" 
                        angle={-45} 
                        textAnchor="end"
                        height={70}
                      />
                      <YAxis />
                      <Tooltip formatter={(value) => [value, 'Score']} />
                      <Legend />
                      <Bar dataKey="score" name="Rationality Score" fill="#6366F1" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
} 