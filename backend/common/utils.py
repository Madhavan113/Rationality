import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from .config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def serialize_datetime(obj):
    """Serialize datetime objects for JSON conversion."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def calculate_mid_price(bids: List[Dict[str, Any]], asks: List[Dict[str, Any]]) -> float:
    """Calculate the mid-price from the order book."""
    if not bids or not asks:
        return 0.0
    
    best_bid = max(bids, key=lambda x: x.get("price", 0))
    best_ask = min(asks, key=lambda x: x.get("price", float("inf")))
    
    bid_price = best_bid.get("price", 0)
    ask_price = best_ask.get("price", 0)
    
    if bid_price and ask_price:
        return (bid_price + ask_price) / 2
    
    return bid_price or ask_price or 0.0

def calculate_true_price(bids: List[Dict[str, Any]], asks: List[Dict[str, Any]]) -> float:
    """
    Calculate the true price using weighted mean of order book.
    
    TODO: Implement a more sophisticated algorithm for true price calculation.
    This is a placeholder implementation.
    """
    total_volume = 0
    weighted_sum = 0
    
    for bid in bids:
        price = bid.get("price", 0)
        volume = bid.get("size", 0)
        weighted_sum += price * volume
        total_volume += volume
    
    for ask in asks:
        price = ask.get("price", 0)
        volume = ask.get("size", 0)
        weighted_sum += price * volume
        total_volume += volume
    
    if total_volume == 0:
        return calculate_mid_price(bids, asks)
    
    return weighted_sum / total_volume

def calculate_brier_score(predictions: List[float], outcomes: List[int]) -> float:
    """
    Calculate Brier score for binary predictions.
    
    TODO: Implement proper Brier score calculation.
    This is a placeholder implementation.
    """
    if len(predictions) != len(outcomes):
        raise ValueError("Predictions and outcomes must have the same length")
    
    n = len(predictions)
    return sum((predictions[i] - outcomes[i]) ** 2 for i in range(n)) / n