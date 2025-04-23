import httpx
from typing import List, Protocol
import logging
import asyncio
import time

from backend.common.models.rationality import Order, Trade

logger = logging.getLogger(__name__)

# Define the interface using Protocol
class PolymarketClient(Protocol):
    async def fetch_active_orders(self, market_id: str) -> List[Order]:
        ...
    
    async def fetch_trades(self, market_id: str) -> List[Trade]:
        ...

# Helper function for retry logic
async def _retry_request(func, *args, max_retries=3, initial_delay=1, backoff_factor=2, **kwargs):
    """Retry an async function with exponential backoff."""
    retries = 0
    delay = initial_delay
    while retries < max_retries:
        try:
            return await func(*args, **kwargs)
        except httpx.RequestError as e:
            retries += 1
            if retries >= max_retries:
                logger.error(f"Max retries reached for {func.__name__}. Error: {e}")
                raise
            logger.warning(f"Request failed ({e}), retrying in {delay}s... ({retries}/{max_retries})")
            await asyncio.sleep(delay)
            delay *= backoff_factor
        except Exception as e:
            logger.error(f"An unexpected error occurred during request: {e}")
            raise

# Implementation for the REST API client
class PolymarketRestClient:
    def __init__(self, base_url: str = "https://clob.polymarket.com/data"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def _fetch_data(self, endpoint: str, params: dict):
        """Internal helper to fetch data from a given endpoint."""
        url = f"{self.base_url}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def fetch_active_orders(self, market_id: str) -> List[Order]:
        """Fetch active orders with retry logic."""
        try:
            orders_data = await _retry_request(
                self._fetch_data,
                endpoint="orders",
                params={"market": market_id}
            )
            return [Order.parse_obj(order) for order in orders_data]
        except Exception as e:
            logger.error(f"Failed to fetch active orders for market {market_id} after retries: {e}")
            return []
    
    async def fetch_trades(self, market_id: str) -> List[Trade]:
        """Fetch trade history with retry logic."""
        try:
            trades_data = await _retry_request(
                self._fetch_data,
                endpoint="trades",
                params={"market": market_id}
            )
            return [Trade.parse_obj(trade) for trade in trades_data]
        except Exception as e:
            logger.error(f"Failed to fetch trades for market {market_id} after retries: {e}")
            return []

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()

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