import { useState, useEffect } from 'react';
import { Leaderboard as LeaderboardType, LeaderboardEntry } from '../types';

interface LeaderboardProps {
  marketId: string;
}

export default function Leaderboard({ marketId }: LeaderboardProps) {
  const [data, setData] = useState<LeaderboardType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Fetch leaderboard data when component mounts or marketId changes
    const fetchLeaderboard = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`/api/leaderboard/${marketId}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch leaderboard data');
        }
        
        const leaderboardData = await response.json() as LeaderboardType;
        setData(leaderboardData);
      } catch (err) {
        console.error('Error fetching leaderboard:', err);
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };
    
    fetchLeaderboard();
    
    // Refresh data every 30 seconds
    const interval = setInterval(fetchLeaderboard, 30000);
    
    return () => clearInterval(interval);
  }, [marketId]);
  
  if (loading) {
    return (
      <div className="flex justify-center py-4">
        <p className="text-gray-500">Loading leaderboard data...</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="text-center py-4">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }
  
  if (!data || data.entries.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-gray-500">No leaderboard data available</p>
      </div>
    );
  }
  
  return (
    <div className="overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Position
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Trader
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Score
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.entries.map((entry) => (
            <tr key={entry.trader_id}>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {entry.position}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {entry.trader_name || entry.trader_id.substring(0, 8) + '...'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {entry.score.toFixed(4)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-right text-xs text-gray-500 mt-2 pr-2">
        Updated: {new Date(data.timestamp).toLocaleString()}
      </div>
    </div>
  );
} 