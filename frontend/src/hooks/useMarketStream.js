import { useState, useEffect, useRef, useCallback } from 'react';

export function useMarketStream(onTickReceived) {
  const [connectionStatus, setConnectionStatus] = useState('CONNECTING');
  const [marketSession, setMarketSession] = useState(null);
  const [lastTickTime, setLastTickTime] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    // Determine WebSocket URL (works with Vite proxy or direct backend port)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.port === '5173' ? 'localhost:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/live`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('CONNECTED');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastTickTime(new Date());

          if (data.type === 'INITIAL_SNAPSHOT') {
            if (data.session) setMarketSession(data.session);
          } else if (data.type === 'TICK_UPDATE') {
            if (onTickReceived) {
              onTickReceived(data);
            }
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      ws.onerror = () => {
        setConnectionStatus('DISCONNECTED');
      };

      ws.onclose = () => {
        setConnectionStatus('DISCONNECTED');
        // Auto-reconnect with 3-second backoff
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };
    } catch (err) {
      setConnectionStatus('DISCONNECTED');
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    }
  }, [onTickReceived]);

  useEffect(() => {
    // Fetch initial market session info via REST as well
    fetch('/api/market/session')
      .then((res) => res.json())
      .then((data) => setMarketSession(data))
      .catch(() => {});

    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return {
    connectionStatus,
    marketSession,
    lastTickTime,
  };
}
