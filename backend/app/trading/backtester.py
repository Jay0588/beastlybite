"""
J.A.Y. Backtesting Engine — Test strategies on historical data
"""
from typing import Dict, List, Optional, Callable
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BacktestResult:
    def __init__(self):
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = []
        self.initial_capital: float = 0
        self.final_capital: float = 0

    @property
    def total_pnl(self) -> float:
        return self.final_capital - self.initial_capital

    @property
    def total_pnl_pct(self) -> float:
        if self.initial_capital == 0:
            return 0
        return (self.total_pnl / self.initial_capital) * 100

    @property
    def win_rate(self) -> float:
        closed = [t for t in self.trades if t.get("pnl") is not None]
        if not closed:
            return 0
        wins = [t for t in closed if t["pnl"] > 0]
        return len(wins) / len(closed) * 100

    @property
    def max_drawdown(self) -> float:
        if len(self.equity_curve) < 2:
            return 0
        peak = self.equity_curve[0]
        max_dd = 0
        for val in self.equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def sharpe_ratio(self) -> float:
        if len(self.equity_curve) < 2:
            return 0
        import numpy as np
        returns = [(self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
                   for i in range(1, len(self.equity_curve))]
        if not returns:
            return 0
        mean_r = sum(returns) / len(returns)
        std_r = (sum((r - mean_r)**2 for r in returns) / len(returns))**0.5
        if std_r == 0:
            return 0
        return (mean_r / std_r) * (252**0.5)  # annualized

    def to_dict(self) -> Dict:
        closed = [t for t in self.trades if t.get("pnl") is not None]
        winning = [t for t in closed if t["pnl"] > 0]
        losing = [t for t in closed if t["pnl"] < 0]

        return {
            "initial_capital": self.initial_capital,
            "final_capital": round(self.final_capital, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "total_trades": len(closed),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(self.win_rate, 2),
            "max_drawdown_pct": round(self.max_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "avg_win": round(sum(t["pnl"] for t in winning) / len(winning), 2) if winning else 0,
            "avg_loss": round(sum(t["pnl"] for t in losing) / len(losing), 2) if losing else 0,
            "largest_win": round(max((t["pnl"] for t in winning), default=0), 2),
            "largest_loss": round(min((t["pnl"] for t in losing), default=0), 2),
            "equity_curve": self.equity_curve[-100:],  # Last 100 points
            "trades": self.trades[-50:],  # Last 50 trades
        }


class Backtester:
    """
    Event-driven backtester for strategy testing on historical OHLCV data.
    """

    async def run(
        self,
        symbol: str,
        strategy_name: str,
        parameters: Dict,
        period: str = "1y",
        initial_capital: float = 100000.0,
        exchange: str = "NSE",
    ) -> Dict:
        """Run a backtest for a given strategy."""
        try:
            from app.trading.market_data import market_data_service
            # Get historical data
            hist_data = await market_data_service.get_historical(symbol, period, "1d", exchange)
            if "error" in hist_data:
                return {"error": hist_data["error"]}

            candles = hist_data["candles"]
            if len(candles) < 30:
                return {"error": "Insufficient historical data for backtest"}

            # Get strategy
            strategy = self._get_strategy(strategy_name, parameters)
            if not strategy:
                return {"error": f"Unknown strategy: {strategy_name}"}

            # Run backtest
            result = await self._execute_backtest(candles, strategy, initial_capital)
            return result.to_dict()

        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {"error": str(e)}

    def _get_strategy(self, name: str, params: Dict) -> Optional[Dict]:
        strategies = {
            "rsi_reversal": {
                "name": "RSI Reversal",
                "entry_long": lambda indicators: indicators.get("rsi", 50) < params.get("oversold", 30),
                "entry_short": lambda indicators: indicators.get("rsi", 50) > params.get("overbought", 70),
                "exit_long": lambda indicators: indicators.get("rsi", 50) > 50,
                "exit_short": lambda indicators: indicators.get("rsi", 50) < 50,
            },
            "ema_crossover": {
                "name": "EMA Crossover",
                "entry_long": lambda i: i.get("ema_fast", 0) > i.get("ema_slow", 0) and i.get("prev_ema_fast", 0) <= i.get("prev_ema_slow", 0),
                "entry_short": lambda i: i.get("ema_fast", 0) < i.get("ema_slow", 0) and i.get("prev_ema_fast", 0) >= i.get("prev_ema_slow", 0),
                "exit_long": lambda i: i.get("ema_fast", 0) < i.get("ema_slow", 0),
                "exit_short": lambda i: i.get("ema_fast", 0) > i.get("ema_slow", 0),
            },
            "macd_crossover": {
                "name": "MACD Crossover",
                "entry_long": lambda i: i.get("macd_hist", 0) > 0 and i.get("prev_macd_hist", 0) <= 0,
                "entry_short": lambda i: i.get("macd_hist", 0) < 0 and i.get("prev_macd_hist", 0) >= 0,
                "exit_long": lambda i: i.get("macd_hist", 0) < 0,
                "exit_short": lambda i: i.get("macd_hist", 0) > 0,
            },
        }
        return strategies.get(name)

    async def _execute_backtest(
        self, candles: List[Dict], strategy: Dict, initial_capital: float
    ) -> BacktestResult:
        result = BacktestResult()
        result.initial_capital = initial_capital
        capital = initial_capital
        result.equity_curve.append(capital)

        position = None  # {"direction", "entry_price", "quantity", "entry_idx"}

        closes = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]

        for i in range(20, len(candles)):
            close = closes[i]
            window = closes[max(0, i-20):i+1]

            # Calculate indicators
            rsi = self._calc_rsi(closes[:i+1])
            ema_fast = self._ema(closes[:i+1], 12)
            ema_slow = self._ema(closes[:i+1], 26)
            prev_ema_fast = self._ema(closes[:i], 12)
            prev_ema_slow = self._ema(closes[:i], 26)
            macd_hist = (ema_fast - ema_slow)
            prev_macd_hist = (prev_ema_fast - prev_ema_slow)

            indicators = {
                "rsi": rsi,
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "prev_ema_fast": prev_ema_fast,
                "prev_ema_slow": prev_ema_slow,
                "macd_hist": macd_hist,
                "prev_macd_hist": prev_macd_hist,
                "close": close,
            }

            # Check exits first
            if position:
                should_exit = False
                if position["direction"] == "long" and strategy["exit_long"](indicators):
                    should_exit = True
                elif position["direction"] == "short" and strategy["exit_short"](indicators):
                    should_exit = True

                if should_exit:
                    entry_p = position["entry_price"]
                    qty = position["quantity"]
                    if position["direction"] == "long":
                        pnl = (close - entry_p) * qty
                        capital += close * qty
                    else:
                        pnl = (entry_p - close) * qty

                    result.trades.append({
                        "direction": position["direction"],
                        "entry_price": entry_p,
                        "exit_price": close,
                        "quantity": qty,
                        "pnl": round(pnl, 2),
                        "entry_idx": position["entry_idx"],
                        "exit_idx": i,
                    })
                    position = None

            # Check entries
            if not position:
                qty = capital * 0.95 / close  # 95% of capital
                if strategy["entry_long"](indicators):
                    capital -= close * qty
                    position = {"direction": "long", "entry_price": close, "quantity": qty, "entry_idx": i}
                elif strategy["entry_short"](indicators):
                    position = {"direction": "short", "entry_price": close, "quantity": qty, "entry_idx": i}

            # Mark-to-market
            if position:
                if position["direction"] == "long":
                    mtm = capital + close * position["quantity"]
                else:
                    pnl = (position["entry_price"] - close) * position["quantity"]
                    mtm = capital + pnl
                result.equity_curve.append(round(mtm, 2))
            else:
                result.equity_curve.append(round(capital, 2))

        result.final_capital = result.equity_curve[-1] if result.equity_curve else initial_capital
        return result

    def _calc_rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d for d in deltas[-period:] if d > 0]
        losses = [-d for d in deltas[-period:] if d < 0]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    def _ema(self, closes: List[float], period: int) -> float:
        if len(closes) < period:
            return closes[-1] if closes else 0
        k = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        for price in closes[period:]:
            ema = price * k + ema * (1 - k)
        return round(ema, 4)


backtester = Backtester()
