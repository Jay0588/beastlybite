"""
J.A.Y. Trading API — Market data, watchlists, paper trading, backtesting
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import logging
from app.core.database import get_db
from app.trading.market_data import market_data_service
from app.trading.paper_trading import paper_trading
from app.trading.backtester import backtester

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trading", tags=["trading"])


class QuoteRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


class WatchlistAddRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    market: str = "equity"
    name: Optional[str] = None
    notes: Optional[str] = None


class TradeRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    direction: str  # long/short
    quantity: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: Optional[str] = None


class BacktestRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    strategy: str  # rsi_reversal, ema_crossover, macd_crossover
    period: str = "1y"
    initial_capital: float = 100000.0
    parameters: dict = {}


@router.get("/quote/{symbol}")
async def get_quote(symbol: str, exchange: str = "NSE"):
    """Get current market quote."""
    result = await market_data_service.get_quote(symbol, exchange)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/historical/{symbol}")
async def get_historical(symbol: str, exchange: str = "NSE", period: str = "3mo", interval: str = "1d"):
    """Get historical OHLCV data."""
    result = await market_data_service.get_historical(symbol, period, interval, exchange)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/indicators/{symbol}")
async def get_indicators(symbol: str, exchange: str = "NSE"):
    """Get technical indicators for a symbol."""
    result = await market_data_service.get_indicators(symbol, exchange)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Watchlist
@router.get("/watchlist")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    """Get all watchlist items with live quotes."""
    from sqlalchemy import select
    from app.models.trading import WatchlistItem
    result = await db.execute(select(WatchlistItem).where(WatchlistItem.is_active == True))
    items = result.scalars().all()
    if not items:
        return {"items": [], "count": 0}
    symbols = [{"symbol": i.symbol, "exchange": i.exchange} for i in items]
    quotes = await market_data_service.get_watchlist_quotes(symbols)
    return {"items": quotes, "count": len(quotes)}


@router.post("/watchlist")
async def add_to_watchlist(request: WatchlistAddRequest, db: AsyncSession = Depends(get_db)):
    """Add a symbol to watchlist."""
    from app.models.trading import WatchlistItem
    item = WatchlistItem(
        symbol=request.symbol.upper(),
        exchange=request.exchange,
        market=request.market,
        name=request.name,
        notes=request.notes,
    )
    db.add(item)
    await db.commit()
    return {"success": True, "symbol": request.symbol}


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    """Remove from watchlist."""
    from sqlalchemy import update
    from app.models.trading import WatchlistItem
    await db.execute(
        update(WatchlistItem)
        .where(WatchlistItem.symbol == symbol.upper())
        .values(is_active=False)
    )
    await db.commit()
    return {"success": True}


# Paper Trading
@router.post("/paper/trade")
async def open_paper_trade(request: TradeRequest):
    """Open a paper trade."""
    result = await paper_trading.open_trade(
        symbol=request.symbol,
        direction=request.direction,
        quantity=request.quantity,
        exchange=request.exchange,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        strategy=request.strategy,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/paper/close/{trade_id}")
async def close_paper_trade(trade_id: str):
    """Close a paper trade."""
    result = await paper_trading.close_trade(trade_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/paper/portfolio")
async def get_paper_portfolio():
    """Get paper trading portfolio."""
    return await paper_trading.get_portfolio()


# Backtesting
@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """Run a strategy backtest."""
    result = await backtester.run(
        symbol=request.symbol,
        strategy_name=request.strategy,
        parameters=request.parameters,
        period=request.period,
        initial_capital=request.initial_capital,
        exchange=request.exchange,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/news/{symbol}")
async def get_symbol_news(symbol: str):
    """Get latest news for a symbol."""
    from app.tools.web_tools import NewsFeedTool
    tool = NewsFeedTool()
    result = await tool.execute({"symbol": symbol})
    return result


@router.get("/calendar")
async def get_economic_calendar():
    """Get economic calendar."""
    return await market_data_service.get_economic_calendar()
