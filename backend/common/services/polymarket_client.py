import httpx
from typing import List, Protocol
import logging

from backend.common.models.rationality import Order, Trade

logger = logging.getLogger(__name__)

# Define the interface using Protocol
class PolymarketClient(Protocol):
    async def fetch_active_orders(self, market_id: str) -> List[Order]:
        ...
    
    async def fetch_trades(self, market_id: str) -> List[Trade]:
        ...

# Implementation for the REST API client
class PolymarketRestClient:
    def __init__(self, base_url: str = "https://clob.polymarket.com/data"):
        self.base_url = base_url
    
    async def fetch_active_orders(self, market_id: str) -> List[Order]:
        """Fetch active orders for a specific market from Polymarket API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/orders?market={market_id}")
                response.raise_for_status()
                
                # Parse and validate the response as a list of Order objects
                orders_data = response.json()
                return [Order.parse_obj(order) for order in orders_data]
        except Exception as e:
            logger.error(f"Error fetching active orders for market {market_id}: {str(e)}")
            return []
    
    async def fetch_trades(self, market_id: str) -> List[Trade]:
        """Fetch trade history for a specific market from Polymarket API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/trades?market={market_id}")
                response.raise_for_status()
                
                # Parse and validate the response as a list of Trade objects
                trades_data = response.json()
                return [Trade.parse_obj(trade) for trade in trades_data]
        except Exception as e:
            logger.error(f"Error fetching trades for market {market_id}: {str(e)}")
            return []

# Mock client for testing or development
class MockPolymarketClient:
    async def fetch_active_orders(self, market_id: str) -> List[Order]:
        """Return mock orders data for testing."""
        return [
            Order(
                makerAddress="0x123abc...",
                price=0.65,
                size=100,
                side="BUY",
                outcome="YES",
                timestamp=int(1000 * 1625097600)  # July 1, 2021
            ),
            Order(
                makerAddress="0x456def...",
                price=0.35,
                size=200,
                side="SELL",
                outcome="YES",
                timestamp=int(1000 * 1625097610)
            )
        ]
    
    async def fetch_trades(self, market_id: str) -> List[Trade]:
        """Return mock trades data for testing."""
        return [
            Trade(
                makerAddress="0x123abc...",
                price=0.65,
                size=50,
                outcome="YES",
                timestamp=int(1000 * 1625097700)
            ),
            Trade(
                makerAddress="0x789ghi...",
                price=0.40,
                size=75,
                outcome="YES",
                timestamp=int(1000 * 1625097800)
            )
        ] 