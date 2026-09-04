import React, { useState } from 'react';
import { X, Search, Plus, Check } from 'lucide-react';

export function AddSymbolModal({ isOpen, onClose, onAddSymbol, existingSymbols = [] }) {
  if (!isOpen) return null;

  const availableSymbols = [
    { symbol: 'ZOMATO', name: 'Zomato Ltd', sector: 'Consumer Internet' },
    { symbol: 'TRENT', name: 'Trent Ltd (Tata)', sector: 'Retail & Fashion' },
    { symbol: 'TATAMOTORS', name: 'Tata Motors Ltd', sector: 'Automobile' },
    { symbol: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy & Retail' },
    { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', sector: 'Banking & Finance' },
    { symbol: 'INFY', name: 'Infosys Ltd', sector: 'Information Technology' },
    { symbol: 'ITC', name: 'ITC Ltd', sector: 'FMCG & Conglomerate' },
  ];

  const [query, setQuery] = useState('');

  const filtered = availableSymbols.filter(
    (s) =>
      s.symbol.toLowerCase().includes(query.toLowerCase()) ||
      s.name.toLowerCase().includes(query.toLowerCase()) ||
      s.sector.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '480px',
          backgroundColor: '#131822',
          border: '1px solid #283344',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
          }}
        >
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#FFF' }}>
            Add Stock to Watchlist
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94A3B8',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Search Box */}
        <div style={{ position: 'relative', marginBottom: '16px' }}>
          <Search size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: '#64748B' }} />
          <input
            type="text"
            placeholder="Search by symbol or company name..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: '#1A2230',
              border: '1px solid #2A3649',
              color: '#FFF',
              fontSize: '13px',
              padding: '10px 14px 10px 36px',
              borderRadius: '10px',
              outline: 'none',
            }}
            autoFocus
          />
        </div>

        {/* Available List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
          {filtered.map((item) => {
            const alreadyAdded = existingSymbols.includes(item.symbol);

            return (
              <div
                key={item.symbol}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  backgroundColor: '#1A212E',
                  borderRadius: '10px',
                  border: '1px solid #242E3E',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="font-mono" style={{ fontWeight: 700, color: '#FFF', fontSize: '14px' }}>
                      {item.symbol}
                    </span>
                    <span style={{ fontSize: '11px', color: '#64748B' }}>• {item.sector}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                    {item.name}
                  </div>
                </div>

                <button
                  onClick={() => !alreadyAdded && onAddSymbol(item.symbol)}
                  disabled={alreadyAdded}
                  style={{
                    backgroundColor: alreadyAdded ? '#1F2937' : 'var(--emerald-green)',
                    border: 'none',
                    color: alreadyAdded ? '#64748B' : '#0B0E14',
                    fontSize: '12px',
                    fontWeight: 700,
                    padding: '6px 12px',
                    borderRadius: '8px',
                    cursor: alreadyAdded ? 'default' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  {alreadyAdded ? (
                    <>
                      <Check size={14} /> Added
                    </>
                  ) : (
                    <>
                      <Plus size={14} /> Add
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
