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

interface TruePriceChartProps {
  marketId: string;
}

export default function TruePriceChart({ marketId }: TruePriceChartProps) {
  const [data, setData] = useState<TruePriceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  
  // Connect to WebSocket when component mounts or marketId changes
  useEffect(() => {
    setLoading(true);
    setError(null);
    
    // Close previous connection if exists
    if (socket) {
      socket.close();
    }
    
    // Create new WebSocket connection
    const ws = new WebSocket(`ws://${window.location.host}/ws/true-price/${marketId}`);
    
    ws.onopen = () => {
      console.log('Connected to WebSocket');
      setData([]);
    };
    
    ws.onmessage = (event) => {
      const newData = JSON.parse(event.data) as TruePriceData;
      
      setData(prevData => {
        // Add new data point and keep only the most recent 100 points
        const newDataArray = [...prevData, newData].slice(-100);
        return newDataArray;
      });
      
      setLoading(false);
    };
    
    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('Failed to connect to WebSocket server');
      setLoading(false);
    };
    
    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };
    
    setSocket(ws);
    
    // Clean up WebSocket connection on unmount
    return () => {
      ws.close();
    };
  }, [marketId]);
  
  // Prepare chart data
  const chartData = data.map(item => ({
    timestamp: new Date(item.timestamp).toLocaleTimeString(),
    truePrice: item.value,
    midPrice: item.mid_price
  }));
  
  return (
    <div className="h-80">
      {loading && data.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-500">Loading price data...</p>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-full">
          <p className="text-red-500">{error}</p>
        </div>
      ) : data.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-500">No price data available</p>
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
              type="monotone" 
              dataKey="truePrice" 
              name="True Price" 
              stroke="#8884d8" 
              activeDot={{ r: 8 }} 
            />
            <Line 
              type="monotone" 
              dataKey="midPrice" 
              name="Mid Price" 
              stroke="#82ca9d" 
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
} 