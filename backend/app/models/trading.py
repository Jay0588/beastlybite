"""
J.A.Y. Trading Models
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, JSON, Float
from app.core.database import Base
from datetime import datetime
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(String, primary_key=True, default=gen_uuid)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), default="NSE")
    market = Column(String(30), default="equity")  # equity, forex, crypto, commodity
    name = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    alert_price_above = Column(Float, nullable=True)
    alert_price_below = Column(Float, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(String, primary_key=True, default=gen_uuid)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), default="NSE")
    direction = Column(String(10), nullable=False)  # long, short
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String(20), default="open")  # open, closed, cancelled
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    strategy = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    metadata_ = Column(JSON, default=dict)


class TradeStrategy(Base):
    __tablename__ = "trade_strategies"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    indicators = Column(JSON, default=list)
    entry_conditions = Column(JSON, default=list)
    exit_conditions = Column(JSON, default=list)
    timeframes = Column(JSON, default=list)
    markets = Column(JSON, default=list)
    backtest_results = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(200), nullable=False)
    tool = Column(String(100), nullable=True)
    params = Column(JSON, default=dict)
    result_summary = Column(Text, nullable=True)
    approved = Column(Boolean, default=True)
    user = Column(String(100), default="user")
