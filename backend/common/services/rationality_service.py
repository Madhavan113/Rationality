import logging
from typing import List

from backend.common.models.rationality import RationalityMetrics
from backend.common.services.polymarket_client import PolymarketClient
from backend.common.services.rationality_calculator import RationalityCalculator

logger = logging.getLogger(__name__)

class RationalityService:
    """
    Service layer that coordinates fetching data and calculating rationality metrics.
    """
    
    def __init__(
        self,
        client: PolymarketClient,
        calculator: RationalityCalculator
    ):
        self.client = client
        self.calculator = calculator
    
    async def get_active(self, market_id: str) -> RationalityMetrics:
        """
        Get active rationality metrics for a specific market.
        
        This method:
        1. Fetches active orders from the Polymarket API
        2. Calculates rationality metrics based on the order book
        3. Returns the metrics
        """
        logger.info(f"Fetching active rationality metrics for market {market_id}")
        orders = await self.client.fetch_active_orders(market_id)
        return await self.calculator.calculate_active_rationality(market_id, orders)
    
    async def get_historical(self, market_id: str) -> RationalityMetrics:
        """
        Get historical rationality metrics for a specific market.
        
        This method:
        1. Fetches historical trades from the Polymarket API
        2. Calculates rationality metrics based on the trade history
        3. Returns the metrics
        """
        logger.info(f"Fetching historical rationality metrics for market {market_id}")
        trades = await self.client.fetch_trades(market_id)
        return await self.calculator.calculate_historical_rationality(market_id, trades) 