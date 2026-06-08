"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Plus, RefreshCw, BarChart2, Activity, Newspaper } from "lucide-react";
import { tradingAPI } from "@/lib/api";
import { useStore } from "@/store";
import type { Quote, TechnicalIndicators } from "@/types";

function PnLBadge({ value }: { value: number }) {
  const positive = value >= 0;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-mono ${positive ? "text-jay-green" : "text-jay-red"}`}>
      {positive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {positive ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

function SignalBadge({ signal, strength }: { signal: string; strength: string }) {
  const isbull = signal.includes("BULL") || signal.includes("OVER") && !signal.includes("OVERBOUGHT");
  const color = signal.includes("BULL") || signal.includes("OVERSOLD") ? "#22c55e"
    : signal.includes("BEAR") || signal.includes("OVERBOUGHT") ? "#ef4444"
    : "#f97316";
  return (
    <span
      className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
      style={{ color, borderColor: color + "44", background: color + "11" }}
    >
      {signal}
    </span>
  );
}

function WatchlistRow({ item, onSelect }: { item: any; onSelect: () => void }) {
  const change = item.change_pct ?? 0;
  const positive = change >= 0;
  return (
    <button
      onClick={onSelect}
      className="w-full flex items-center justify-between px-3 py-2 hover:bg-jay-surface/60 rounded-lg transition-colors group"
    >
      <div className="text-left">
        <div className="text-xs font-mono font-semibold text-jay-text group-hover:text-jay-accent transition-colors">
          {item.symbol}
        </div>
        <div className="text-[10px] text-jay-textMuted">{item.exchange}</div>
      </div>
      <div className="text-right">
        <div className="text-xs font-mono text-jay-text">{item.price?.toFixed(2) || "—"}</div>
        <PnLBadge value={change} />
      </div>
    </button>
  );
}

function IndicatorGauge({ label, value, min, max, unit = "" }: { label: string; value: number; min: number; max: number; unit?: string }) {
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  const color = pct < 30 ? "#22c55e" : pct > 70 ? "#ef4444" : "#00d4ff";
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-[10px] font-mono text-jay-textDim">
        <span>{label}</span>
        <span style={{ color }}>{value.toFixed(1)}{unit}</span>
      </div>
      <div className="h-1 bg-jay-border/40 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8 }}
        />
      </div>
    </div>
  );
}

export default function TradingPanel() {
  const { activeSymbol, activeExchange, setActiveSymbol, watchlist, setWatchlist, portfolio, setPortfolio } = useStore();
  const [quote, setQuote] = useState<Quote | null>(null);
  const [indicators, setIndicators] = useState<TechnicalIndicators | null>(null);
  const [news, setNews] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [addSymbol, setAddSymbol] = useState("");
  const [activeTab, setActiveTab] = useState<"indicators" | "news" | "portfolio" | "backtest">("indicators");
  const [backtestConfig, setBacktestConfig] = useState({ strategy: "rsi_reversal", period: "1y" });
  const [backtestResult, setBacktestResult] = useState<any>(null);

  const loadSymbolData = useCallback(async (symbol: string, exchange: string) => {
    setLoading(true);
    try {
      const [q, ind] = await Promise.all([
        tradingAPI.getQuote(symbol, exchange),
        tradingAPI.getIndicators(symbol, exchange),
      ]);
      setQuote(q);
      setIndicators(ind);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadWatchlist = useCallback(async () => {
    try {
      const data = await tradingAPI.getWatchlist();
      setWatchlist(data.items || []);
    } catch {}
  }, []);

  const loadPortfolio = useCallback(async () => {
    try {
      const p = await tradingAPI.getPortfolio();
      setPortfolio(p);
    } catch {}
  }, []);

  useEffect(() => {
    loadSymbolData(activeSymbol, activeExchange);
    loadWatchlist();
    loadPortfolio();
  }, [activeSymbol, activeExchange]);

  useEffect(() => {
    if (activeTab === "news") {
      tradingAPI.getNews(activeSymbol).then((r) => setNews(r.articles || [])).catch(() => {});
    }
  }, [activeTab, activeSymbol]);

  const handleAddWatchlist = async () => {
    if (!addSymbol.trim()) return;
    await tradingAPI.addToWatchlist(addSymbol.toUpperCase(), activeExchange);
    setAddSymbol("");
    loadWatchlist();
  };

  const runBacktest = async () => {
    setLoading(true);
    try {
      const result = await tradingAPI.runBacktest({
        symbol: activeSymbol,
        exchange: activeExchange,
        strategy: backtestConfig.strategy,
        period: backtestConfig.period,
        initial_capital: 100000,
      });
      setBacktestResult(result);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full gap-3 p-0">
      {/* Sidebar: watchlist */}
      <div className="w-52 flex-shrink-0 flex flex-col border-r border-jay-border/40 pr-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-mono text-jay-textDim tracking-widest">WATCHLIST</span>
          <button onClick={loadWatchlist} className="text-jay-textMuted hover:text-jay-accent">
            <RefreshCw size={11} />
          </button>
        </div>
        <div className="flex gap-1 mb-2">
          <input
            value={addSymbol}
            onChange={(e) => setAddSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && handleAddWatchlist()}
            placeholder="Add symbol…"
            className="flex-1 bg-jay-surface border border-jay-border/50 rounded px-2 py-1 text-[11px] font-mono text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/60"
          />
          <button onClick={handleAddWatchlist} className="px-1.5 text-jay-accent hover:text-jay-text">
            <Plus size={12} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto space-y-0.5">
          {watchlist.length === 0 ? (
            <div className="text-[11px] text-jay-textMuted text-center py-4">
              Add symbols to watchlist
            </div>
          ) : (
            watchlist.map((item: any) => (
              <WatchlistRow
                key={item.symbol}
                item={item}
                onSelect={() => setActiveSymbol(item.symbol, item.exchange || activeExchange)}
              />
            ))
          )}
        </div>

        {/* Default symbols */}
        <div className="pt-2 border-t border-jay-border/30">
          <div className="text-[9px] font-mono text-jay-textMuted mb-1">QUICK ACCESS</div>
          {["NIFTY 50", "RELIANCE.NS", "BTCUSDT", "EURUSD=X"].map((s) => (
            <button
              key={s}
              onClick={() => setActiveSymbol(s.replace(".NS", "").replace("=X", ""))}
              className="w-full text-left text-[11px] font-mono text-jay-textDim hover:text-jay-accent py-0.5 px-2 rounded hover:bg-jay-surface/60 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col gap-3 overflow-hidden">
        {/* Symbol header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-display font-bold text-jay-text">{activeSymbol}</h2>
              <span className="text-[10px] font-mono text-jay-textDim border border-jay-border/40 px-1.5 py-0.5 rounded">
                {activeExchange}
              </span>
              {loading && (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-3 h-3 border border-jay-accent/60 border-t-transparent rounded-full"
                />
              )}
            </div>
            {quote && (
              <div className="flex items-center gap-4 mt-1">
                <span className="text-2xl font-mono font-bold text-jay-text">
                  {quote.price?.toFixed(2)}
                </span>
                <PnLBadge value={quote.change_pct} />
                <span className="text-xs text-jay-textDim font-mono">
                  H: {quote.high?.toFixed(2)} · L: {quote.low?.toFixed(2)}
                </span>
                <span className="text-xs text-jay-textDim font-mono">
                  Vol: {(quote.volume / 1000).toFixed(0)}K
                </span>
              </div>
            )}
          </div>
          <button
            onClick={() => loadSymbolData(activeSymbol, activeExchange)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-jay-textDim hover:text-jay-accent border border-jay-border/40 hover:border-jay-accent/40 rounded-lg transition-colors"
          >
            <RefreshCw size={11} /> REFRESH
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-jay-border/30 pb-2">
          {(["indicators", "news", "portfolio", "backtest"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 text-[11px] font-mono rounded transition-all ${
                activeTab === tab
                  ? "bg-jay-accent/10 text-jay-accent border border-jay-accent/30"
                  : "text-jay-textDim hover:text-jay-text"
              }`}
            >
              {tab.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "indicators" && indicators && (
            <div className="grid grid-cols-2 gap-4">
              {/* Gauges */}
              <div className="space-y-3">
                <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-1">OSCILLATORS</div>
                <IndicatorGauge label="RSI (14)" value={indicators.rsi_14} min={0} max={100} />
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-3">
                  {[
                    ["MACD", indicators.macd?.toFixed(4)],
                    ["Signal", indicators.macd_signal?.toFixed(4)],
                    ["Histogram", indicators.macd_hist?.toFixed(4)],
                    ["ATR (14)", indicators.atr_14?.toFixed(2)],
                    ["EMA 20", indicators.ema_20?.toFixed(2)],
                    ["EMA 50", indicators.ema_50?.toFixed(2)],
                    ["BB Upper", indicators.bb_upper?.toFixed(2)],
                    ["BB Lower", indicators.bb_lower?.toFixed(2)],
                    ["VWAP", indicators.vwap?.toFixed(2)],
                  ].map(([label, val]) => (
                    <div key={label} className="flex justify-between">
                      <span className="text-[11px] text-jay-textDim font-mono">{label}</span>
                      <span className="text-[11px] text-jay-text font-mono">{val}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Signals */}
              <div>
                <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-3">AI SIGNALS</div>
                {indicators.signals?.length === 0 ? (
                  <div className="text-[11px] text-jay-textMuted">No strong signals detected</div>
                ) : (
                  <div className="space-y-2">
                    {indicators.signals?.map((s, i) => (
                      <div key={i} className="flex items-center justify-between bg-jay-surface/30 border border-jay-border/30 rounded-lg px-3 py-2">
                        <span className="text-[11px] font-mono text-jay-textDim">{s.indicator}</span>
                        <SignalBadge signal={s.signal} strength={s.strength} />
                        <span className="text-[9px] text-jay-textMuted">{s.strength}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Disclaimer */}
                <div className="mt-4 p-2 bg-jay-surface/20 border border-jay-orange/20 rounded-lg">
                  <p className="text-[10px] text-jay-orange/80 font-mono">
                    ⚠️ DISCLAIMER: Signals are probabilistic, not guarantees. Always use proper risk management. Past performance does not predict future results.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "news" && (
            <div className="space-y-3">
              {news.length === 0 ? (
                <div className="text-center text-jay-textMuted text-sm py-8">
                  Loading news for {activeSymbol}…
                </div>
              ) : (
                news.map((article: any, i: number) => (
                  <motion.a
                    key={i}
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="block p-3 bg-jay-surface/30 border border-jay-border/30 hover:border-jay-accent/30 rounded-lg transition-colors group"
                  >
                    <div className="text-sm font-semibold text-jay-text group-hover:text-jay-accent mb-1 transition-colors">
                      {article.title}
                    </div>
                    <div className="text-xs text-jay-textDim line-clamp-2">{article.body}</div>
                    <div className="text-[10px] text-jay-textMuted mt-1">
                      {article.source} · {article.date}
                    </div>
                  </motion.a>
                ))
              )}
            </div>
          )}

          {activeTab === "portfolio" && portfolio && (
            <div className="space-y-4">
              {/* Portfolio summary */}
              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: "Total Value", value: `₹${portfolio.total_value?.toLocaleString()}`, color: "#00d4ff" },
                  { label: "Cash", value: `₹${portfolio.cash?.toLocaleString()}`, color: "#22c55e" },
                  { label: "Total P&L", value: `₹${portfolio.total_pnl?.toFixed(2)}`, color: portfolio.total_pnl >= 0 ? "#22c55e" : "#ef4444" },
                  { label: "P&L %", value: `${portfolio.total_pnl_pct?.toFixed(2)}%`, color: portfolio.total_pnl_pct >= 0 ? "#22c55e" : "#ef4444" },
                ].map((item) => (
                  <div key={item.label} className="bg-jay-surface/30 border border-jay-border/30 rounded-lg p-3">
                    <div className="text-[10px] text-jay-textMuted font-mono mb-1">{item.label}</div>
                    <div className="text-sm font-mono font-bold" style={{ color: item.color }}>{item.value}</div>
                  </div>
                ))}
              </div>

              {/* Open positions */}
              <div>
                <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-2">OPEN POSITIONS ({portfolio.open_positions})</div>
                {portfolio.positions?.length === 0 ? (
                  <div className="text-sm text-jay-textMuted text-center py-4">No open positions</div>
                ) : (
                  <div className="space-y-2">
                    {portfolio.positions?.map((pos: any) => (
                      <div key={pos.id} className="flex items-center justify-between bg-jay-surface/30 border border-jay-border/30 rounded-lg px-3 py-2">
                        <div>
                          <span className="text-xs font-mono font-semibold text-jay-text">{pos.symbol}</span>
                          <span className={`ml-2 text-[10px] font-mono px-1 rounded ${pos.direction === "long" ? "text-jay-green bg-jay-green/10" : "text-jay-red bg-jay-red/10"}`}>
                            {pos.direction.toUpperCase()}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="text-xs font-mono text-jay-text">Entry: {pos.entry_price?.toFixed(2)}</div>
                          <PnLBadge value={pos.pnl_pct || 0} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "backtest" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-mono text-jay-textDim mb-1 block">STRATEGY</label>
                  <select
                    value={backtestConfig.strategy}
                    onChange={(e) => setBacktestConfig((c) => ({ ...c, strategy: e.target.value }))}
                    className="w-full bg-jay-surface border border-jay-border/50 rounded px-2 py-1.5 text-xs font-mono text-jay-text outline-none focus:border-jay-accent/60"
                  >
                    <option value="rsi_reversal">RSI Reversal</option>
                    <option value="ema_crossover">EMA Crossover</option>
                    <option value="macd_crossover">MACD Crossover</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-mono text-jay-textDim mb-1 block">PERIOD</label>
                  <select
                    value={backtestConfig.period}
                    onChange={(e) => setBacktestConfig((c) => ({ ...c, period: e.target.value }))}
                    className="w-full bg-jay-surface border border-jay-border/50 rounded px-2 py-1.5 text-xs font-mono text-jay-text outline-none focus:border-jay-accent/60"
                  >
                    {["3mo", "6mo", "1y", "2y", "5y"].map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={runBacktest}
                disabled={loading}
                className="w-full py-2 bg-jay-accent/10 border border-jay-accent/30 hover:bg-jay-accent/20 text-jay-accent text-sm font-mono rounded-lg transition-colors disabled:opacity-50"
              >
                {loading ? "Running backtest…" : `Run Backtest: ${activeSymbol}`}
              </button>

              {backtestResult && !backtestResult.error && (
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { label: "Total P&L", value: `${backtestResult.total_pnl_pct?.toFixed(2)}%`, pos: backtestResult.total_pnl_pct >= 0 },
                    { label: "Win Rate", value: `${backtestResult.win_rate?.toFixed(1)}%`, pos: backtestResult.win_rate >= 50 },
                    { label: "Max Drawdown", value: `${backtestResult.max_drawdown_pct?.toFixed(2)}%`, pos: false },
                    { label: "Sharpe Ratio", value: backtestResult.sharpe_ratio?.toFixed(2), pos: backtestResult.sharpe_ratio >= 1 },
                    { label: "Total Trades", value: backtestResult.total_trades, pos: true },
                    { label: "Avg Win", value: `₹${backtestResult.avg_win?.toFixed(0)}`, pos: true },
                  ].map(({ label, value, pos }) => (
                    <div key={label} className="bg-jay-surface/30 border border-jay-border/30 rounded-lg p-2">
                      <div className="text-[10px] text-jay-textMuted font-mono">{label}</div>
                      <div className={`text-sm font-mono font-bold mt-0.5 ${pos ? "text-jay-green" : "text-jay-red"}`}>{value}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
