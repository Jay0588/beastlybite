"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search, Globe, ExternalLink, RefreshCw } from "lucide-react";
import { toolsAPI } from "@/lib/api";
import ReactMarkdown from "react-markdown";

export default function ResearchPanel() {
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [fetchedContent, setFetchedContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"search" | "fetch">("search");

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResults([]);
    try {
      const result = await toolsAPI.execute("web_search", { query, max_results: 8 }, true);
      if (result.success) {
        setResults(result.results || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleFetch = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setFetchedContent("");
    try {
      const result = await toolsAPI.execute("fetch_url", { url }, true);
      if (result.success) {
        setFetchedContent(result.output);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Tabs */}
      <div className="flex gap-2">
        {(["search", "fetch"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 text-[11px] font-mono rounded-lg transition-all ${
              activeTab === tab
                ? "bg-jay-accent/10 text-jay-accent border border-jay-accent/30"
                : "text-jay-textDim hover:text-jay-text"
            }`}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {activeTab === "search" ? (
        <>
          <div className="flex gap-2">
            <div className="flex-1 flex gap-2 items-center bg-jay-surface border border-jay-border/50 rounded-xl px-3 py-2 focus-within:border-jay-accent/50">
              <Search size={14} className="text-jay-textMuted flex-shrink-0" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search the web…"
                className="flex-1 bg-transparent text-sm text-jay-text placeholder-jay-textMuted outline-none"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading}
              className="px-4 py-2 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20 rounded-xl text-sm font-mono transition-colors disabled:opacity-50"
            >
              {loading ? <RefreshCw size={14} className="animate-spin" /> : "SEARCH"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3">
            {results.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-4 bg-jay-surface/30 border border-jay-border/30 hover:border-jay-accent/30 rounded-xl transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-semibold text-jay-accent hover:text-jay-text transition-colors block truncate"
                    >
                      {r.title}
                    </a>
                    <p className="text-xs text-jay-textDim mt-1 leading-relaxed line-clamp-3">{r.snippet}</p>
                    <div className="flex items-center gap-1.5 mt-2">
                      <Globe size={10} className="text-jay-textMuted" />
                      <span className="text-[10px] text-jay-textMuted truncate">{r.url}</span>
                    </div>
                  </div>
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-jay-textMuted hover:text-jay-accent flex-shrink-0">
                    <ExternalLink size={14} />
                  </a>
                </div>
                <button
                  onClick={() => { setUrl(r.url); setActiveTab("fetch"); handleFetch(); }}
                  className="mt-2 text-[10px] font-mono text-jay-textDim hover:text-jay-accent transition-colors"
                >
                  READ FULL PAGE →
                </button>
              </motion.div>
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="flex gap-2">
            <div className="flex-1 flex gap-2 items-center bg-jay-surface border border-jay-border/50 rounded-xl px-3 py-2 focus-within:border-jay-accent/50">
              <Globe size={14} className="text-jay-textMuted flex-shrink-0" />
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleFetch()}
                placeholder="https://example.com"
                className="flex-1 bg-transparent text-sm font-mono text-jay-text placeholder-jay-textMuted outline-none"
              />
            </div>
            <button
              onClick={handleFetch}
              disabled={loading}
              className="px-4 py-2 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20 rounded-xl text-sm font-mono transition-colors disabled:opacity-50"
            >
              {loading ? <RefreshCw size={14} className="animate-spin" /> : "FETCH"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {fetchedContent ? (
              <div className="prose prose-invert prose-sm max-w-none p-4 bg-jay-surface/20 border border-jay-border/30 rounded-xl">
                <ReactMarkdown>{fetchedContent}</ReactMarkdown>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-jay-textMuted text-sm">
                Enter a URL to fetch its content
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
