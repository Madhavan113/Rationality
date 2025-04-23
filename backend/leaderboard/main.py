import asyncio
import logging
from datetime import datetime, timedelta
import uuid

from fastapi import FastAPI, Depends
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from backend.common.config import get_settings
from backend.common.utils import get_db, calculate_brier_score
from backend.common.db import Market, Trader, TraderScore, init_db
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
    Background task to update trader scores.
    In a real implementation, this would analyze trader predictions and calculate Brier scores.
    """
    while True:
        try:
            # In a real implementation, this would:
            # 1. Get recent market data
            # 2. Get trader predictions
            # 3. Calculate Brier scores
            # 4. Update trader scores in the database
            
            # For demo purposes, we'll just add some random scores
            await generate_mock_trader_scores()
            
            # Wait before the next update
            await asyncio.sleep(60)  # Update every minute
        except Exception as e:
            logger.error(f"Error updating trader scores: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds on error

async def generate_mock_trader_scores():
    """Generate mock trader scores for demonstration purposes."""
    # This is just a placeholder. In a real implementation, scores would be
    # calculated based on actual trader predictions and market outcomes.
    import random
    
    # Mock traders
    mock_traders = [
        {"id": "trader1", "name": "Alice"},
        {"id": "trader2", "name": "Bob"},
        {"id": "trader3", "name": "Charlie"},
        {"id": "trader4", "name": "Diana"},
        {"id": "trader5", "name": "Evan"},
        {"id": "trader6", "name": "Fiona"},
        {"id": "trader7", "name": "George"}
    ]
    
    # Mock markets
    mock_markets = ["1", "2"]
    
    # Generate scores
    for market_id in mock_markets:
        for trader in mock_traders:
            # Generate a random score between 0 and 1 (lower is better for Brier score)
            score = random.random()
            
            # Log the score
            logger.info(f"Generated score {score} for trader {trader['name']} in market {market_id}")
            
            # In a real implementation, this would be stored in the database
            # For now, we just log it

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

@app.get("/api/leaderboard/{market_id}")
async def get_leaderboard(market_id: str, db: Session = Depends(get_db)):
    """
    Get the leaderboard for a specific market.
    Returns the top 5 traders by score.
    """
    # In a real implementation, this would query the database for the latest scores
    # For demo purposes, we'll generate random scores
    import random
    
    # Mock traders
    mock_traders = [
        {"id": "trader1", "name": "Alice"},
        {"id": "trader2", "name": "Bob"},
        {"id": "trader3", "name": "Charlie"},
        {"id": "trader4", "name": "Diana"},
        {"id": "trader5", "name": "Evan"},
        {"id": "trader6", "name": "Fiona"},
        {"id": "trader7", "name": "George"}
    ]
    
    # Generate entries
    entries = []
    for i, trader in enumerate(mock_traders[:5]):  # Top 5 traders
        # Generate a random score between 0 and 1 (lower is better for Brier score)
        score = random.random() * 0.5  # Make scores better (lower) for top traders
        
        entry = LeaderboardEntry(
            trader_id=trader["id"],
            trader_name=trader["name"],
            market_id=market_id,
            score=score,
            position=i+1
        )
        entries.append(entry)
    
    # Sort by score (lower is better)
    entries.sort(key=lambda x: x.score)
    
    # Update positions
    for i, entry in enumerate(entries):
        entry.position = i + 1
    
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