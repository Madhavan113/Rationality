import asyncio
import logging
from datetime import datetime, timedelta
import uuid
import random
from typing import List, Tuple
import math

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Change absolute imports to relative imports
from ..common.config import get_settings
from ..common.db import Market, Trader, TraderScore, init_db, get_db
from ..common.models import LeaderboardEntry, Leaderboard
from ..common.services.polymarket_client import PolymarketRestClient
from ..common.utils import calculate_brier_score

# Initialize settings and logging
settings = get_settings()
settings.service_name = "leaderboard"
settings.service_port = 8003

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Leaderboard Service")

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
    asyncio.create_task(update_trader_scores_periodically())

async def _get_trader_predictions_for_market(db: Session, market_id: str, trader_id: str) -> List[float]:
    """
    Fetch all predictions made by a trader for a specific market from the database.
    Returns a list of probability predictions (floats between 0 and 1).
    """
    from sqlalchemy import text
    try:
        # Query trader predictions from the trader_predictions table
        stmt = text("""
            SELECT prediction_value 
            FROM trader_predictions 
            WHERE trader_id = :trader_id AND market_id = :market_id
            ORDER BY created_at
        """)
        
        result = db.execute(stmt, {"trader_id": trader_id, "market_id": market_id})
        predictions = [float(row[0]) for row in result]
        
        if predictions:
            logger.info(f"Found {len(predictions)} predictions for trader {trader_id} on market {market_id}")
        else:
            logger.debug(f"No predictions found for trader {trader_id} on market {market_id}")
            
        return predictions
    except Exception as e:
        logger.error(f"Error fetching trader predictions: {str(e)}")
        return []

async def calculate_and_store_real_trader_scores(db: Session):
    """Calculate real trader scores using Brier score for resolved markets and store them."""
    try:
        resolved_markets = db.query(Market).filter(Market.is_resolved == True, Market.outcome != None).all()
        if not resolved_markets:
            logger.info("No resolved markets found with outcomes to calculate scores for.")
            return

        all_traders = db.query(Trader).all()
        if not all_traders:
            logger.warning("No traders found in DB to calculate scores for.")
            return

        logger.info(f"Found {len(resolved_markets)} resolved markets to process.")

        for market in resolved_markets:
            market_outcome = getattr(market, 'outcome', None)
            if market_outcome is None:
                logger.warning(f"Market {market.id} missing 'outcome' attribute. Using random mock outcome.")
                market_outcome = random.choice([0, 1])
            elif market_outcome not in [0.0, 1.0, 0, 1]:
                logger.warning(f"Market {market.id} has non-binary outcome {market_outcome}. Skipping Brier score calculation.")
                continue
            market_outcome = int(market_outcome)

            logger.info(f"Processing resolved market {market.id} with outcome: {market_outcome}")

            for trader in all_traders:
                try:
                    predictions = await _get_trader_predictions_for_market(db, market.id, trader.id)

                    if not predictions:
                        continue

                    outcomes = [market_outcome] * len(predictions)
                    brier_score = calculate_brier_score(predictions, outcomes)
                    logger.info(f"Calculated Brier score {brier_score:.4f} for trader {trader.id} in market {market.id}")

                    existing_score = db.query(TraderScore).filter(
                        TraderScore.trader_id == trader.id,
                        TraderScore.market_id == market.id
                    ).first()

                    current_time = datetime.utcnow()
                    if existing_score:
                        existing_score.score = brier_score
                        existing_score.timestamp = current_time
                        logger.debug(f"Updating score for trader {trader.id}, market {market.id}")
                    else:
                        new_score_entry = TraderScore(
                            trader_id=trader.id,
                            market_id=market.id,
                            score=brier_score,
                            timestamp=current_time
                        )
                        db.add(new_score_entry)
                        logger.debug(f"Inserting new score for trader {trader.id}, market {market.id}")

                except ValueError as ve:
                    logger.error(f"Input error calculating Brier score for trader {trader.id}, market {market.id}: {ve}")
                except Exception as calc_err:
                    logger.error(f"Unexpected error during score calculation for trader {trader.id}, market {market.id}: {calc_err}", exc_info=True)

        db.commit()
        logger.info("Successfully calculated and stored/updated real trader scores for resolved markets.")

    except AttributeError as ae:
        logger.error(f"Missing expected attribute (likely 'is_resolved' or 'outcome' in Market model): {ae}. Please update backend/common/db.py.")
        db.rollback()
    except SQLAlchemyError as e:
        logger.error(f"Database error during score calculation: {e}")
        db.rollback()
    except Exception as e:
        logger.error(f"Unexpected error during score calculation process: {e}", exc_info=True)
        db.rollback()

async def update_trader_scores_periodically():
    """
    Background task to periodically update trader scores based on market outcomes.
    Fetches data and stores scores in the database.
    """
    while True:
        db: Session = next(get_db())
        try:
            logger.info("Starting periodic trader score update...")
            await calculate_and_store_real_trader_scores(db)
            logger.info("Trader score update finished.")
        except Exception as e:
            logger.error(f"Error in periodic trader score update task: {e}", exc_info=True)
        finally:
            db.close()

        await asyncio.sleep(3600)

@app.get("/api/markets")
async def get_markets(db: Session = Depends(get_db)):
    """Get all available markets."""
    try:
        markets = db.query(Market).all()
        return [
            {
                "id": market.id,
                "name": market.name,
                "description": market.description
            }
            for market in markets
        ]
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving markets: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve markets")

@app.get("/api/leaderboard/{market_id}", response_model=Leaderboard)
async def get_leaderboard(market_id: str, db: Session = Depends(get_db)):
    """
    Get the leaderboard for a specific market from the database.
    Returns the top traders based on the latest scores (lower Brier score is better).
    """
    try:
        market = db.query(Market).filter(Market.id == market_id).first()
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        latest_score_subquery = db.query(
            TraderScore.trader_id,
            func.max(TraderScore.timestamp).label('latest_timestamp')
        ).filter(TraderScore.market_id == market_id).group_by(TraderScore.trader_id).subquery()

        top_scores = db.query(TraderScore, Trader.name)\
            .join(Trader, TraderScore.trader_id == Trader.id)\
            .join(
                latest_score_subquery,
                (TraderScore.trader_id == latest_score_subquery.c.trader_id) &
                (TraderScore.timestamp == latest_score_subquery.c.latest_timestamp)
            )\
            .filter(TraderScore.market_id == market_id)\
            .order_by(TraderScore.score.asc())\
            .limit(10)\
            .all()

        if not top_scores:
            return Leaderboard(market_id=market_id, timestamp=datetime.utcnow(), entries=[])

        entries = []
        current_time = datetime.utcnow()
        for i, (score_entry, trader_name) in enumerate(top_scores):
            entry = LeaderboardEntry(
                trader_id=score_entry.trader_id,
                trader_name=trader_name or f"Trader {score_entry.trader_id[:6]}...",
                market_id=score_entry.market_id,
                score=score_entry.score,
                position=i + 1,
                timestamp=current_time
            )
            entries.append(entry)

        leaderboard = Leaderboard(
            market_id=market_id,
            timestamp=current_time,
            entries=entries
        )

        return leaderboard

    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving leaderboard for market {market_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve leaderboard data")
    except Exception as e:
        logger.error(f"Unexpected error retrieving leaderboard for market {market_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@app.post("/api/traders")
async def create_trader(name: str, db: Session = Depends(get_db)):
    """Create a new trader."""
    trader_id = str(uuid.uuid4())
    trader = Trader(
        id=trader_id,
        name=name,
        created_at=datetime.utcnow()
    )

    try:
        db.add(trader)
        db.commit()
        db.refresh(trader)
        logger.info(f"Created trader {trader_id}: {name}")
        return {"id": trader_id, "name": name}
    except SQLAlchemyError as e:
        logger.error(f"Database error creating trader: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create trader")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )