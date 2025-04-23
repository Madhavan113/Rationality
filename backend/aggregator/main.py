import asyncio
import json
import logging
from datetime import datetime

import httpx
from fastapi import FastAPI, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.common.config import get_settings
from backend.common.utils import get_db, get_from_redis, store_in_redis, calculate_true_price
from backend.common.db import Market, TruePrice, init_db
from backend.common.models import TruePrice as TruePriceModel

# Initialize settings and logging
settings = get_settings()
settings.service_name = "aggregator"
settings.service_port = 8002

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Data Aggregator Service")

# Initialize database
init_db()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.service_name}

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    asyncio.create_task(aggregate_market_data())

async def aggregate_market_data():
    """
    Aggregate market data from Redis and calculate true prices.
    Run every second to provide real-time data.
    """
    while True:
        try:
            # Get all market IDs
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://ingestion:8001/api/markets")
                markets = response.json()

            for market in markets:
                market_id = market["id"]
                await process_market(market_id)
            
            # Wait for the next aggregation interval
            await asyncio.sleep(settings.aggregation_interval)
        except Exception as e:
            logger.error(f"Error in market data aggregation: {e}")
            await asyncio.sleep(5)  # Wait 5 seconds on error

async def process_market(market_id: str):
    """Process a single market's data and calculate the true price."""
    try:
        # Get the latest snapshot from Redis
        redis_key = f"market:{market_id}:snapshot"
        snapshot_data = get_from_redis(redis_key)
        
        if not snapshot_data:
            logger.warning(f"No snapshot data found for market {market_id}")
            return
        
        # Extract bids and asks
        bids = snapshot_data.get("bids", [])
        asks = snapshot_data.get("asks", [])
        mid_price = snapshot_data.get("mid_price", 0.0)
        
        # Calculate true price
        true_price_value = calculate_true_price(bids, asks)
        
        # Create true price model
        true_price = TruePriceModel(
            market_id=market_id,
            timestamp=datetime.utcnow(),
            value=true_price_value,
            mid_price=mid_price
        )
        
        # Store in Redis
        redis_key_true_price = f"market:{market_id}:true_price"
        store_in_redis(redis_key_true_price, true_price.dict(), expiry=3600)
        
        # Store in database
        await store_true_price_in_db(true_price)
        
        logger.info(f"Calculated true price {true_price_value} for market {market_id} (mid price: {mid_price})")
    except Exception as e:
        logger.error(f"Error processing market {market_id}: {e}")

async def store_true_price_in_db(true_price: TruePriceModel):
    """Store true price in the database."""
    db_true_price = TruePrice(
        market_id=true_price.market_id,
        timestamp=true_price.timestamp,
        value=true_price.value,
        mid_price=true_price.mid_price
    )
    
    # TODO: Implement actual database storage
    logger.info(f"Stored true price {true_price.value} for market {true_price.market_id}")

@app.get("/api/true-price/{market_id}")
async def get_true_price(market_id: str):
    """Get the latest true price for a specific market."""
    redis_key = f"market:{market_id}:true_price"
    true_price_data = get_from_redis(redis_key)
    
    if not true_price_data:
        return {"error": "No true price data found for this market"}
    
    return true_price_data

@app.websocket("/ws/true-price/{market_id}")
async def websocket_true_price(websocket, market_id: str):
    """WebSocket endpoint to stream true price updates."""
    await websocket.accept()
    
    try:
        while True:
            # Get the latest true price from Redis
            redis_key = f"market:{market_id}:true_price"
            true_price_data = get_from_redis(redis_key)
            
            if true_price_data:
                await websocket.send_json(true_price_data)
            
            # Wait before sending the next update
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    ) 