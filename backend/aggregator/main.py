import asyncio
import json
import logging
from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from backend.common.config import get_settings
from backend.common.utils import calculate_true_price
from backend.common.db import Market, TruePrice, MarketSnapshot, init_db, get_db
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
    Aggregate market data from the database and calculate true prices.
    Run periodically.
    """
    while True:
        try:
            # Get DB session
            db: Session = next(get_db())
            try:
                # Get all market IDs from the database
                markets = db.query(Market).all()

                for market in markets:
                    market_id = market.id
                    await process_market(market_id, db)
            finally:
                db.close() # Close session after processing all markets

            # Wait for the next aggregation interval
            await asyncio.sleep(settings.aggregation_interval)
        except Exception as e:
            logger.error(f"Error in market data aggregation: {e}")
            await asyncio.sleep(5)  # Wait 5 seconds on error

async def process_market(market_id: str, db: Session):
    """Process a single market's data and calculate the true price using the provided DB session."""
    try:
        # Get the latest snapshot from the database
        latest_snapshot = db.query(MarketSnapshot)\
            .filter(MarketSnapshot.market_id == market_id)\
            .order_by(desc(MarketSnapshot.timestamp))\
            .first()

        if not latest_snapshot:
            logger.warning(f"No snapshot data found for market {market_id} in DB")
            return

        # Deserialize bids and asks from raw_data
        snapshot_data = json.loads(latest_snapshot.raw_data)
        bids = snapshot_data.get("bids", [])
        asks = snapshot_data.get("asks", [])
        # Use mid_price stored in the snapshot
        mid_price = latest_snapshot.mid_price

        # Calculate true price
        true_price_value = calculate_true_price(bids, asks)

        # Create true price model
        true_price = TruePriceModel(
            market_id=market_id,
            timestamp=datetime.utcnow(),
            value=true_price_value,
            mid_price=mid_price
        )

        # Store true price in database
        await store_true_price_in_db(true_price, db)

        logger.info(f"Calculated true price {true_price_value} for market {market_id} (mid price: {mid_price})")
    except Exception as e:
        logger.error(f"Error processing market {market_id}: {e}")

async def store_true_price_in_db(true_price: TruePriceModel, db: Session):
    """Store true price in the database using the provided session."""
    db_true_price = TruePrice(
        market_id=true_price.market_id,
        timestamp=true_price.timestamp,
        value=true_price.value,
        mid_price=true_price.mid_price
    )

    db.add(db_true_price)
    db.commit()

    # Optional: Supabase Realtime
    # To trigger realtime updates on the frontend for new true_prices:
    # 1. Ensure the `true_prices` table has Row Level Security (RLS) enabled in Supabase.
    # 2. Define a publication in Supabase for the `true_prices` table (e.g., `supabase_realtime`).
    #    ```sql
    #    CREATE PUBLICATION supabase_realtime FOR TABLE true_prices;
    #    ```
    # 3. The frontend `supabase-js` client can then subscribe to inserts on this table.

    logger.info(f"Stored true price {true_price.value} for market {true_price.market_id}")

@app.get("/api/true-price/{market_id}")
async def get_true_price(market_id: str, db: Session = Depends(get_db)):
    """Get the latest true price for a specific market from the database."""
    latest_true_price = db.query(TruePrice)\
        .filter(TruePrice.market_id == market_id)\
        .order_by(desc(TruePrice.timestamp))\
        .first()

    if not latest_true_price:
        raise HTTPException(status_code=404, detail="No true price data found for this market")

    return TruePriceModel(
        market_id=latest_true_price.market_id,
        timestamp=latest_true_price.timestamp,
        value=latest_true_price.value,
        mid_price=latest_true_price.mid_price
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )