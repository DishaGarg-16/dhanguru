import React, { useState, useEffect, useRef } from 'react';
import { X, Search, Plus, Check, Loader2, Sparkles } from 'lucide-react';

const POPULAR_CATEGORIES = [
  { id: 'ALL', label: 'All Curated' },
  { id: 'NIFTY 50', label: 'NIFTY 50' },
  { id: 'Automobile', label: 'Automobile' },
  { id: 'Banking & Finance', label: 'Banking & Finance' },
  { id: 'Information Technology', label: 'IT & Tech' },
  { id: 'FMCG & Retail', label: 'FMCG & Retail' },
  { id: 'Energy & Metals', label: 'Energy & Metals' },
  { id: 'Pharma & Healthcare', label: 'Pharma' },
  { id: 'Consumer Internet', label: 'Internet / Growth' },
];

export function AddSymbolModal({ isOpen, onClose, onAddSymbol, existingSymbols = [] }) {
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [addingSymbol, setAddingSymbol] = useState(null);
  const searchTimeoutRef = useRef(null);

  // Load curated stocks or search results
  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setSelectedCategory('ALL');
      setStocks([]);
      return;
    }

    // Initial load: fetch curated list
    fetchCuratedStocks(selectedCategory);
  }, [isOpen]);

  const fetchCuratedStocks = async (catId) => {
    setLoading(true);
    try {
      const url = catId === 'ALL' 
        ? '/api/stocks/curated' 
        : `/api/stocks/curated?category=${encodeURIComponent(catId)}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setStocks(data.stocks || []);
      }
    } catch (err) {
      console.error('Failed to fetch curated stocks:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle live debounced search
  useEffect(() => {
    if (!isOpen) return;

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (!query.trim()) {
      // Revert to selected category view
      fetchCuratedStocks(selectedCategory);
      return;
    }

    setLoading(true);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`/api/stocks/search?q=${encodeURIComponent(query.trim())}`);
        if (res.ok) {
          const data = await res.json();
          setStocks(data.results || []);
        }
      } catch (err) {
        console.error('Search request failed:', err);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => {
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, [query]);

  // Handle category chip click
  const handleCategorySelect = (catId) => {
    setSelectedCategory(catId);
    setQuery('');
    fetchCuratedStocks(catId);
  };

  // Handle add click
  const handleAddClick = async (symbol) => {
    setAddingSymbol(symbol);
    try {
      await onAddSymbol(symbol);
    } finally {
      setAddingSymbol(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.78)',
        backdropFilter: 'blur(6px)',
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
          maxWidth: '560px',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#111620',
          border: '1px solid #232D3F',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 24px 48px rgba(0,0,0,0.7)',
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
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#FFF', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={16} style={{ color: 'var(--emerald-green)' }} />
              Add Stock to Watchlist
            </h3>
            <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
              Explore 2,000+ Indian equities by sector or search any company
            </p>
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
            <X size={18} />
          </button>
        </div>

        {/* Search Box */}
        <div style={{ position: 'relative', marginBottom: '14px' }}>
          <Search size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: '#64748B' }} />
          <input
            type="text"
            placeholder="Search by ticker or name (e.g., M&M, TCS, Maruti, Tata)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: '#18202C',
              border: '1px solid #283548',
              color: '#FFF',
              fontSize: '13px',
              padding: '10px 38px 10px 36px',
              borderRadius: '10px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
            autoFocus
          />
          {loading && (
            <Loader2
              size={15}
              className="animate-spin"
              style={{ position: 'absolute', right: '12px', top: '12px', color: 'var(--emerald-green)' }}
            />
          )}
        </div>

        {/* Sector Filter Chips */}
        <div
          style={{
            display: 'flex',
            gap: '6px',
            overflowX: 'auto',
            paddingBottom: '8px',
            marginBottom: '12px',
            scrollbarWidth: 'none',
          }}
        >
          {POPULAR_CATEGORIES.map((cat) => {
            const isSelected = selectedCategory === cat.id && !query.trim();
            return (
              <button
                key={cat.id}
                onClick={() => handleCategorySelect(cat.id)}
                style={{
                  backgroundColor: isSelected ? 'rgba(0, 208, 156, 0.15)' : '#18212D',
                  color: isSelected ? 'var(--emerald-green)' : '#94A3B8',
                  border: isSelected ? '1px solid rgba(0, 208, 156, 0.4)' : '1px solid #222C3C',
                  borderRadius: '20px',
                  padding: '5px 12px',
                  fontSize: '11px',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {cat.label}
              </button>
            );
          })}
        </div>

        {/* Stock Results List */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            overflowY: 'auto',
            maxHeight: '340px',
            paddingRight: '4px',
          }}
        >
          {stocks.length === 0 && !loading && (
            <div
              style={{
                textAlign: 'center',
                padding: '40px 16px',
                color: '#64748B',
                fontSize: '13px',
              }}
            >
              {query ? (
                <>
                  <div style={{ fontWeight: 600, color: '#94A3B8', marginBottom: '4px' }}>
                    No stocks matching "{query}"
                  </div>
                  <div>Try searching by ticker (e.g., M&M, TCS, RELIANCE) or choose a sector above.</div>
                </>
              ) : (
                <div>No stocks found in this category.</div>
              )}
            </div>
          )}

          {stocks.map((item) => {
            const alreadyAdded = existingSymbols.includes(item.symbol);
            const isCurrentlyAdding = addingSymbol === item.symbol;

            return (
              <div
                key={item.symbol}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  backgroundColor: '#161D28',
                  borderRadius: '10px',
                  border: '1px solid #222B3A',
                  transition: 'background-color 0.15s ease',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      className="font-mono"
                      style={{
                        fontWeight: 700,
                        color: '#FFF',
                        fontSize: '13px',
                      }}
                    >
                      {item.symbol}
                    </span>
                    {item.exchange && (
                      <span
                        style={{
                          fontSize: '10px',
                          color: '#00D09C',
                          backgroundColor: 'rgba(0, 208, 156, 0.1)',
                          padding: '1px 5px',
                          borderRadius: '4px',
                          fontWeight: 600,
                        }}
                      >
                        {item.exchange}
                      </span>
                    )}
                    <span
                      style={{
                        fontSize: '11px',
                        color: '#64748B',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      • {item.sector}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: '12px',
                      color: '#94A3B8',
                      marginTop: '2px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {item.name}
                  </div>
                </div>

                <button
                  onClick={() => !alreadyAdded && !isCurrentlyAdding && handleAddClick(item.symbol)}
                  disabled={alreadyAdded || isCurrentlyAdding}
                  style={{
                    backgroundColor: alreadyAdded ? '#1F2836' : 'var(--emerald-green)',
                    border: 'none',
                    color: alreadyAdded ? '#64748B' : '#0B0E14',
                    fontSize: '12px',
                    fontWeight: 700,
                    padding: '6px 14px',
                    borderRadius: '8px',
                    cursor: alreadyAdded ? 'default' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    flexShrink: 0,
                    marginLeft: '12px',
                    minWidth: '76px',
                    justifyContent: 'center',
                  }}
                >
                  {isCurrentlyAdding ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : alreadyAdded ? (
                    <>
                      <Check size={13} /> Added
                    </>
                  ) : (
                    <>
                      <Plus size={13} /> Add
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
