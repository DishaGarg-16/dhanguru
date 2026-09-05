import React from 'react';

export function CircuitProximityBar({
  currentPrice,
  lowerCircuit,
  upperCircuit,
  isNearUpper,
  isNearLower,
}) {
  if (!lowerCircuit || !upperCircuit || upperCircuit <= lowerCircuit) {
    return null;
  }

  // Calculate percentage progress between lower and upper band
  const totalRange = upperCircuit - lowerCircuit;
  const progress = Math.min(100, Math.max(0, ((currentPrice - lowerCircuit) / totalRange) * 100));

  let statusBadge = null;
  if (isNearUpper) {
    statusBadge = (
      <span
        style={{
          fontSize: '10px',
          fontWeight: 700,
          color: '#FF6B4A',
          backgroundColor: 'rgba(255, 107, 74, 0.15)',
          padding: '2px 6px',
          borderRadius: '4px',
          border: '1px solid rgba(255, 107, 74, 0.3)',
        }}
      >
        Near Upper Limit
      </span>
    );
  } else if (isNearLower) {
    statusBadge = (
      <span
        style={{
          fontSize: '10px',
          fontWeight: 700,
          color: '#EB5B56',
          backgroundColor: 'rgba(235, 91, 86, 0.15)',
          padding: '2px 6px',
          borderRadius: '4px',
          border: '1px solid rgba(235, 91, 86, 0.3)',
        }}
      >
        Near Lower Limit
      </span>
    );
  }

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10px', color: '#94A3B8' }}>
        <span>LC: ₹{lowerCircuit.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</span>
        {statusBadge}
        <span>UC: ₹{upperCircuit.toLocaleString('en-IN', { maximumFractionDigits: 1 })}</span>
      </div>

      <div
        style={{
          position: 'relative',
          height: '5px',
          backgroundColor: '#202938',
          borderRadius: '999px',
          overflow: 'visible',
        }}
      >
        {/* Track fill */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: `${progress}%`,
            backgroundColor: isNearUpper ? '#FF6B4A' : isNearLower ? '#EB5B56' : '#00D09C',
            borderRadius: '999px',
            opacity: 0.8,
          }}
        />

        {/* Current price pin */}
        <div
          style={{
            position: 'absolute',
            left: `${progress}%`,
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: '9px',
            height: '9px',
            borderRadius: '50%',
            backgroundColor: '#FFF',
            boxShadow: '0 0 4px rgba(0, 0, 0, 0.5)',
            border: '1.5px solid #0B0E14',
          }}
          title={`Price: ₹${currentPrice} (${progress.toFixed(0)}% of band)`}
        />
      </div>
    </div>
  );
}
