from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Market(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
class MarketSnapshot(BaseModel):
    market_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    bids: List[Dict[str, Any]]
    asks: List[Dict[str, Any]]
    mid_price: float
    
class TruePrice(BaseModel):
    market_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    value: float
    mid_price: float
    
class LeaderboardEntry(BaseModel):
    trader_id: str
    trader_name: str
    market_id: str
    score: float
    position: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
class Leaderboard(BaseModel):
    market_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    entries: List[LeaderboardEntry]
    
class AlertRule(BaseModel):
    id: Optional[str] = None
    name: str
    market_id: str
    email: str
    threshold: float
    condition: str  # "above" or "below"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Large deviation alert",
                "market_id": "1",
                "email": "user@example.com",
                "threshold": 0.05,
                "condition": "above"
            }
        }
    
class AlertNotification(BaseModel):
    alert_rule_id: str
    market_id: str
    true_price: float
    mid_price: float
    difference: float
    timestamp: datetime = Field(default_factory=datetime.utcnow) 