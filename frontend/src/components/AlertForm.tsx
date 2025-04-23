import { useState } from 'react';
import { AlertRule } from '../types';

interface AlertFormProps {
  marketId: string;
}

export default function AlertForm({ marketId }: AlertFormProps) {
  const [alertName, setAlertName] = useState('');
  const [email, setEmail] = useState('');
  const [threshold, setThreshold] = useState('0.05');
  const [condition, setCondition] = useState<'above' | 'below'>('above');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!alertName || !email || !threshold) {
      setError('Please fill out all fields');
      return;
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address');
      return;
    }
    
    // Validate threshold is a number
    const thresholdValue = parseFloat(threshold);
    if (isNaN(thresholdValue) || thresholdValue <= 0 || thresholdValue >= 1) {
      setError('Threshold must be a number between 0 and 1');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccess(false);
    
    try {
      const alertData: AlertRule = {
        name: alertName,
        market_id: marketId,
        email,
        threshold: thresholdValue,
        condition
      };
      
      const response = await fetch('/api/alerts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(alertData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create alert');
      }
      
      // Reset form on success
      setAlertName('');
      setEmail('');
      setThreshold('0.05');
      setCondition('above');
      setSuccess(true);
    } catch (err) {
      console.error('Error creating alert:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
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
      
      {success && (
        <div className="rounded-md bg-green-50 p-4 mb-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Success</h3>
              <div className="text-sm text-green-700">
                Alert created successfully
              </div>
            </div>
          </div>
        </div>
      )}
      
      <div className="space-y-4">
        <div>
          <label htmlFor="alert-name" className="block text-sm font-medium text-gray-700">
            Alert Name
          </label>
          <input
            type="text"
            id="alert-name"
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="e.g., Large Price Deviation"
            value={alertName}
            onChange={(e) => setAlertName(e.target.value)}
            required
          />
        </div>
        
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            Email for Notifications
          </label>
          <input
            type="email"
            id="email"
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        
        <div>
          <label htmlFor="threshold" className="block text-sm font-medium text-gray-700">
            Price Deviation Threshold (0-1)
          </label>
          <input
            type="number"
            id="threshold"
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            placeholder="0.05"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            step="0.01"
            min="0.01"
            max="0.99"
            required
          />
        </div>
        
        <div>
          <label htmlFor="condition" className="block text-sm font-medium text-gray-700">
            Alert Condition
          </label>
          <select
            id="condition"
            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            value={condition}
            onChange={(e) => setCondition(e.target.value as 'above' | 'below')}
            required
          >
            <option value="above">When deviation is above threshold</option>
            <option value="below">When deviation is below threshold</option>
          </select>
        </div>
        
        <div>
          <button
            type="submit"
            className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            disabled={loading}
          >
            {loading ? 'Creating Alert...' : 'Create Alert'}
          </button>
        </div>
      </div>
    </form>
  );
} 