import React from 'react';
import { Sparkles, Shield, Clock, CheckCircle, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';

export function ExecutiveBriefingCard({ briefing, onAcknowledge, acknowledging, loading }) {
  if (loading && !briefing) {
    return (
      <div
        className="glass-card"
        style={{
          background: 'linear-gradient(135deg, rgba(19, 26, 38, 0.95) 0%, rgba(13, 17, 24, 0.95) 100%)',
          border: '1px solid rgba(0, 208, 156, 0.25)',
          borderRadius: '16px',
          padding: '22px 26px',
          marginBottom: '28px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            backgroundColor: 'var(--emerald-green-soft)',
            color: 'var(--emerald-green)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            animation: 'pulse 1.5s infinite',
          }}
        >
          <Sparkles size={18} />
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: '#FFF' }}>
            AI Co-Pilot analyzing your watchlist delta...
          </div>
          <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
            Computing 14-day ATR volatility bands and Relative Volume surges...
          </div>
        </div>
      </div>
    );
  }

  if (!briefing) return null;

  const moodColor = {
    BULLISH: 'var(--emerald-green)',
    BEARISH: 'var(--ruby-red)',
    VOLATILE: 'var(--amber-gold)',
    CALM: '#94A3B8',
  }[briefing.market_mood] || '#94A3B8';

  return (
    <div
      className="glass-card"
      style={{
        background: 'linear-gradient(135deg, rgba(19, 26, 38, 0.95) 0%, rgba(13, 17, 24, 0.95) 100%)',
        border: '1px solid rgba(0, 208, 156, 0.25)',
        borderRadius: '16px',
        padding: '22px 26px',
        marginBottom: '28px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Glow highlight */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '2px',
          background: 'linear-gradient(90deg, transparent, var(--emerald-green), transparent)',
        }}
      />

      {/* Top Banner Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              backgroundColor: 'var(--emerald-green-soft)',
              color: 'var(--emerald-green)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={16} />
          </div>
          <h2 style={{ fontSize: '15px', fontWeight: 700, letterSpacing: '-0.02em', color: '#FFF' }}>
            Since You Checked
          </h2>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '999px',
              backgroundColor: 'rgba(255, 255, 255, 0.06)',
              color: '#94A3B8',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Clock size={12} /> Away for {briefing.time_away_human}
          </span>
        </div>

        {/* Market Mood Tag & AI Generator Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '6px',
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              border: `1px solid ${moodColor}40`,
              color: moodColor,
            }}
          >
            MARKET: {briefing.market_mood}
          </span>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 600,
              color: briefing.generated_by === 'AI_AGENT' ? 'var(--emerald-green)' : '#64748B',
              backgroundColor: briefing.generated_by === 'AI_AGENT' ? 'rgba(0, 208, 156, 0.1)' : 'rgba(255, 255, 255, 0.02)',
              border: briefing.generated_by === 'AI_AGENT' ? '1px solid rgba(0, 208, 156, 0.3)' : '1px solid transparent',
              padding: '3px 8px',
              borderRadius: '4px',
              transition: 'all 0.2s ease',
            }}
          >
            {briefing.generated_by === 'AI_AGENT' ? 'AI Co-Pilot' : 'Rule Engine Fallback'}
          </span>
        </div>
      </div>

      {/* Main Headline */}
      <p
        style={{
          fontSize: '16px',
          fontWeight: 600,
          color: '#F8FAFC',
          marginBottom: '16px',
          lineHeight: '1.4',
        }}
      >
        {briefing.headline}
      </p>

      {/* Structural Key Takeaways */}
      {briefing.key_takeaways && briefing.key_takeaways.length > 0 && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            marginBottom: '16px',
          }}
        >
          {briefing.key_takeaways.map((takeaway, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                fontSize: '13px',
                color: '#CBD5E1',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.04)',
              }}
            >
              <span style={{ color: 'var(--emerald-green)', marginTop: '2px', fontWeight: 700 }}>•</span>
              <span>{takeaway}</span>
            </div>
          ))}
        </div>
      )}

      {/* Responsible Investing / FOMO Guard Alert */}
      {briefing.fomo_guard_notice &&
        typeof briefing.fomo_guard_notice === 'string' &&
        briefing.fomo_guard_notice.trim().toLowerCase() !== 'null' &&
        briefing.fomo_guard_notice.trim().toLowerCase() !== 'none' && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '10px 14px',
            borderRadius: '10px',
            backgroundColor: 'rgba(255, 179, 0, 0.08)',
            border: '1px solid rgba(255, 179, 0, 0.25)',
            color: '#FCD34D',
            fontSize: '12px',
            marginBottom: '16px',
          }}
        >
          <Shield size={16} style={{ flexShrink: 0 }} />
          <span>{briefing.fomo_guard_notice}</span>
        </div>
      )}

      {/* One-Click Catch-Up Button */}
      <button
        onClick={onAcknowledge}
        disabled={acknowledging}
        style={{
          width: '100%',
          backgroundColor: '#1B2433',
          border: '1px solid #2B384E',
          color: '#F1F5F9',
          fontSize: '13px',
          fontWeight: 600,
          padding: '10px 16px',
          borderRadius: '10px',
          cursor: acknowledging ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          if (!acknowledging) e.currentTarget.style.backgroundColor = '#243145';
        }}
        onMouseLeave={(e) => {
          if (!acknowledging) e.currentTarget.style.backgroundColor = '#1B2433';
        }}
      >
        <CheckCircle size={15} color="var(--emerald-green)" />
        {acknowledging ? 'Syncing Checkpoint...' : 'Acknowledge & Mark All Caught Up'}
      </button>
    </div>
  );
}
