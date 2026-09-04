import React, { useState, useEffect } from 'react';
import { FreshnessBeacon } from './components/atoms/FreshnessBeacon';
import { UrgencyBadge } from './components/atoms/UrgencyBadge';
import { CircuitProximityBar } from './components/atoms/CircuitProximityBar';
import { Sparkline } from './components/atoms/Sparkline';
import { Activity, Shield, TrendingUp, Zap, Clock, AlertTriangle } from 'lucide-react';

export default function App() {
  const [backendHealth, setBackendHealth] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Poll backend health & tickers to verify frontend-to-backend proxy
  useEffect(() => {
    async function fetchData() {
      try {
        const healthRes = await fetch('/health');
        if (healthRes.ok) {
          const hData = await healthRes.json();
          setBackendHealth(hData);
        }

        const marketRes = await fetch('/api/market/tickers');
        if (marketRes.ok) {
          const mData = await marketRes.json();
          setMarketData(mData);
        }
      } catch (err) {
        console.error('Failed to fetch backend data:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const benchmark = marketData?.benchmark;
  const isBenchPos = (benchmark?.change_percent ?? 0) >= 0;

  return (
    <div style={{ minHeight: '100vh', padding: '24px 32px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Top Navigation Bar */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          paddingBottom: '24px',
          borderBottom: '1px solid var(--border-subtle)',
          marginBottom: '28px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              backgroundColor: 'var(--emerald-green-soft)',
              border: '1px solid rgba(0, 208, 156, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--emerald-green)',
            }}
          >
            <Zap size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.03em' }}>
                DHANGURU
              </h1>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  backgroundColor: '#1E2738',
                  color: '#94A3B8',
                  padding: '2px 6px',
                  borderRadius: '4px',
                }}
              >
                PROTOTYPE v0.1
              </span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Autonomous Market Intelligence Co-Pilot
            </p>
          </div>
        </div>

        {/* Center: Live Benchmark Banner */}
        {benchmark && (
          <div
            className="glass-card"
            style={{
              padding: '6px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '12px',
            }}
          >
            <span style={{ fontWeight: 700, color: '#94A3B8' }}>{benchmark.symbol}</span>
            <span className="font-mono" style={{ fontWeight: 700 }}>
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

        {/* Right: Freshness Beacon */}
        <FreshnessBeacon
          status={backendHealth ? 'LIVE' : 'OFFLINE'}
          provider="FastAPI Engine"
          lastUpdated={new Date()}
        />
      </header>

      {/* Phase 4 Foundation Showcase */}
      <section style={{ marginBottom: '32px' }}>
        <div
          className="glass-card"
          style={{
            padding: '24px',
            background: 'linear-gradient(135deg, rgba(20, 26, 36, 0.9) 0%, rgba(15, 20, 28, 0.9) 100%)',
            border: '1px solid rgba(0, 208, 156, 0.2)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#FFF' }}>
                Phase 4: Design System & Core UI Atoms
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Verified end-to-end communication between React + Vite frontend and FastAPI backend.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  backgroundColor: backendHealth ? 'var(--emerald-green-soft)' : 'var(--ruby-red-soft)',
                  color: backendHealth ? 'var(--emerald-green)' : 'var(--ruby-red)',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: `1px solid ${backendHealth ? 'rgba(0, 208, 156, 0.3)' : 'rgba(235, 91, 86, 0.3)'}`,
                }}
              >
                Backend: {backendHealth ? 'CONNECTED (Port 8000)' : 'CONNECTING...'}
              </span>
            </div>
          </div>

          {/* Component Atoms Showcase Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '16px',
              marginTop: '18px',
            }}
          >
            {/* Atom 1: Urgency Badges */}
            <div className="glass-card" style={{ padding: '16px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                1. DYNAMIC URGENCY BADGES
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
                <UrgencyBadge score={92} />
                <UrgencyBadge score={65} />
                <UrgencyBadge score={45} />
                <UrgencyBadge score={15} />
              </div>
            </div>

            {/* Atom 2: Circuit Band Proximity */}
            <div className="glass-card" style={{ padding: '16px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                2. CIRCUIT PROXIMITY METER (NSE BANDS)
              </span>
              <div style={{ marginTop: '12px' }}>
                <CircuitProximityBar
                  currentPrice={7530}
                  lowerCircuit={6840}
                  upperCircuit={7560}
                  isNearUpper={true}
                />
              </div>
            </div>

            {/* Atom 3: Micro Sparklines */}
            <div className="glass-card" style={{ padding: '16px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                3. FAST MICRO SPARKLINES
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '12px' }}>
                <Sparkline data={[250, 252, 251, 258, 256, 262, 264]} isPositive={true} />
                <Sparkline data={[985, 980, 978, 970, 974, 965, 962]} isPositive={false} />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
