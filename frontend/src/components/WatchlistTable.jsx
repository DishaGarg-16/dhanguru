import React from 'react';
import { UrgencyBadge } from './atoms/UrgencyBadge';
import { CircuitProximityBar } from './atoms/CircuitProximityBar';
import { Sparkline } from './atoms/Sparkline';
import { TrendingUp, TrendingDown, Trash2, ArrowRight } from 'lucide-react';

export function WatchlistTable({ items, onSelectStock, onRemoveStock }) {
  if (!items || items.length === 0) {
    return (
      <div
        className="glass-card"
        style={{
          padding: '48px 24px',
          textAlign: 'center',
          color: '#94A3B8',
        }}
      >
        <p style={{ fontSize: '14px', fontWeight: 500 }}>No stocks match your filter criteria.</p>
        <p style={{ fontSize: '12px', color: '#64748B', marginTop: '6px' }}>
          Try clearing search or adding stocks to your watchlist.
        </p>
      </div>
    );
  }

  const formatVolume = (vol) => {
    if (vol >= 10000000) {
      return `${(vol / 10000000).toFixed(2)} Cr`;
    } else if (vol >= 100000) {
      return `${(vol / 100000).toFixed(2)} L`;
    }
    return vol.toLocaleString('en-IN');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {items.map((stock) => {
        const isPos = stock.change >= 0;
        const changeColor = isPos ? 'var(--emerald-green)' : 'var(--ruby-red)';

        return (
          <div
            key={stock.symbol}
            className="glass-card"
            style={{
              padding: '16px 20px',
              display: 'grid',
              gridTemplateColumns: 'minmax(200px, 1.4fr) minmax(180px, 1fr) minmax(160px, 1fr)',
              alignItems: 'center',
              gap: '20px',
              cursor: 'pointer',
              position: 'relative',
              borderRadius: '12px',
            }}
            onClick={() => onSelectStock(stock)}
          >
            {/* 1. Left: Symbol, Company & Human Signal Badges */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  className="font-mono"
                  style={{
                    fontSize: '15px',
                    fontWeight: 800,
                    color: '#FFF',
                    letterSpacing: '-0.02em',
                  }}
                >
                  {stock.symbol}
                </span>
                <span style={{ fontSize: '11px', color: '#64748B' }}>•</span>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {stock.company_name}
                </span>
              </div>

              {/* Human-translated signal badges */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                {stock.signals && stock.signals.length > 0 ? (
                  stock.signals.map((sig, sIdx) => {
                    let pillStyle = {
                      bg: 'rgba(255, 255, 255, 0.04)',
                      text: '#94A3B8',
                      border: 'rgba(255, 255, 255, 0.08)',
                    };

                    if (sig.badge_color === 'green') {
                      pillStyle = {
                        bg: 'var(--emerald-green-soft)',
                        text: 'var(--emerald-green)',
                        border: 'rgba(0, 208, 156, 0.25)',
                      };
                    } else if (sig.badge_color === 'red') {
                      pillStyle = {
                        bg: 'var(--ruby-red-soft)',
                        text: 'var(--ruby-red)',
                        border: 'rgba(235, 91, 86, 0.25)',
                      };
                    } else if (sig.badge_color === 'circuit') {
                      pillStyle = {
                        bg: 'var(--circuit-orange-soft)',
                        text: 'var(--circuit-orange)',
                        border: 'rgba(255, 107, 74, 0.35)',
                      };
                    }

                    return (
                      <span
                        key={sIdx}
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '6px',
                          backgroundColor: pillStyle.bg,
                          color: pillStyle.text,
                          border: `1px solid ${pillStyle.border}`,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        {sig.headline}
                      </span>
                    );
                  })
                ) : (
                  <span
                    style={{
                      fontSize: '11px',
                      color: '#64748B',
                      backgroundColor: 'rgba(255, 255, 255, 0.02)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                    }}
                  >
                    Normal Daily Drift
                  </span>
                )}
              </div>
            </div>

            {/* 2. Middle: Circuit Limits & Volume Indicator */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <CircuitProximityBar
                currentPrice={stock.current_price}
                lowerCircuit={stock.lower_circuit}
                upperCircuit={stock.upper_circuit}
                isNearUpper={stock.is_near_upper_circuit}
                isNearLower={stock.is_near_lower_circuit}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748B' }}>
                <span>Vol: <strong style={{ color: '#94A3B8' }}>{formatVolume(stock.volume)}</strong></span>
                <span>RVol: <strong style={{ color: stock.rvol >= 2.0 ? 'var(--emerald-green)' : '#94A3B8' }}>{stock.rvol}x</strong></span>
              </div>
            </div>

            {/* 3. Right: Live Price, % Change & Attention Meter */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: '18px',
              }}
            >
              <div style={{ textAlign: 'right' }}>
                <div
                  className="font-mono"
                  style={{
                    fontSize: '16px',
                    fontWeight: 700,
                    color: '#FFF',
                  }}
                >
                  ₹{typeof stock.current_price === 'number'
                    ? stock.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : stock.current_price}
                </div>
                <div
                  className="font-mono"
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: changeColor,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: '2px',
                    marginTop: '2px',
                  }}
                >
                  {isPos ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                  <span>
                    {isPos ? '+' : ''}₹{typeof stock.change === 'number' ? stock.change.toFixed(2) : stock.change} ({isPos ? '+' : ''}{typeof stock.change_percent === 'number' ? stock.change_percent.toFixed(2) : stock.change_percent}%)
                  </span>
                </div>
              </div>

              {/* Urgency Badge */}
              <UrgencyBadge score={stock.urgency_score} />

              {/* Delete / Remove Action */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveStock(stock.symbol);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#64748B',
                  padding: '6px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'color 0.15s ease',
                }}
                title="Remove from watchlist"
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--ruby-red)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#64748B')}
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
