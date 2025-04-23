import time
import logging
from typing import Dict, List, Protocol
from collections import defaultdict

from backend.common.models.rationality import Order, Trade, RationalityMetrics, RawInputs

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
                # Simplified Brier score calculation
                # For a binary market: measure squared distance from consensus
                deviation = (order.price - consensus_price) ** 2
                weight = order.size / total_size
                weighted_score += deviation * weight
            
            # Lower is better for Brier score
            trader_scores[trader] = 1.0 - weighted_score  # Invert so higher is better
        
        # Calculate overall score (weighted average)
        total_size = sum(order.size for order in orders)
        if total_size == 0:
            overall_score = 0.0
        else:
            overall_score = sum(
                trader_scores[order.makerAddress] * (order.size / total_size)
                for order in orders
            )
        
        return RationalityMetrics(
            marketId=market_id,
            computedAt=int(time.time() * 1000),
            overallScore=overall_score,
            perTraderScore=trader_scores,
            rawInputs=RawInputs(orders=orders)
        )
    
    async def calculate_historical_rationality(self, market_id: str, trades: List[Trade]) -> RationalityMetrics:
        """
        Calculate rationality metrics based on historical trades.
        
        For historical data, we focus on:
        1. How trades perform over time
        2. Whether traders were on the right side of future price movements
        3. Consistency in a trader's strategy
        """
        if not trades:
            return RationalityMetrics(
                marketId=market_id,
                computedAt=int(time.time() * 1000),
                overallScore=0.0,
                perTraderScore={},
                rawInputs=RawInputs(trades=trades)
            )
        
        # Sort trades by timestamp (oldest first)
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        
        # Group trades by trader
        trader_trades = defaultdict(list)
        for trade in sorted_trades:
            trader_trades[trade.makerAddress].append(trade)
        
        # Calculate future price trend for each trade
        trade_outcomes = {}
        # For simplicity, we'll use the last price as the "outcome"
        final_price = sorted_trades[-1].price if sorted_trades else 0.5
        
        for i, trade in enumerate(sorted_trades):
            # If this is the last trade, use the final price as reference
            if i == len(sorted_trades) - 1:
                next_price = final_price
            else:
                next_price = sorted_trades[i + 1].price
            
            # Calculate if the trade was "rational" based on future price movement
            # A trade is more rational if the trader bought low before price rise
            # or sold high before price decline
            if trade.price < next_price:  # Price rose after this trade
                # Buying at low price before rise is rational (high score)
                rationality = 1.0 - trade.price  # Higher for lower purchase prices
            else:  # Price stayed same or fell after this trade
                # Selling at high price before decline is rational (high score)
                rationality = trade.price  # Higher for higher sale prices
            
            trade_outcomes[i] = rationality
        
        # Calculate trader scores based on their trades
        trader_scores = {}
        for trader, trader_trade_list in trader_trades.items():
            if not trader_trade_list:
                trader_scores[trader] = 0.0
                continue
                
            # Find this trader's trades in the sorted list
            trader_indices = [
                i for i, trade in enumerate(sorted_trades)
                if trade.makerAddress == trader
            ]
            
            # Calculate average rationality score for this trader's trades
            trader_scores[trader] = sum(
                trade_outcomes[i] for i in trader_indices
            ) / len(trader_indices)
        
        # Calculate overall score (average of all trader scores)
        overall_score = sum(trader_scores.values()) / len(trader_scores) if trader_scores else 0.0
        
        return RationalityMetrics(
            marketId=market_id,
            computedAt=int(time.time() * 1000),
            overallScore=overall_score,
            perTraderScore=trader_scores,
            rawInputs=RawInputs(trades=trades)
        ) 