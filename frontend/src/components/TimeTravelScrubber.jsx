import React from 'react';
import { Clock, Filter, Plus, Search } from 'lucide-react';

export function TimeTravelScrubber({
  selectedWindow,
  onSelectWindow,
  filterHighAttention,
  onToggleFilter,
  searchQuery,
  onSearchChange,
  onOpenAddModal,
  highAttentionCount = 0,
}) {
  const windows = [
    { id: 'since_last', label: 'Since Last Visit' },
    { id: '15m', label: 'Past 15m', minutes: 15 },
    { id: '1h', label: 'Past 1h', minutes: 60 },
    { id: '3h', label: 'Past 3h', minutes: 180 },
  ];

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '14px',
        marginBottom: '20px',
      }}
    >
      {/* Time Window Pills */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto' }}>
        <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px', marginRight: '4px' }}>
          <Clock size={13} /> DELTA:
        </span>
        {windows.map((win) => {
          const isActive = selectedWindow === win.id;
          return (
            <button
              key={win.id}
              onClick={() => onSelectWindow(win.id)}
              style={{
                background: isActive ? 'var(--emerald-green-soft)' : '#141A23',
                border: `1px solid ${isActive ? 'var(--emerald-green)' : '#232C3A'}`,
                color: isActive ? 'var(--emerald-green)' : '#94A3B8',
                fontSize: '12px',
                fontWeight: 600,
                padding: '6px 14px',
                borderRadius: '20px',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              {win.label}
            </button>
          );
        })}
      </div>

      {/* Right Controls: Search, Attention Filter & Add Stock */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Search Bar */}
        <div
          style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Search size={14} style={{ position: 'absolute', left: '10px', color: '#64748B' }} />
          <input
            type="text"
            placeholder="Filter symbols..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{
              backgroundColor: '#141A23',
              border: '1px solid #232C3A',
              color: '#FFF',
              fontSize: '12px',
              padding: '6px 12px 6px 30px',
              borderRadius: '8px',
              outline: 'none',
              width: '140px',
            }}
          />
        </div>

        {/* High Attention Toggle Button */}
        <button
          onClick={onToggleFilter}
          style={{
            backgroundColor: filterHighAttention ? 'rgba(255, 179, 0, 0.15)' : '#141A23',
            border: `1px solid ${filterHighAttention ? 'var(--amber-gold)' : '#232C3A'}`,
            color: filterHighAttention ? 'var(--amber-gold)' : '#94A3B8',
            fontSize: '12px',
            fontWeight: 600,
            padding: '6px 12px',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease',
          }}
        >
          <Filter size={13} />
          <span>Outliers Only ({highAttentionCount})</span>
        </button>

        {/* Add Stock Button */}
        <button
          onClick={onOpenAddModal}
          style={{
            backgroundColor: 'var(--emerald-green)',
            border: 'none',
            color: '#0B0E14',
            fontSize: '12px',
            fontWeight: 700,
            padding: '7px 14px',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            transition: 'opacity 0.2s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.9')}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
        >
          <Plus size={15} /> Add Stock
        </button>
      </div>
    </div>
  );
}
