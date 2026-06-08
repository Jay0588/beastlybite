"""
J.A.Y. Market Data — Real-time and historical data from multiple sources
"""
import logging
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Unified market data service.
    Sources: Yahoo Finance, NSE API, CCXT (crypto), Alpha Vantage
    """

    async def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict:
        """Get current quote for a symbol."""
        yf_symbol = self._to_yf_symbol(symbol, exchange)
        try:
            import yfinance as yf
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            hist = ticker.history(period="2d")

            if hist.empty:
                return {"error": f"No data for {symbol}"}

            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
            change = current - prev
            change_pct = (change / prev * 100) if prev else 0

            return {
                "symbol": symbol,
                "exchange": exchange,
                "price": round(current, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": int(hist["Volume"].iloc[-1]),
                "high": round(float(hist["High"].iloc[-1]), 2),
                "low": round(float(hist["Low"].iloc[-1]), 2),
                "open": round(float(hist["Open"].iloc[-1]), 2),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Quote fetch error for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}

    async def get_historical(
        self,
        symbol: str,
        period: str = "3mo",
        interval: str = "1d",
        exchange: str = "NSE",
    ) -> Dict:
        """Get OHLCV historical data."""
        yf_symbol = self._to_yf_symbol(symbol, exchange)
        try:
            import yfinance as yf
            import pandas as pd
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return {"error": "No historical data"}

            data = {
                "symbol": symbol,
                "exchange": exchange,
                "interval": interval,
                "period": period,
                "candles": [
                    {
                        "timestamp": idx.isoformat(),
                        "open": round(float(row["Open"]), 4),
                        "high": round(float(row["High"]), 4),
                        "low": round(float(row["Low"]), 4),
                        "close": round(float(row["Close"]), 4),
                        "volume": int(row["Volume"]),
                    }
                    for idx, row in hist.iterrows()
                ],
                "count": len(hist),
            }
            return data
        except Exception as e:
            return {"error": str(e)}

    async def get_indicators(self, symbol: str, exchange: str = "NSE") -> Dict:
        """Calculate technical indicators."""
        yf_symbol = self._to_yf_symbol(symbol, exchange)
        try:
            import yfinance as yf
            import pandas as pd
            import pandas_ta as ta

            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period="6mo", interval="1d")

            if df.empty or len(df) < 20:
                return {"error": "Insufficient data for indicators"}

            # Calculate indicators
            df.ta.rsi(append=True)
            df.ta.macd(append=True)
            df.ta.bbands(append=True)
            df.ta.ema(length=20, append=True)
            df.ta.ema(length=50, append=True)
            df.ta.atr(append=True)
            df.ta.vwap(append=True)

            last = df.iloc[-1]

            indicators = {
                "symbol": symbol,
                "price": round(float(df["Close"].iloc[-1]), 2),
                "rsi_14": round(float(last.get("RSI_14", 0) or 0), 2),
                "macd": round(float(last.get("MACD_12_26_9", 0) or 0), 4),
                "macd_signal": round(float(last.get("MACDs_12_26_9", 0) or 0), 4),
                "macd_hist": round(float(last.get("MACDh_12_26_9", 0) or 0), 4),
                "bb_upper": round(float(last.get("BBU_5_2.0", 0) or 0), 2),
                "bb_middle": round(float(last.get("BBM_5_2.0", 0) or 0), 2),
                "bb_lower": round(float(last.get("BBL_5_2.0", 0) or 0), 2),
                "ema_20": round(float(last.get("EMA_20", 0) or 0), 2),
                "ema_50": round(float(last.get("EMA_50", 0) or 0), 2),
                "atr_14": round(float(last.get("ATRr_14", 0) or 0), 4),
                "vwap": round(float(last.get("VWAP_D", 0) or 0), 2),
                "volume": int(df["Volume"].iloc[-1]),
                "avg_volume_20d": int(df["Volume"].rolling(20).mean().iloc[-1]),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Add signals
            indicators["signals"] = self._generate_signals(indicators)
            return indicators

        except Exception as e:
            logger.error(f"Indicator calculation error: {e}")
            return {"error": str(e)}

    def _generate_signals(self, indicators: Dict) -> List[Dict]:
        """Generate buy/sell signals from indicators."""
        signals = []
        price = indicators.get("price", 0)

        # RSI signals
        rsi = indicators.get("rsi_14", 50)
        if rsi < 30:
            signals.append({"indicator": "RSI", "signal": "OVERSOLD", "strength": "STRONG", "value": rsi})
        elif rsi < 40:
            signals.append({"indicator": "RSI", "signal": "OVERSOLD", "strength": "MODERATE", "value": rsi})
        elif rsi > 70:
            signals.append({"indicator": "RSI", "signal": "OVERBOUGHT", "strength": "STRONG", "value": rsi})
        elif rsi > 60:
            signals.append({"indicator": "RSI", "signal": "OVERBOUGHT", "strength": "MODERATE", "value": rsi})

        # MACD signals
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        macd_hist = indicators.get("macd_hist", 0)
        if macd > macd_signal and macd_hist > 0:
            signals.append({"indicator": "MACD", "signal": "BULLISH", "strength": "MODERATE", "value": macd_hist})
        elif macd < macd_signal and macd_hist < 0:
            signals.append({"indicator": "MACD", "signal": "BEARISH", "strength": "MODERATE", "value": macd_hist})

        # EMA signals
        ema20 = indicators.get("ema_20", 0)
        ema50 = indicators.get("ema_50", 0)
        if ema20 and ema50:
            if price > ema20 > ema50:
                signals.append({"indicator": "EMA", "signal": "BULLISH_TREND", "strength": "MODERATE"})
            elif price < ema20 < ema50:
                signals.append({"indicator": "EMA", "signal": "BEARISH_TREND", "strength": "MODERATE"})

        # Bollinger Bands
        bb_upper = indicators.get("bb_upper", 0)
        bb_lower = indicators.get("bb_lower", 0)
        if bb_upper and bb_lower and price:
            if price >= bb_upper:
                signals.append({"indicator": "BB", "signal": "OVERBOUGHT", "strength": "MODERATE"})
            elif price <= bb_lower:
                signals.append({"indicator": "BB", "signal": "OVERSOLD", "strength": "MODERATE"})

        return signals

    async def get_watchlist_quotes(self, symbols: List[Dict]) -> List[Dict]:
        """Get quotes for all watchlist symbols."""
        tasks = [self.get_quote(s["symbol"], s.get("exchange", "NSE")) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        quotes = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                quotes.append({"symbol": symbols[i]["symbol"], "error": str(r)})
            else:
                quotes.append(r)
        return quotes

    async def get_economic_calendar(self) -> List[Dict]:
        """Get upcoming economic events."""
        try:
            tool_instance = None
            from app.tools.web_tools import FetchURLTool
            tool = FetchURLTool()
            result = await tool.execute({"url": "https://finance.yahoo.com/calendar/earnings"})
            return [{"note": "Economic calendar: fetch from financial data provider", "raw": str(result.get("output", ""))[:500]}]
        except Exception:
            return []

    def _to_yf_symbol(self, symbol: str, exchange: str) -> str:
        """Convert symbol to Yahoo Finance format."""
        symbol = symbol.upper().strip()
        exchange = exchange.upper()

        if exchange in ["NSE", "NSE_EQ"]:
            if not symbol.endswith(".NS"):
                return f"{symbol}.NS"
        elif exchange in ["BSE", "BSE_EQ"]:
            if not symbol.endswith(".BO"):
                return f"{symbol}.BO"
        elif exchange in ["FOREX"]:
            if not symbol.endswith("=X"):
                return f"{symbol}=X"

        return symbol


market_data_service = MarketDataService()
