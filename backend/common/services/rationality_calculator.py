import time
import logging
from typing import Dict, List, Protocol, Tuple
from collections import defaultdict
import math

from backend.common.models.rationality import Order, Trade, RationalityMetrics, RawInputs
from backend.common.utils import calculate_brier_score

logger = logging.getLogger(__name__)

# Define the interface using Protocol
class RationalityCalculator(Protocol):
    async def calculate_active_rationality(self, market_id: str, orders: List[Order]) -> RationalityMetrics:
        ...
    
    async def calculate_historical_rationality(self, market_id: str, trades: List[Trade]) -> RationalityMetrics:
        ...

class SimpleRationalityCalculator:
    async def calculate_active_rationality(self, market_id: str, orders: List[Order]) -> RationalityMetrics:
        """
        Calculate rationality metrics based on active order book.
        
        This is a simple implementation that:
        1. Groups orders by maker address
        2. Weights orders by size
        3. Computes deviation from expected behavior (e.g., from consensus price)
        4. Aggregates into trader scores
        """
        if not orders:
            return RationalityMetrics(
                marketId=market_id,
                computedAt=int(time.time() * 1000),
                overallScore=0.0,
                perTraderScore={},
                rawInputs=RawInputs(orders=orders)
            )
        
        # Group orders by trader
        trader_orders = defaultdict(list)
        for order in orders:
            trader_orders[order.makerAddress].append(order)
        
        # Calculate mid-price (simple consensus value)
        buy_orders = [o for o in orders if o.side == "BUY"]
        sell_orders = [o for o in orders if o.side == "SELL"]
        
        if not buy_orders or not sell_orders:
            consensus_price = 0.5  # Default for binary markets
        else:
            best_bid = max(buy_orders, key=lambda o: o.price).price if buy_orders else 0
            best_ask = min(sell_orders, key=lambda o: o.price).price if sell_orders else 1
            consensus_price = (best_bid + best_ask) / 2
        
        # Validate consensus price
        if math.isnan(consensus_price) or consensus_price < 0 or consensus_price > 1:
            logger.warning(f"Invalid consensus price {consensus_price} for market {market_id}, using default 0.5")
            consensus_price = 0.5
        
        # Calculate trader scores
        trader_scores = {}
        for trader, trader_order_list in trader_orders.items():
            # Calculate weighted deviation from consensus
            total_size = sum(order.size for order in trader_order_list)
            if total_size == 0:
                trader_scores[trader] = 0.0
                continue
                
            # Calculate Brier score components
            weighted_score = 0.0
            
            for order in trader_order_list:
                # Validate price
                price = order.price
                if math.isnan(price) or price < 0 or price > 1:
                    logger.warning(f"Invalid price {price} from trader {trader} on market {market_id}, skipping order")
                    continue
                    
                # Simplified Brier score calculation
                # For a binary market: measure squared distance from consensus
                deviation = (price - consensus_price) ** 2
                weight = order.size / total_size
                weighted_score += deviation * weight
            
            # Lower is better for Brier score
            score = 1.0 - weighted_score  # Invert so higher is better
            
            # Final validation of score
            if math.isnan(score):
                logger.warning(f"Calculated NaN score for trader {trader} on market {market_id}, defaulting to 0")
                trader_scores[trader] = 0.0
            else:
                trader_scores[trader] = max(0.0, min(1.0, score))  # Clamp to [0, 1]
        
        # Calculate overall score (weighted average)
        total_size = sum(order.size for order in orders)
        if total_size == 0:
            overall_score = 0.0
        else:
            weighted_sum = sum(
                trader_scores[order.makerAddress] * (order.size / total_size)
                for order in orders if order.makerAddress in trader_scores
            )
            overall_score = weighted_sum
            
            # Validate overall score
            if math.isnan(overall_score):
                logger.warning(f"Calculated NaN overall score for market {market_id}, defaulting to 0")
                overall_score = 0.0
            else:
                overall_score = max(0.0, min(1.0, overall_score))  # Clamp to [0, 1]
        
        return RationalityMetrics(
            marketId=market_id,
            computedAt=int(time.time() * 1000),
            overallScore=overall_score,
            perTraderScore=trader_scores,
            rawInputs=RawInputs(orders=orders)
        )
    
    async def _get_trader_market_data(self, market_id: str, trader_id: str) -> Tuple[List[float], List[int]]:
        """
        Fetch trader predictions and market outcomes from the database.
        Returns a tuple of:
        - List of probability predictions made by the trader
        - List of actual outcomes (0 or 1) for those predictions
        """
        from backend.common.db import get_db, Market, TraderScore
        from sqlalchemy import text
        import json
        
        logger.info(f"Fetching prediction data for trader {trader_id} on market {market_id}")
        
        # Get database session
        db = next(get_db())
        try:
            # Get market outcome (1 for YES, 0 for NO)
            market = db.query(Market).filter(Market.id == market_id).first()
            if not market or not hasattr(market, 'outcome') or market.outcome is None:
                logger.warning(f"Market {market_id} not found or has no outcome. Cannot calculate Brier score.")
                return [], []
                
            outcome = int(market.outcome)
            
            # Query trader predictions from the trader_predictions table
            # Adjust this query based on your actual schema
            stmt = text("""
                SELECT prediction_value, created_at 
                FROM trader_predictions 
                WHERE trader_id = :trader_id AND market_id = :market_id
                ORDER BY created_at
            """)
            
            result = db.execute(stmt, {"trader_id": trader_id, "market_id": market_id})
            predictions = []
            outcomes = []
            
            for row in result:
                prediction_value = float(row[0])
                # Validate prediction value
                if not math.isnan(prediction_value) and 0 <= prediction_value <= 1:
                    predictions.append(prediction_value)
                    outcomes.append(outcome)  # Same outcome for all predictions
                else:
                    logger.warning(f"Invalid prediction value {prediction_value} for trader {trader_id} on market {market_id}")
            
            if not predictions:
                logger.warning(f"No valid predictions found for trader {trader_id} on market {market_id}")
                return [], []
                
            logger.info(f"Found {len(predictions)} valid predictions for trader {trader_id} on market {market_id}")
            return predictions, outcomes
            
        except Exception as e:
            logger.error(f"Error fetching trader market data: {str(e)}")
            return [], []
        finally:
            db.close()

    async def calculate_historical_rationality(self, market_id: str, trades: List[Trade]) -> RationalityMetrics:
        """
        Calculate rationality metrics based on historical trades using Brier Score.

        Requires fetching each trader's predictions and the actual market outcome(s).
        """
        if not trades:
            return RationalityMetrics(
                marketId=market_id,
                computedAt=int(time.time() * 1000),
                overallScore=0.0,
                perTraderScore={},
                rawInputs=RawInputs(trades=trades)
            )

        # Group trades by trader to identify unique traders
        traders = set(trade.makerAddress for trade in trades)

        trader_scores = {}
        valid_scores = []

        for trader_id in traders:
            try:
                # Fetch predictions and outcomes for this trader and market
                predictions, outcomes = await self._get_trader_market_data(market_id, trader_id)

                if not predictions or len(predictions) != len(outcomes):
                    logger.warning(f"Insufficient or mismatched data for trader {trader_id} on market {market_id}. Skipping Brier score calculation.")
                    trader_scores[trader_id] = 0.0  # Default value instead of NaN
                    continue

                try:
                    # Calculate Brier score (lower is better)
                    brier_score = calculate_brier_score(predictions, outcomes)
                    
                    # Validate score
                    if math.isnan(brier_score):
                        logger.warning(f"Brier score calculation resulted in NaN for trader {trader_id}. Using default score.")
                        trader_scores[trader_id] = 0.0  # Default value
                    else:
                        # Clamp to [0, 1] range
                        clamped_score = max(0.0, min(1.0, brier_score))
                        trader_scores[trader_id] = clamped_score
                        valid_scores.append(clamped_score)
                except ValueError as ve:
                    logger.error(f"Error calculating Brier score for trader {trader_id}: {ve}")
                    trader_scores[trader_id] = 0.0  # Default value
                    
            except Exception as e:
                logger.error(f"Error calculating Brier score for trader {trader_id} on market {market_id}: {e}")
                trader_scores[trader_id] = 0.0  # Default value

        # Calculate overall score (e.g., average Brier score, lower is better)
        if valid_scores:
            overall_score = sum(valid_scores) / len(valid_scores)
        else:
            overall_score = 0.0  # Default value when no valid scores

        return RationalityMetrics(
            marketId=market_id,
            computedAt=int(time.time() * 1000),
            overallScore=overall_score,
            perTraderScore=trader_scores,
            rawInputs=RawInputs(trades=trades)
        )