import React from 'react';

export function UrgencyBadge({ score, label, showLabel = true }) {
  let themeClass = {
    bg: 'rgba(148, 163, 184, 0.1)',
    text: '#94A3B8',
    border: 'rgba(148, 163, 184, 0.2)',
    dot: '#94A3B8',
    pulse: false,
    textLabel: 'CALM',
  };

  if (score >= 80) {
    themeClass = {
      bg: 'rgba(235, 91, 86, 0.15)',
      text: '#EB5B56',
      border: 'rgba(235, 91, 86, 0.3)',
      dot: '#EB5B56',
      pulse: true,
      textLabel: 'CRITICAL',
    };
  } else if (score >= 60) {
    themeClass = {
      bg: 'rgba(255, 179, 0, 0.15)',
      text: '#FFB300',
      border: 'rgba(255, 179, 0, 0.3)',
      dot: '#FFB300',
      pulse: true,
      textLabel: 'ATTENTION',
    };
  } else if (score >= 40) {
    themeClass = {
      bg: 'rgba(0, 208, 156, 0.12)',
      text: '#00D09C',
      border: 'rgba(0, 208, 156, 0.25)',
      dot: '#00D09C',
      pulse: false,
      textLabel: 'MODERATE',
    };
  }

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '3px 8px',
        borderRadius: '6px',
        fontSize: '11px',
        fontWeight: 600,
        backgroundColor: themeClass.bg,
        color: themeClass.text,
        border: `1px solid ${themeClass.border}`,
        userSelect: 'none',
      }}
      title={`Urgency Score: ${score}/100`}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: themeClass.dot,
        }}
        className={themeClass.pulse ? 'animate-pulse-dot' : ''}
      />
      <span>{label || `${score}/100`}</span>
      {showLabel && (
        <span style={{ fontSize: '9px', opacity: 0.8, textTransform: 'uppercase' }}>
          {themeClass.textLabel}
        </span>
      )}
    </div>
  );
}
