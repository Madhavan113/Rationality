import { RationalityMetrics } from '../types';

/**
 * Fetch active rationality metrics for a specific market
 * @param marketId The market ID to fetch metrics for
 * @returns Promise resolving to rationality metrics
 */
export async function fetchActiveRationality(marketId: string): Promise<RationalityMetrics> {
  try {
    const response = await fetch(`/api/v1/rationality/active/${marketId}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch active rationality metrics');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching active rationality:', error);
    throw error;
  }
}

/**
 * Fetch historical rationality metrics for a specific market
 * @param marketId The market ID to fetch metrics for
 * @returns Promise resolving to rationality metrics
 */
export async function fetchHistoricalRationality(marketId: string): Promise<RationalityMetrics> {
  try {
    const response = await fetch(`/api/v1/rationality/historical/${marketId}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch historical rationality metrics');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching historical rationality:', error);
    throw error;
  }
} 