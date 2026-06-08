"""
J.A.Y. Paper Trading Engine — Simulate trades with virtual capital
"""
from typing import Dict, List, Optional
from datetime import datetime
import logging
import uuid
from app.core.config import settings
from app.trading.market_data import market_data_service

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    In-memory paper trading with DB persistence.
    """

    def __init__(self):
        self.capital = settings.PAPER_TRADING_CAPITAL
        self.cash = settings.PAPER_TRADING_CAPITAL
        self.positions: Dict[str, Dict] = {}
        self.trade_history: List[Dict] = []

    async def open_trade(
        self,
        symbol: str,
        direction: str,  # long/short
        quantity: float,
        exchange: str = "NSE",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: Optional[str] = None,
    ) -> Dict:
        """Open a paper trade."""
        quote = await market_data_service.get_quote(symbol, exchange)
        if "error" in quote:
            return {"success": False, "error": quote["error"]}

        entry_price = quote["price"]
        cost = entry_price * quantity

        if direction == "long" and cost > self.cash:
            return {"success": False, "error": f"Insufficient capital. Need ₹{cost:,.2f}, have ₹{self.cash:,.2f}"}

        trade_id = str(uuid.uuid4())[:8]
        trade = {
            "id": trade_id,
            "symbol": symbol,
            "exchange": exchange,
            "direction": direction,
            "entry_price": entry_price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "strategy": strategy,
            "status": "open",
            "cost": cost,
            "opened_at": datetime.utcnow().isoformat(),
            "pnl": 0.0,
            "pnl_pct": 0.0,
        }

        self.positions[trade_id] = trade
        if direction == "long":
            self.cash -= cost

        self.trade_history.append({"action": "open", "trade": trade})
        logger.info(f"Paper trade opened: {direction} {quantity} {symbol} @ {entry_price}")
        return {"success": True, "trade": trade, "remaining_cash": self.cash}

    async def close_trade(self, trade_id: str) -> Dict:
        """Close an open paper trade."""
        if trade_id not in self.positions:
            return {"success": False, "error": "Trade not found"}

        trade = self.positions[trade_id]
        if trade["status"] != "open":
            return {"success": False, "error": "Trade already closed"}

        quote = await market_data_service.get_quote(trade["symbol"], trade.get("exchange", "NSE"))
        if "error" in quote:
            return {"success": False, "error": quote["error"]}

        exit_price = quote["price"]
        entry_price = trade["entry_price"]
        quantity = trade["quantity"]

        if trade["direction"] == "long":
            pnl = (exit_price - entry_price) * quantity
            self.cash += exit_price * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        pnl_pct = (pnl / (entry_price * quantity)) * 100

        trade.update({
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "status": "closed",
            "closed_at": datetime.utcnow().isoformat(),
        })
        del self.positions[trade_id]

        return {
            "success": True,
            "trade": trade,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "cash": self.cash,
        }

    async def get_portfolio(self) -> Dict:
        """Get current portfolio status."""
        total_value = self.cash
        positions_with_pnl = []

        for trade_id, trade in self.positions.items():
            try:
                quote = await market_data_service.get_quote(trade["symbol"], trade.get("exchange", "NSE"))
                current_price = quote.get("price", trade["entry_price"])
                qty = trade["quantity"]

                if trade["direction"] == "long":
                    current_value = current_price * qty
                    pnl = (current_price - trade["entry_price"]) * qty
                else:
                    current_value = trade["cost"]
                    pnl = (trade["entry_price"] - current_price) * qty

                pnl_pct = (pnl / trade["cost"]) * 100
                total_value += current_value

                positions_with_pnl.append({
                    **trade,
                    "current_price": current_price,
                    "current_value": round(current_value, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                })
            except Exception as e:
                positions_with_pnl.append({**trade, "error": str(e)})

        total_pnl = total_value - self.capital
        total_pnl_pct = (total_pnl / self.capital) * 100

        return {
            "capital": self.capital,
            "cash": round(self.cash, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "open_positions": len(self.positions),
            "positions": positions_with_pnl,
            "trades_taken": len(self.trade_history),
        }

    def get_trade_history(self) -> List[Dict]:
        return self.trade_history


paper_trading = PaperTradingEngine()
