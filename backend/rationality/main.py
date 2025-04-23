import logging
import asyncio

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import httpx

from backend.common.config import get_settings
from backend.common.db import init_db, get_db
from backend.common.models.rationality import RationalityMetrics
from backend.common.services.polymarket_client import PolymarketRestClient
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

# Define allowed origins (replace with your actual frontend domain)
allowed_origins = [
    "http://localhost:3000",  # Allow local development frontend
    "https://app.yourdomain.com"  # Production frontend URL
]

# Add CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Use the specific list
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Initialize service objects with the real client
client = PolymarketRestClient()
calculator = SimpleRationalityCalculator()
rationality_service = RationalityService(client, calculator)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.service_name}

@app.get("/api/v1/rationality/active/{market_id}", response_model=RationalityMetrics)
async def get_active_rationality(market_id: str, db: Session = Depends(get_db)):
    """
    Get active rationality metrics for a specific market.

    This endpoint:
    1. Fetches active orders for the market via RationalityService
    2. Calculates rationality metrics based on the order book
    3. Returns the metrics
    """
    try:
        metrics = await rationality_service.get_active(market_id)
        return metrics
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting active rationality for market {market_id}: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch data from Polymarket: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request error getting active rationality for market {market_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to Polymarket: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting active rationality for market {market_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate active rationality: {str(e)}")
    finally:
        pass

@app.get("/api/v1/rationality/historical/{market_id}", response_model=RationalityMetrics)
async def get_historical_rationality(market_id: str, db: Session = Depends(get_db)):
    """
    Get historical rationality metrics for a specific market.

    This endpoint:
    1. Fetches historical trades for the market via RationalityService
    2. Calculates rationality metrics based on the trade history
    3. Returns the metrics
    """
    try:
        metrics = await rationality_service.get_historical(market_id)
        return metrics
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting historical rationality for market {market_id}: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch data from Polymarket: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request error getting historical rationality for market {market_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to Polymarket: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting historical rationality for market {market_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate historical rationality: {str(e)}")
    finally:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )