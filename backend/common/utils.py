import json
import logging
import math
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
        return math.nan

    try:
        best_bid_price = max(b.get("price", 0.0) for b in bids if isinstance(b.get("price"), (int, float)))
        best_ask_price = min(a.get("price", float("inf")) for a in asks if isinstance(a.get("price"), (int, float)))

        if best_bid_price == 0.0 or best_ask_price == float("inf"):
            return math.nan

        return (best_bid_price + best_ask_price) / 2
    except (ValueError, TypeError) as e:
        logger.error(f"Error calculating mid-price: {e}. Bids: {bids}, Asks: {asks}")
        return math.nan

def calculate_true_price(bids: List[Dict[str, Any]], asks: List[Dict[str, Any]]) -> float:
    """
    Calculate the true price using Volume Weighted Average Price (VWAP)
    across the top N levels of the order book or the entire book.
    This implementation uses the entire provided book depth.
    """
    total_volume = 0.0
    weighted_sum = 0.0

    for bid in bids:
        try:
            price = float(bid.get("price", 0.0))
            volume = float(bid.get("size", 0.0))
            if price > 0 and volume > 0:
                weighted_sum += price * volume
                total_volume += volume
        except (ValueError, TypeError):
            logger.warning(f"Skipping invalid bid data: {bid}")
            continue

    for ask in asks:
        try:
            price = float(ask.get("price", 0.0))
            volume = float(ask.get("size", 0.0))
            if price > 0 and volume > 0:
                weighted_sum += price * volume
                total_volume += volume
        except (ValueError, TypeError):
            logger.warning(f"Skipping invalid ask data: {ask}")
            continue

    if total_volume == 0:
        logger.warning("Total volume is zero, falling back to mid-price for true price calculation.")
        return calculate_mid_price(bids, asks)

    vwap = weighted_sum / total_volume
    return max(0.0, min(1.0, vwap))

def calculate_brier_score(predictions: List[float], outcomes: List[int]) -> float:
    """
    Calculate the Brier score for binary outcomes (0 or 1).

    Args:
        predictions: A list of predicted probabilities (float between 0 and 1).
        outcomes: A list of actual outcomes (int, either 0 or 1).

    Returns:
        The Brier score (float, lower is better).
    """
    if len(predictions) != len(outcomes):
        raise ValueError("Predictions and outcomes lists must have the same length.")
    if not predictions:
        return math.nan

    n = len(predictions)
    total_squared_error = 0.0

    for i in range(n):
        prediction = predictions[i]
        outcome = outcomes[i]

        if not (0.0 <= prediction <= 1.0):
            raise ValueError(f"Prediction must be between 0 and 1, got {prediction}")
        if outcome not in [0, 1]:
            raise ValueError(f"Outcome must be 0 or 1, got {outcome}")

        total_squared_error += (prediction - outcome) ** 2

    return total_squared_error / n