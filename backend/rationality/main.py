import logging
import asyncio

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.common.config import get_settings
from backend.common.db import init_db, get_db
from backend.common.models.rationality import RationalityMetrics
from backend.common.services.polymarket_client import PolymarketRestClient, MockPolymarketClient
from backend.common.services.rationality_calculator import SimpleRationalityCalculator
from backend.common.services.rationality_service import RationalityService

# Initialize settings and logging
settings = get_settings()
settings.service_name = "rationality"
settings.service_port = 8005

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Rationality Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Initialize service objects
client = MockPolymarketClient()
calculator = SimpleRationalityCalculator()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.service_name}

@app.get("/api/v1/rationality/active/{market_id}", response_model=RationalityMetrics)
async def get_active_rationality(market_id: str, db: Session = Depends(get_db)):
    """
    Get active rationality metrics for a specific market.
    
    This endpoint:
    1. Fetches active orders for the market
    2. Calculates rationality metrics based on the order book
    3. Returns the metrics
    """
    try:
        service = RationalityService(client, calculator)
        return await service.get_active(market_id)
    except Exception as e:
        logger.error(f"Error getting active rationality for market {market_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate active rationality: {str(e)}")

@app.get("/api/v1/rationality/historical/{market_id}", response_model=RationalityMetrics)
async def get_historical_rationality(market_id: str, db: Session = Depends(get_db)):
    """
    Get historical rationality metrics for a specific market.
    
    This endpoint:
    1. Fetches historical trades for the market
    2. Calculates rationality metrics based on the trade history
    3. Returns the metrics
    """
    try:
        service = RationalityService(client, calculator)
        return await service.get_historical(market_id)
    except Exception as e:
        logger.error(f"Error getting historical rationality for market {market_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate historical rationality: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )