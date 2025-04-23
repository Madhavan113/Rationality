from datetime import datetime
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field

class Order(BaseModel):
    makerAddress: str
    price: float
    size: float
    side: Literal["BUY", "SELL"]
    outcome: str  # YES / NO / OutcomeIndex
    timestamp: int  # ms since epoch

class Trade(BaseModel):
    makerAddress: str
    price: float
    size: float
    outcome: str
    timestamp: int

class RawInputs(BaseModel):
    orders: Optional[List[Order]] = None
    trades: Optional[List[Trade]] = None

class RationalityMetrics(BaseModel):
    marketId: str
    computedAt: int
    overallScore: float
    perTraderScore: Dict[str, float]
    rawInputs: Optional[RawInputs] = None 