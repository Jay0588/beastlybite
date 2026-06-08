"""
J.A.Y. Market Agent — Trading analysis, market data, technical analysis
"""
from typing import List, Dict, Optional
import logging
import json
from app.agents.base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

MARKET_SYSTEM = """You are J.A.Y.'s Market Agent — an expert algorithmic trader and market analyst.

Coverage: NSE, BSE, Forex (major pairs), Commodities (Gold, Oil, Silver), Cryptocurrency (BTC, ETH, major alts), US Stocks.

Technical Analysis capabilities:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- EMA/SMA (Exponential/Simple Moving Averages)
- Bollinger Bands
- VWAP (Volume Weighted Average Price)
- ATR (Average True Range)
- Volume Analysis
- Support/Resistance levels
- Chart patterns

Fundamental Analysis:
- Earnings analysis
- Revenue growth
- P/E, P/B ratios
- Debt analysis
- Sector analysis

Rules (CRITICAL):
- NEVER guarantee profits
- ALWAYS present probabilities, not certainties
- ALWAYS state risk alongside potential reward
- ALWAYS present alternative scenarios
- State confidence levels (Low/Medium/High) for all calls
- Recommend position sizing based on risk tolerance
- Clearly label opinions vs. data

Format: Present analysis clearly with:
1. Current situation
2. Technical picture
3. Key levels
4. Probabilities
5. Risk/reward
6. Recommendation with confidence
7. Invalidation conditions"""


class MarketAgent(BaseAgent):
    name = "market"
    description = "Trading analysis, market data, technical analysis, strategies"
    capabilities = [
        "market_analysis", "technical_analysis", "fundamental_analysis",
        "watchlist", "paper_trading", "backtesting", "news_analysis"
    ]

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self._emit(f"Market analysis: {context.user_query[:100]}", "thought")

        # Fetch market data if we can identify a symbol
        symbol = self._extract_symbol(context.user_query)
        market_data = ""
        if symbol:
            self._emit(f"Fetching data for {symbol}", "action")
            market_data = await self._fetch_market_data(symbol)

        messages = [
            {
                "role": "user",
                "content": f"Market query: {context.user_query}"
                           + (f"\n\nMarket Data for {symbol}:\n{market_data}" if market_data else "")
            }
        ]

        try:
            output = await self._llm(messages, system=MARKET_SYSTEM, temperature=0.3)
            self._emit("Analysis complete", "result")

            return AgentResult(
                agent=self.name,
                success=True,
                output=output,
                messages=self._messages,
            )
        except Exception as e:
            logger.error(f"Market agent error: {e}")
            return AgentResult(agent=self.name, success=False, output=str(e), error=str(e))

    def _extract_symbol(self, query: str) -> Optional[str]:
        """Extract stock/crypto symbol from query."""
        import re
        # Match: $BTC, NIFTY, RELIANCE.NS, BTCUSDT, etc.
        patterns = [
            r'\$([A-Z]{2,10})',           # $BTC
            r'\b([A-Z]{2,10}\.(?:NS|BO|NYSE|NASDAQ))\b',  # NSE/BSE
            r'\b(NIFTY|BANKNIFTY|SENSEX)\b',
            r'\b([A-Z]{2,5}USDT)\b',      # Crypto pairs
        ]
        for p in patterns:
            m = re.search(p, query.upper())
            if m:
                return m.group(1)
        return None

    async def _fetch_market_data(self, symbol: str) -> str:
        """Fetch real market data."""
        try:
            import yfinance as yf
            import pandas as pd

            # Map NSE symbols
            yf_symbol = symbol
            if not any(c in symbol for c in [".", "USDT", "USD"]):
                if len(symbol) <= 10:
                    yf_symbol = f"{symbol}.NS"

            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="1mo", interval="1d")
            info = ticker.info

            if hist.empty:
                return f"No data found for {symbol}"

            current = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else current
            change_pct = ((current - prev_close) / prev_close * 100)
            volume = hist["Volume"].iloc[-1]
            high_52w = hist["Close"].max()
            low_52w = hist["Close"].min()

            # Simple indicators
            sma20 = hist["Close"].rolling(20).mean().iloc[-1] if len(hist) >= 20 else None
            sma50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else None

            # RSI
            delta = hist["Close"].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / (loss + 1e-10)
            rsi = (100 - 100 / (1 + rs)).iloc[-1] if len(hist) >= 14 else None

            data = [
                f"Symbol: {symbol}",
                f"Current Price: {current:.2f}",
                f"Change: {change_pct:+.2f}%",
                f"Volume: {volume:,.0f}",
                f"52W High: {high_52w:.2f}",
                f"52W Low: {low_52w:.2f}",
            ]
            if sma20: data.append(f"SMA20: {sma20:.2f}")
            if sma50: data.append(f"SMA50: {sma50:.2f}")
            if rsi: data.append(f"RSI(14): {rsi:.1f}")
            if info.get("marketCap"):
                data.append(f"Market Cap: {info['marketCap']:,.0f}")
            if info.get("trailingPE"):
                data.append(f"P/E: {info['trailingPE']:.2f}")

            return "\n".join(data)

        except Exception as e:
            return f"Data fetch error: {e}"
