import asyncio
import logging
from datetime import datetime, timedelta
import uuid
import random

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from backend.common.config import get_settings
from backend.common.db import Market, Trader, TraderScore, init_db, get_db
from backend.common.models import LeaderboardEntry, Leaderboard

# Initialize settings and logging
settings = get_settings()
settings.service_name = "leaderboard"
settings.service_port = 8003

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Leaderboard Service")

# Initialize database
init_db()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.service_name}

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    asyncio.create_task(update_trader_scores())

async def update_trader_scores():
    """
    Background task to update trader scores based on market outcomes.
    Fetches data and stores scores in the database.
    """
    while True:
        try:
            # Get DB session
            db: Session = next(get_db())
            try:
                # For demo purposes, we'll generate mock scores and store them.
                await generate_and_store_mock_trader_scores(db)
            finally:
                db.close()  # Close session after update cycle

            # Wait before the next update
            await asyncio.sleep(60)  # Update every minute
        except Exception as e:
            logger.error(f"Error updating trader scores: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds on error

async def generate_and_store_mock_trader_scores(db: Session):
    """Generate mock trader scores and store them in the database."""
    # Ensure mock traders exist
    mock_trader_data = [
        {"id": "trader1", "name": "Alice"},
        {"id": "trader2", "name": "Bob"},
        {"id": "trader3", "name": "Charlie"},
        {"id": "trader4", "name": "Diana"},
        {"id": "trader5", "name": "Evan"},
        {"id": "trader6", "name": "Fiona"},
        {"id": "trader7", "name": "George"}
    ]
    for t_data in mock_trader_data:
        trader = db.query(Trader).filter(Trader.id == t_data["id"]).first()
        if not trader:
            trader = Trader(id=t_data["id"], name=t_data["name"])
            db.add(trader)
    db.commit()  # Commit traders if any were added

    # Mock markets (fetch from DB)
    markets = db.query(Market).all()
    if not markets:
        logger.warning("No markets found in DB to generate scores for.")
        return

    # Generate scores
    for market in markets:
        for t_data in mock_trader_data:
            # Generate a random score (lower is better for Brier score)
            score = random.random()

            # Create or update score
            existing_score = db.query(TraderScore)\
                .filter(TraderScore.trader_id == t_data["id"], TraderScore.market_id == market.id)\
                .first()

            if existing_score:
                existing_score.score = score  # Update existing score
                existing_score.timestamp = datetime.utcnow()
            else:
                new_score = TraderScore(
                    trader_id=t_data["id"],
                    market_id=market.id,
                    score=score,
                    timestamp=datetime.utcnow()
                )
                db.add(new_score)

            logger.info(f"Generated/Updated score {score} for trader {t_data['name']} in market {market.id}")

    db.commit()  # Commit all score updates

@app.get("/api/markets")
async def get_markets(db: Session = Depends(get_db)):
    """Get all available markets."""
    markets = db.query(Market).all()
    return [
        {
            "id": market.id,
            "name": market.name,
            "description": market.description
        }
        for market in markets
    ]

@app.get("/api/leaderboard/{market_id}", response_model=Leaderboard)
async def get_leaderboard(market_id: str, db: Session = Depends(get_db)):
    """
    Get the leaderboard for a specific market from the database.
    Returns the top traders based on the latest scores.
    """
    # Check if market exists
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # Query for the latest score for each trader in the specified market
    top_scores = db.query(TraderScore, Trader.name)\
        .join(Trader, TraderScore.trader_id == Trader.id)\
        .filter(TraderScore.market_id == market_id)\
        .order_by(TraderScore.score.asc())\
        .limit(10)\
        .all()

    if not top_scores:
        # Return empty leaderboard if no scores found
        return Leaderboard(market_id=market_id, timestamp=datetime.utcnow(), entries=[])

    # Format entries
    entries = []
    for i, (score_entry, trader_name) in enumerate(top_scores):
        entry = LeaderboardEntry(
            trader_id=score_entry.trader_id,
            trader_name=trader_name,
            market_id=score_entry.market_id,
            score=score_entry.score,
            position=i + 1
        )
        entries.append(entry)

    leaderboard = Leaderboard(
        market_id=market_id,
        timestamp=datetime.utcnow(),
        entries=entries
    )

    return leaderboard

@app.post("/api/traders")
async def create_trader(name: str, db: Session = Depends(get_db)):
    """Create a new trader."""
    trader_id = str(uuid.uuid4())
    trader = Trader(
        id=trader_id,
        name=name
    )

    db.add(trader)
    db.commit()

    return {"id": trader_id, "name": name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )