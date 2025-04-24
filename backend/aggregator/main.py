import asyncio
import json
import logging
import math  # Import math for isnan
from datetime import datetime, timedelta
import sys
import os

# Add the backend directory to the path to resolve imports correctly
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import httpx
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from sqlalchemy.exc import SQLAlchemyError

# Import directly from the correct modules
from common.config import get_settings
from common.utils import calculate_true_price
from common.db import Market, MarketSnapshot, init_db, get_db, TruePrice  

# Create an alias for the TruePrice Pydantic model
TruePriceModel = None  # Will be defined below

# Initialize settings and logging
settings = get_settings()
settings.service_name = "aggregator"
settings.service_port = 8002

# Import the TruePriceModel directly from the file
try:
    # Try importing from common.models module
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "models", os.path.join(backend_dir, "common", "models.py")
    )
    models_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_module)
    TruePriceModel = models_module.TruePrice
    logging.info("Successfully imported TruePriceModel")
except Exception as e:
    logging.error(f"Error importing TruePriceModel: {e}")
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Data Aggregator Service")

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
    Run periodically using a single DB session per cycle.
    """
    while True:
        db: Session = next(get_db())
        try:
            # Get all market IDs from the database
            markets = db.query(Market).all()
            if not markets:
                logger.warning("No markets found in DB for aggregation.")
            else:
                logger.info(f"Aggregating data for {len(markets)} markets...")
                tasks = [process_market(market.id, db) for market in markets]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error processing market {markets[i].id} during aggregation: {result}")

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching markets for aggregation: {e}")
            # No rollback needed for read
        except Exception as e:
            logger.error(f"Error in market data aggregation cycle: {e}", exc_info=True)
        finally:
            db.close()  # Close session after processing all markets

        # Wait for the next aggregation interval
        await asyncio.sleep(settings.aggregation_interval)

async def process_market(market_id: str, db: Session):
    """Process a single market's data and calculate the true price using the provided DB session."""
    try:
        # Get the latest snapshot from the database
        latest_snapshot = db.query(MarketSnapshot)\
            .filter(MarketSnapshot.market_id == market_id)\
            .order_by(desc(MarketSnapshot.timestamp))\
            .first()

        if not latest_snapshot:
            return

        # Deserialize bids and asks from raw_data
        try:
            snapshot_data = json.loads(latest_snapshot.raw_data)
            bids = snapshot_data.get("bids", [])
            asks = snapshot_data.get("asks", [])
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to decode snapshot raw_data for market {market_id}, snapshot ID {latest_snapshot.id}: {json_err}")
            return

        # Use mid_price stored in the snapshot
        mid_price = latest_snapshot.mid_price

        # Calculate true price
        true_price_value = calculate_true_price(bids, asks)

        # Check if calculation resulted in NaN (e.g., due to invalid inputs)
        if math.isnan(true_price_value):
            logger.warning(f"True price calculation resulted in NaN for market {market_id}. Skipping storage.")
            return
        # Also check mid_price if it's used and could be NaN
        if mid_price is None or math.isnan(mid_price):
            logger.warning(f"Mid price is invalid (None or NaN) for market {market_id}. Skipping storage.")
            return

        # Create true price model
        true_price = TruePriceModel(
            market_id=market_id,
            timestamp=datetime.utcnow(),
            value=true_price_value,
            mid_price=mid_price
        )

        # Store true price in database
        await store_true_price_in_db(true_price, db)

        logger.info(f"Calculated true price {true_price_value:.4f} for market {market_id} (mid price: {mid_price:.4f})")

    except SQLAlchemyError as e:
        # Log DB errors during snapshot retrieval
        logger.error(f"Database error retrieving snapshot for market {market_id}: {e}")
        # Don't rollback here as it's likely a read error
        raise  # Re-raise to be caught by gather
    except Exception as e:
        logger.error(f"Unexpected error processing market {market_id}: {e}", exc_info=True)
        raise  # Re-raise to be caught by gather

async def store_true_price_in_db(true_price: TruePriceModel, db: Session):
    """Store true price in the database using the provided session."""
    try:
        db_true_price = TruePrice(
            market_id=true_price.market_id,
            timestamp=true_price.timestamp,
            value=true_price.value,
            mid_price=true_price.mid_price
        )

        db.add(db_true_price)
        db.commit()

        # Supabase Realtime Integration Comment:
        # -------------------------------------
        # The insert into the 'true_prices' table above will trigger a
        # notification via Supabase Realtime if:
        # 1. RLS is enabled for 'true_prices'.
        # 2. A suitable RLS policy allows reads (e.g., public read).
        # 3. A Supabase publication includes 'true_prices' (e.g., 'supabase_realtime').
        #
        # Frontend clients using supabase-js can subscribe to these changes like so:
        #
        # const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        #
        # const channel = supabase.channel('schema-db-changes');
        # channel.on(
        #   'postgres_changes',
        #   { event: 'INSERT', schema: 'public', table: 'true_prices' },
        #   (payload) => {
        #     console.log('New true price received:', payload.new);
        #     // Update your frontend state/UI here
        #   }
        # ).subscribe();
        #
        # See Supabase Realtime documentation for more details.
        # -------------------------------------

        logger.info(f"Stored true price {true_price.value:.4f} for market {true_price.market_id}")

    except SQLAlchemyError as e:
        logger.error(f"Database error storing true price for market {true_price.market_id}: {e}")
        db.rollback()  # Rollback failed commit
        raise  # Re-raise to be caught by caller
    except Exception as e:
        logger.error(f"Unexpected error storing true price for market {true_price.market_id}: {e}", exc_info=True)
        db.rollback()
        raise  # Re-raise

@app.get("/api/true-price/{market_id}", response_model=TruePriceModel)
async def get_true_price(market_id: str, db: Session = Depends(get_db)):
    """Get the latest true price for a specific market from the database."""
    try:
        latest_true_price = db.query(TruePrice)\
            .filter(TruePrice.market_id == market_id)\
            .order_by(desc(TruePrice.timestamp))\
            .first()

        if not latest_true_price:
            raise HTTPException(status_code=404, detail="No true price data found for this market")

        # Convert ORM object to Pydantic model before returning
        return TruePriceModel.from_orm(latest_true_price)

    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving true price for market {market_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve true price data")
    except Exception as e:
        logger.error(f"Unexpected error retrieving true price for market {market_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        # Assuming get_db uses yield
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )