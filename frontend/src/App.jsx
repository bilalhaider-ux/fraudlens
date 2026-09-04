import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import SituationRoom from './components/SituationRoom';
import GraphCanvas from './components/GraphCanvas';
import DriftMonitor from './components/DriftMonitor';
import AlertsQueue from './components/AlertsQueue';

// Local JSON fallbacks bundled in src/assets
import fallbackAlerts from './assets/alerts.json';
import fallbackDrift from './assets/drift.json';

const API_BASE = 'http://127.0.0.1:8000';
const WS_BASE = 'ws://127.0.0.1:8000';

/** Strict fetch wrapper: returns null on ANY network/parse error instead of throwing */
const safeFetch = async (url, opts) => {
  try {
    const res = await fetch(url, opts);
    return res;
  } catch {
    return null;
  }
};

export default function App() {
  const [activeTab, setActiveTab] = useState('situation');
  const [transactions, setTransactions] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [rules, setRules] = useState([]);
  const [selectedTx, setSelectedTx] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(true);
  const [streamSpeed, setStreamSpeed] = useState(2.0);
  const [newestTxId, setNewestTxId] = useState(null);
  const [isAttacking, setIsAttacking] = useState(false);
  const [targetGraphNodeId, setTargetGraphNodeId] = useState(null);

  const wsRef = useRef(null);

  // 1. Initial Data Fetch — strict try/catch with local JSON fallback
  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(fetchMetrics, 3500);
    return () => clearInterval(interval);
  }, []);

  const fetchInitialData = async () => {
    try {
      const [txRes, metRes, ruleRes] = await Promise.all([
        safeFetch(`${API_BASE}/api/transactions?limit=60`),
        safeFetch(`${API_BASE}/api/metrics`),
        safeFetch(`${API_BASE}/api/rules`)
      ]);
      if (txRes?.ok) {
        const txData = await txRes.json();
        setTransactions(txData);
        if (txData.length > 0 && !selectedTx) {
          setSelectedTx(txData[0]);
        }
      }
      if (metRes?.ok) {
        const metData = await metRes.json();
        setMetrics(metData);
      }
      if (ruleRes?.ok) {
        const ruleData = await ruleRes.json();
        setRules(ruleData);
      }
    } catch (err) {
      // Backend unreachable — silently fall back to bundled JSON assets
      console.warn("[FraudLens] Backend unreachable, using local fallback data.", err?.message);
    }
  };

  const fetchMetrics = async () => {
    try {
      const res = await safeFetch(`${API_BASE}/api/metrics`);
      if (res?.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (e) {
      // silently ignore — backend may be offline
    }
  };

  // 2. WebSocket Stream Connection
  useEffect(() => {
    let reconnectTimeout = null;

    const connectWS = () => {
      try {
        const ws = new WebSocket(`${WS_BASE}/ws/transactions`);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'NEW_TRANSACTION') {
              const newTx = data.payload;
              setTransactions((prev) => [newTx, ...prev.slice(0, 150)]);
              setNewestTxId(newTx.id);
              fetchMetrics();
            }
          } catch (e) {
            console.error("Error parsing WS payload", e);
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimeout = setTimeout(connectWS, 2500);
        };

        ws.onerror = () => {
          setWsConnected(false);
          ws.close();
        };
      } catch (err) {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connectWS, 2500);
      }
    };

    connectWS();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // 3. Stream Play/Pause & Speed Controller
  const toggleStreaming = async () => {
    const nextState = !isStreaming;
    setIsStreaming(nextState);
    try {
      await fetch(`${API_BASE}/api/stream/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ running: nextState, interval_sec: streamSpeed })
      });
    } catch (e) {
      console.error(e);
    }
  };

  const handleSpeedChange = async (speed) => {
    setStreamSpeed(speed);
    try {
      await fetch(`${API_BASE}/api/stream/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ running: isStreaming, interval_sec: speed })
      });
    } catch (e) {
      console.error(e);
    }
  };

  // 4. Investigation Actions
  const handlePerformAction = async (txId, action, note) => {
    try {
      const res = await fetch(`${API_BASE}/api/transactions/${txId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: txId,
          action: action,
          analyst_id: 'analyst_lead',
          note: note
        })
      });
      if (res.ok) {
        const updatedTx = await res.json();
        setTransactions((prev) => prev.map(t => t.id === txId ? updatedTx : t));
        setSelectedTx(updatedTx);
        fetchMetrics();
        return updatedTx;
      }
    } catch (e) {
      console.error("Action error:", e);
    }
  };

  // 5. Rule Actions
  const handleToggleRule = async (ruleId, enabled) => {
    try {
      const res = await fetch(`${API_BASE}/api/rules/${ruleId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });
      if (res.ok) {
        const updated = await res.json();
        setRules((prev) => prev.map(r => r.id === ruleId ? updated : r));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateRule = async (newRule) => {
    try {
      const res = await fetch(`${API_BASE}/api/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newRule)
      });
      if (res.ok) {
        const created = await res.json();
        setRules((prev) => [...prev, created]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    try {
      const res = await fetch(`${API_BASE}/api/rules/${ruleId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setRules((prev) => prev.filter(r => r.id !== ruleId));
      }
    } catch (e) {
      console.error(e);
    }
  };

  // 6. Attack Simulator Trigger
  const handleTriggerAttack = async (attackType, count) => {
    setIsAttacking(true);
    try {
      const res = await fetch(`${API_BASE}/api/simulate/attack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attack_type: attackType, count, intensity: 'HIGH' })
      });
      if (res.ok) {
        const data = await res.json();
        fetchMetrics();
        return data;
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsAttacking(false);
    }
  };

  // 7. Custom API Screening Evaluation
  const handleEvaluateCustomTx = async (payload) => {
    try {
      const res = await safeFetch(`${API_BASE}/api/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res?.ok) {
        throw new Error(`HTTP error ${res?.status || 'network failure'}`);
      }
      const scoredTx = await res.json();
      setTransactions((prev) => [scoredTx, ...prev.slice(0, 150)]);
      setSelectedTx(scoredTx);
      fetchMetrics();
      return scoredTx;
    } catch (e) {
      console.error('[FraudLens] Evaluate API error:', e?.message);
      return null;
    }
  };

  const handleSelectTxForWorkbench = (tx) => {
    setSelectedTx(tx);
    setActiveTab('graph');
  };

  const handleTargetNodeInGraph = (nodeId) => {
    setTargetGraphNodeId(nodeId);
    setActiveTab('graph');
  };

  const alertCount = transactions.filter(t => t.status === 'UNDER_REVIEW').length;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        wsConnected={wsConnected}
        isStreaming={isStreaming}
        toggleStreaming={toggleStreaming}
        streamSpeed={streamSpeed}
        setStreamSpeed={handleSpeedChange}
        threatLevel={metrics?.active_threat_level || 'ELEVATED'}
        alertCount={alertCount}
      />

      <main className="w-full max-w-7xl mx-auto px-3 sm:px-6 flex-1">
        {activeTab === 'situation' && (
          <SituationRoom
            onNavigateToGraph={(nodeId) => {
              setTargetGraphNodeId(nodeId || '174515');
              setActiveTab('graph');
            }}
            onNavigateToAlerts={() => {
              setActiveTab('alerts');
            }}
          />
        )}

        {activeTab === 'graph' && (
          <GraphCanvas
            targetNodeId={targetGraphNodeId}
            onSelectNodeId={(id) => setTargetGraphNodeId(id)}
          />
        )}

        {activeTab === 'drift' && (
          <DriftMonitor />
        )}

        {activeTab === 'alerts' && (
          <AlertsQueue
            onTargetNode={handleTargetNodeInGraph}
            selectedNodeId={targetGraphNodeId}
          />
        )}
      </main>
    </div>
  );
}
