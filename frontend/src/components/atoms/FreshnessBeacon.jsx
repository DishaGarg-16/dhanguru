import React from 'react';

export function FreshnessBeacon({
  connectionStatus = 'CONNECTED',
  marketSession,
  lastUpdated,
  provider = 'NSE Feed',
}) {
  const isConnected = connectionStatus === 'CONNECTED';
  const isMarketLive = marketSession?.is_open ?? true;

  let config = {
    dot: '#00D09C',
    text: '#00D09C',
    bg: 'rgba(0, 208, 156, 0.1)',
    border: 'rgba(0, 208, 156, 0.25)',
    label: isMarketLive ? 'LIVE STREAM' : 'SIMULATED FEED',
    pulse: true,
  };

  if (!isConnected) {
    config = {
      dot: '#EB5B56',
      text: '#EB5B56',
      bg: 'rgba(235, 91, 86, 0.1)',
      border: 'rgba(235, 91, 86, 0.25)',
      label: 'RECONNECTING',
      pulse: true,
    };
  } else if (!isMarketLive) {
    config = {
      dot: '#FFB300',
      text: '#FFB300',
      bg: 'rgba(255, 179, 0, 0.1)',
      border: 'rgba(255, 179, 0, 0.25)',
      label: marketSession?.status || 'MARKET CLOSED',
      pulse: false,
    };
  }

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '5px 12px',
        borderRadius: '999px',
        fontSize: '11px',
        fontWeight: 600,
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        color: config.text,
      }}
      title={marketSession?.reason || 'Real-time WebSocket connection active'}
    >
      <span
        style={{
          width: '7px',
          height: '7px',
          borderRadius: '50%',
          backgroundColor: config.dot,
        }}
        className={config.pulse ? 'animate-pulse-dot' : ''}
      />
      <span>{config.label}</span>
      <span style={{ color: '#64748B', fontWeight: 400 }}>•</span>
      <span style={{ color: '#94A3B8', fontWeight: 500 }}>{provider}</span>
      {marketSession?.ist_time && (
        <span style={{ color: '#64748B', fontSize: '10px' }}>
          ({marketSession.ist_time})
        </span>
      )}
    </div>
  );
}
