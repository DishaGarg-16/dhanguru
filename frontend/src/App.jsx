import React, { useState, useEffect, useCallback } from 'react';
import { FreshnessBeacon } from './components/atoms/FreshnessBeacon';
import { ExecutiveBriefingCard } from './components/ExecutiveBriefingCard';
import { TimeTravelScrubber } from './components/TimeTravelScrubber';
import { WatchlistTable } from './components/WatchlistTable';
import { AddSymbolModal } from './components/AddSymbolModal';
import { AssetDetailDrawer } from './components/AssetDetailDrawer';
import { Zap, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

export default function App() {
  const [watchlistData, setWatchlistData] = useState(null);
  const [briefing, setBriefing] = useState(null);
  const [selectedWindow, setSelectedWindow] = useState('since_last');
  const [filterHighAttention, setFilterHighAttention] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [acknowledging, setAcknowledging] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch Watchlist
  const fetchWatchlist = useCallback(async () => {
    try {
      const res = await fetch('/api/watchlist');
      if (res.ok) {
        const data = await res.json();
        setWatchlistData(data);
      }
    } catch (err) {
      console.error('Failed to fetch watchlist:', err);
    }
  }, []);

  // Fetch Executive Briefing
  const fetchBriefing = useCallback(async (windowId = selectedWindow) => {
    try {
      let url = '/api/briefing/since-last';
      if (windowId === '15m') url = '/api/briefing/window?minutes_ago=15';
      else if (windowId === '1h') url = '/api/briefing/window?minutes_ago=60';
      else if (windowId === '3h') url = '/api/briefing/window?minutes_ago=180';

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setBriefing(data);
      }
    } catch (err) {
      console.error('Failed to fetch briefing:', err);
    }
  }, [selectedWindow]);

  // Initial load and polling every 2.5 seconds
  useEffect(() => {
    fetchWatchlist();
    fetchBriefing();

    const interval = setInterval(() => {
      fetchWatchlist();
    }, 2500);

    return () => clearInterval(interval);
  }, [fetchWatchlist, fetchBriefing]);

  // Handle window change in Time-Travel Scrubber
  const handleSelectWindow = (winId) => {
    setSelectedWindow(winId);
    fetchBriefing(winId);
  };

  // Handle 1-Click Acknowledge
  const handleAcknowledge = async () => {
    setAcknowledging(true);
    try {
      const res = await fetch('/api/watchlist/acknowledge', { method: 'POST' });
      if (res.ok) {
        await fetchWatchlist();
        await fetchBriefing('since_last');
        setSelectedWindow('since_last');
      }
    } catch (err) {
      console.error('Acknowledge failed:', err);
    } finally {
      setAcknowledging(false);
    }
  };

  // Handle Add Symbol
  const handleAddSymbol = async (symbol) => {
    try {
      const res = await fetch('/api/watchlist/symbols', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol }),
      });
      if (res.ok) {
        setIsAddModalOpen(false);
        await fetchWatchlist();
        await fetchBriefing();
      }
    } catch (err) {
      console.error('Failed to add symbol:', err);
    }
  };

  // Handle Remove Symbol
  const handleRemoveStock = async (symbol) => {
    try {
      const res = await fetch(`/api/watchlist/symbols/${symbol}`, { method: 'DELETE' });
      if (res.ok) {
        await fetchWatchlist();
        await fetchBriefing();
      }
    } catch (err) {
      console.error('Failed to remove symbol:', err);
    }
  };

  // Filter stocks based on search query & high-attention filter
  const items = watchlistData?.items || [];
  const filteredItems = items.filter((stock) => {
    const matchesSearch =
      stock.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stock.company_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesAttention = filterHighAttention ? stock.requires_attention : true;
    return matchesSearch && matchesAttention;
  });

  const benchmark = watchlistData?.benchmark;
  const isBenchPos = (benchmark?.change_percent ?? 0) >= 0;

  return (
    <div style={{ minHeight: '100vh', padding: '24px 32px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Top Navbar */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          paddingBottom: '20px',
          borderBottom: '1px solid var(--border-subtle)',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              backgroundColor: 'var(--emerald-green-soft)',
              border: '1px solid rgba(0, 208, 156, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--emerald-green)',
            }}
          >
            <Zap size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.03em', color: '#FFF' }}>
                DHANGURU
              </h1>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  backgroundColor: '#1E2738',
                  color: 'var(--emerald-green)',
                  padding: '2px 7px',
                  borderRadius: '4px',
                  border: '1px solid rgba(0, 208, 156, 0.2)',
                }}
              >
                NSE LIVE
              </span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Autonomous Market Watchlist & Delta Intelligence
            </p>
          </div>
        </div>

        {/* Live NIFTY 50 Benchmark Card */}
        {benchmark && (
          <div
            className="glass-card"
            style={{
              padding: '6px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '12px',
            }}
          >
            <span style={{ fontWeight: 700, color: '#94A3B8' }}>{benchmark.symbol}</span>
            <span className="font-mono" style={{ fontWeight: 700, color: '#FFF' }}>
              {benchmark.current_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
            </span>
            <span
              className="font-mono"
              style={{
                fontWeight: 600,
                color: isBenchPos ? 'var(--emerald-green)' : 'var(--ruby-red)',
              }}
            >
              {isBenchPos ? '+' : ''}
              {benchmark.change_percent.toFixed(2)}%
            </span>
          </div>
        )}

        {/* Right Status Beacon */}
        <FreshnessBeacon
          status="LIVE"
          provider="FastAPI Engine"
          lastUpdated={new Date()}
        />
      </header>

      {/* Flagship: "Since You Checked" Executive Briefing Card */}
      <ExecutiveBriefingCard
        briefing={briefing}
        onAcknowledge={handleAcknowledge}
        acknowledging={acknowledging}
      />

      {/* Time-Travel Scrubber Controls */}
      <TimeTravelScrubber
        selectedWindow={selectedWindow}
        onSelectWindow={handleSelectWindow}
        filterHighAttention={filterHighAttention}
        onToggleFilter={() => setFilterHighAttention(!filterHighAttention)}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onOpenAddModal={() => setIsAddModalOpen(true)}
        highAttentionCount={watchlistData?.high_attention_count || 0}
      />

      {/* Smart Watchlist Grid */}
      <WatchlistTable
        items={filteredItems}
        onSelectStock={(stock) => setSelectedStock(stock)}
        onRemoveStock={handleRemoveStock}
      />

      {/* Add Stock Modal */}
      <AddSymbolModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAddSymbol={handleAddSymbol}
        existingSymbols={watchlistData?.items?.map((i) => i.symbol) || []}
      />

      {/* Asset Deep-Dive Drawer */}
      <AssetDetailDrawer
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
      />
    </div>
  );
}
