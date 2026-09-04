import React from 'react';
import { X, Shield, Activity, TrendingUp, TrendingDown, Layers, Zap } from 'lucide-react';
import { UrgencyBadge } from './atoms/UrgencyBadge';
import { CircuitProximityBar } from './atoms/CircuitProximityBar';

export function AssetDetailDrawer({ stock, onClose }) {
  if (!stock) return null;

  const isPos = stock.change >= 0;
  const changeColor = isPos ? 'var(--emerald-green)' : 'var(--ruby-red)';

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(3px)',
        zIndex: 1050,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          height: '100%',
          backgroundColor: '#11151D',
          borderLeft: '1px solid #232C3A',
          padding: '28px 24px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Close & Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 className="font-mono" style={{ fontSize: '20px', fontWeight: 800, color: '#FFF' }}>
                {stock.symbol}
              </h2>
              <span style={{ fontSize: '11px', color: '#64748B' }}>• {stock.exchange || 'NSE'}</span>
            </div>
            <div style={{ fontSize: '13px', color: '#94A3B8', marginTop: '2px' }}>
              {stock.company_name}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Price & Urgency Card */}
        <div
          className="glass-card"
          style={{
            padding: '18px',
            backgroundColor: '#161C26',
            borderRadius: '12px',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <div>
              <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>CURRENT PRICE</span>
              <div className="font-mono" style={{ fontSize: '24px', fontWeight: 800, color: '#FFF' }}>
                ₹{stock.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div
                className="font-mono"
                style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  color: changeColor,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  marginTop: '2px',
                }}
              >
                {isPos ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                <span>
                  {isPos ? '+' : ''}₹{stock.change.toFixed(2)} ({isPos ? '+' : ''}{stock.change_percent.toFixed(2)}%)
                </span>
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                ATTENTION SCORE
              </span>
              <UrgencyBadge score={stock.urgency_score} />
            </div>
          </div>
        </div>

        {/* Circuit Limits Section */}
        <div style={{ marginBottom: '22px' }}>
          <h4 style={{ fontSize: '12px', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '10px' }}>
            Exchange Circuit Bands (NSE)
          </h4>
          <div className="glass-card" style={{ padding: '16px', backgroundColor: '#161C26' }}>
            <CircuitProximityBar
              currentPrice={stock.current_price}
              lowerCircuit={stock.lower_circuit}
              upperCircuit={stock.upper_circuit}
              isNearUpper={stock.is_near_upper_circuit}
              isNearLower={stock.is_near_lower_circuit}
            />
            <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94A3B8' }}>
              <span>Lower Circuit: ₹{stock.lower_circuit?.toLocaleString('en-IN')}</span>
              <span>Upper Circuit: ₹{stock.upper_circuit?.toLocaleString('en-IN')}</span>
            </div>
          </div>
        </div>

        {/* Quantitative Signals & Anomalies */}
        <div style={{ marginBottom: '22px' }}>
          <h4 style={{ fontSize: '12px', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '10px' }}>
            Detected Signals & Structural Drivers
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {stock.signals && stock.signals.length > 0 ? (
              stock.signals.map((sig, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: '#161C26',
                    border: '1px solid #232C3A',
                    borderRadius: '10px',
                    padding: '12px 14px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 600, color: '#FFF' }}>
                    <Zap size={14} color="var(--emerald-green)" />
                    <span>{sig.headline}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '4px' }}>
                    {sig.technical_detail}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ fontSize: '12px', color: '#64748B', padding: '12px', backgroundColor: '#161C26', borderRadius: '10px' }}>
                No outlier anomalies detected. Operating within normal 14-day ATR volatility bands.
              </div>
            )}
          </div>
        </div>

        {/* 52-Week Range & Volume Context */}
        <div>
          <h4 style={{ fontSize: '12px', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', marginBottom: '10px' }}>
            Market Structure (52-Week Range)
          </h4>
          <div className="glass-card" style={{ padding: '16px', backgroundColor: '#161C26', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: '#64748B' }}>52-Week High:</span>
              <span className="font-mono" style={{ color: '#FFF', fontWeight: 600 }}>₹{stock.week_52_high?.toLocaleString('en-IN')}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: '#64748B' }}>52-Week Low:</span>
              <span className="font-mono" style={{ color: '#FFF', fontWeight: 600 }}>₹{stock.week_52_low?.toLocaleString('en-IN')}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: '#64748B' }}>Relative Volume (RVol):</span>
              <span className="font-mono" style={{ color: stock.rvol >= 2.0 ? 'var(--emerald-green)' : '#FFF', fontWeight: 600 }}>
                {stock.rvol}x
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
