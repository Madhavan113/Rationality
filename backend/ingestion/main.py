import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any
import math

import httpx
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from common.config import get_settings
from common.utils import calculate_mid_price
from common.db import Market, MarketSnapshot, init_db, get_db
from common.models import MarketSnapshot as MarketSnapshotModel
from common.services.polymarket_client import PolymarketRestClient

# Initialize settings and logging
settings = get_settings()
settings.service_name = "ingestion"
settings.service_port = 8001

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Data Ingestion Service")

# Define allowed origins for CORS
allowed_origins = [
    "http://localhost:3000",  # Allow local development frontend
    "https://app.yourdomain.com"  # Production frontend URL
]

# Add CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize database
init_db(use_create_all=False)

# Initialize Polymarket client
polymarket_client = PolymarketRestClient()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.service_name}

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    asyncio.create_task(poll_polymarket())

async def poll_polymarket():
    """
    Poll Polymarket API for market data periodically.
    Uses a separate DB session for each market to prevent race conditions.
    """
    while True:
        try:
            # Get a master session just for reading markets
            master_db: Session = next(get_db())
            try:
                markets = await fetch_markets_from_db(master_db)
                master_db.close()
                
                if not markets:
                    logger.warning("No markets found in the database to poll.")
                else:
                    logger.info(f"Polling data for {len(markets)} markets...")
                    # Process each market with its own DB session to prevent race conditions
                    tasks = []
                    for market in markets:
                        # Each task will create its own session
                        tasks.append(process_market_with_session(market["id"]))
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Error processing market {markets[i]['id']} during poll cycle: {result}", 
                                        exc_info=isinstance(result, Exception))
            except Exception as e:
                logger.error(f"Error fetching markets: {e}", exc_info=True)
                master_db.close()

            await asyncio.sleep(settings.aggregation_interval) # Use interval from settings
        except Exception as e:
            logger.error(f"Critical error during polling cycle: {e}", exc_info=True)
            await asyncio.sleep(10) # Longer wait on critical error

async def process_market_with_session(market_id: str):
    """
    Process a single market with its own DB session to prevent race conditions.
    """
    db: Session = next(get_db()) # Get a fresh DB session for this market
    try:
        await fetch_and_store_market_data(market_id, db)
    except Exception as e:
        logger.error(f"Error processing market {market_id}: {e}", exc_info=True)
        raise
    finally:
        db.close() # Always close the session

async def fetch_markets_from_db(db: Session) -> List[Dict[str, Any]]:
    """
    Fetch available markets from the database using the provided session.
    Handles potential database errors.
    """
    try:
        markets_orm = db.query(Market).all()
        return [
            {
                "id": market.id,
                "name": market.name,
                "description": market.description,
                "created_at": market.created_at.isoformat() if market.created_at else None,
                "updated_at": market.updated_at.isoformat() if market.updated_at else None
            }
            for market in markets_orm
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching markets: {e}")
        return [] # Return empty list on error
    except Exception as e:
        logger.error(f"Unexpected error fetching markets: {e}", exc_info=True)
        return [] # Return empty list on unexpected error

async def fetch_and_store_market_data(market_id: str, db: Session):
    """
    Fetch market data (active orders) for a specific market using PolymarketRestClient
    and store a snapshot in the database using the provided session.
    Includes error handling for API calls and DB writes.
    """
    orders = []
    try:
        # Fetch active orders using the real client
        orders = await polymarket_client.fetch_active_orders(market_id)

        # Separate bids and asks
        bids_raw = [o for o in orders if o.side == "BUY"]
        asks_raw = [o for o in orders if o.side == "SELL"]

        # Convert to the dictionary format expected by utils and snapshot model
        bids = [{"price": o.price, "size": o.size} for o in bids_raw]
        asks = [{"price": o.price, "size": o.size} for o in asks_raw]

        # Calculate mid price
        mid_price = calculate_mid_price(bids, asks)
        if mid_price is None or math.isnan(mid_price):
            logger.warning(f"Calculated mid_price is NaN for market {market_id}. Storing snapshot with NaN mid_price.")

        # Create snapshot model
        snapshot = MarketSnapshotModel(
            market_id=market_id,
            timestamp=datetime.utcnow(),
            bids=bids,
            asks=asks,
            mid_price=mid_price
        )

        # Store in database
        await store_snapshot_in_db(snapshot, db)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching orders for market {market_id}: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Request error fetching orders for market {market_id}: {e}")
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred while processing market {market_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching/storing data for market {market_id}: {e}", exc_info=True)
        raise

async def store_snapshot_in_db(snapshot: MarketSnapshotModel, db: Session):
    """Store market snapshot in the database using the provided session. Includes transaction handling."""
    try:
        db_snapshot = MarketSnapshot(
            market_id=snapshot.market_id,
            timestamp=snapshot.timestamp,
            raw_data=json.dumps({
                "bids": snapshot.bids,
                "asks": snapshot.asks
            }),
            mid_price=snapshot.mid_price
        )

        db.add(db_snapshot)
        db.commit() # Commit the individual snapshot

        logger.info(f"Stored snapshot for market {snapshot.market_id} with mid-price {snapshot.mid_price:.4f}")
    except SQLAlchemyError as e:
        logger.error(f"Database error storing snapshot for market {snapshot.market_id}: {e}")
        db.rollback() # Rollback on error
        raise
    except Exception as e:
        logger.error(f"Unexpected error storing snapshot for market {snapshot.market_id}: {e}", exc_info=True)
        db.rollback() # Rollback on error
        raise

@app.post("/api/markets")
async def create_market(
    name: str,
    description: str = None,
    db: Session = Depends(get_db)
):
    """Create a new market. Includes transaction handling."""
    market_id = str(uuid.uuid4())
    market = Market(
        id=market_id,
        name=name,
        description=description,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    try:
        db.add(market)
        db.commit()
        db.refresh(market)
        logger.info(f"Created market {market_id}: {name}")
        return {"id": market_id, "name": name, "description": description}
    except SQLAlchemyError as e:
        logger.error(f"Database error creating market: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create market in database")
    except Exception as e:
        logger.error(f"Unexpected error creating market: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        db.close()

@app.get("/api/markets")
async def get_markets(db: Session = Depends(get_db)):
    """Get all available markets. Includes error handling."""
    try:
        markets_orm = db.query(Market).all()
        return [
            {
                "id": market.id,
                "name": market.name,
                "description": market.description,
                "created_at": market.created_at,
                "updated_at": market.updated_at
            }
            for market in markets_orm
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving markets: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve markets")
    except Exception as e:
        logger.error(f"Unexpected error retrieving markets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )