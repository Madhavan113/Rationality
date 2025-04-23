import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { TruePriceData } from '../types';
import { createClient, SupabaseClient, RealtimeChannel } from '@supabase/supabase-js';

interface TruePriceChartProps {
  marketId: string;
}

interface TruePrice extends TruePriceData {
  id?: number;
  market_id: string;
}

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

let supabase: SupabaseClient | null = null;
if (supabaseUrl && supabaseAnonKey) {
  supabase = createClient(supabaseUrl, supabaseAnonKey);
} else {
  console.error("Supabase URL or Anon Key is missing. Please check your .env file.");
}

export default function TruePriceChart({ marketId }: TruePriceChartProps) {
  const [data, setData] = useState<TruePriceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!supabase) {
      setError("Supabase client not initialized.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setData([]);

    setLoading(false);

    const channel: RealtimeChannel = supabase
      .channel(`true_prices:${marketId}`)
      .on<TruePrice>(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'true_prices',
          filter: `market_id=eq.${marketId}`
        },
        (payload) => {
          console.log('New true price received:', payload.new);
          const newData = payload.new as TruePriceData;
          setData(prevData => {
            const newDataArray = [...prevData, newData].slice(-100);
            return newDataArray;
          });
        }
      )
      .subscribe((status, err) => {
        if (status === 'SUBSCRIBED') {
          console.log(`Subscribed to true_prices for market ${marketId}`);
          setLoading(false);
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          console.error('Supabase subscription error:', err);
          setError(`Failed to subscribe to real-time updates: ${err?.message || 'Unknown error'}`);
          setLoading(false);
        }
      });

    return () => {
      if (channel) {
        console.log(`Unsubscribing from true_prices for market ${marketId}`);
        supabase?.removeChannel(channel);
      }
    };
  }, [marketId]);

  const chartData = data.map(item => ({
    timestamp: new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    truePrice: item.value,
    midPrice: item.mid_price
  }));

  return (
    <div className="h-80">
      {loading && data.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-500">Connecting to real-time price data...</p>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-full">
          <p className="text-red-500">{error}</p>
        </div>
      ) : data.length === 0 && !loading ? (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-500">No price data available yet for this market.</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis domain={[0, 1]} />
            <Tooltip />
            <Legend />
            <Line
              isAnimationActive={false}
              type="monotone"
              dataKey="truePrice"
              name="True Price"
              stroke="#8884d8"
              dot={false}
            />
            <Line
              isAnimationActive={false}
              type="monotone"
              dataKey="midPrice"
              name="Mid Price"
              stroke="#82ca9d"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}