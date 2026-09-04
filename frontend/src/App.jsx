import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import SituationRoom from './components/SituationRoom';
import GraphCanvas from './components/GraphCanvas';
import DriftMonitor from './components/DriftMonitor';
import AlertsQueue from './components/AlertsQueue';
import {
  WS_BASE,
  fetchTransactionsApi,
  fetchMetricsApi,
  fetchRulesApi,
  controlStreamApi,
  submitTransactionActionApi,
  toggleRuleApi,
  createRuleApi,
  deleteRuleApi,
  triggerAttackApi,
  evaluateCustomTxApi
} from './api';

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

  // 1. Initial Data Fetch — resilient API layer with guaranteed static fallbacks
  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(fetchMetrics, 3500);
    return () => clearInterval(interval);
  }, []);

  const fetchInitialData = async () => {
    try {
      const [txData, metData, ruleData] = await Promise.all([
        fetchTransactionsApi(60),
        fetchMetricsApi(),
        fetchRulesApi()
      ]);

      if (txData && txData.length > 0) {
        setTransactions(txData);
        if (!selectedTx) setSelectedTx(txData[0]);
      }
      if (metData) {
        setMetrics(metData);
      }
      if (ruleData) {
        setRules(ruleData);
      }
    } catch (err) {
      console.warn("[FraudLens] Initial load handled with static fixtures:", err?.message);
    }
  };

  const fetchMetrics = async () => {
    try {
      const data = await fetchMetricsApi();
      if (data) {
        setMetrics(data);
      }
    } catch (e) {
      // silently ignore
    }
  };

  // 2. WebSocket Stream Connection with graceful reconnection
  useEffect(() => {
    let reconnectTimeout = null;

    const connectWS = () => {
      if (!WS_BASE) {
        setWsConnected(false);
        return;
      }

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
          reconnectTimeout = setTimeout(connectWS, 4000);
        };

        ws.onerror = () => {
          setWsConnected(false);
          try { ws.close(); } catch {}
        };
      } catch (err) {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connectWS, 4000);
      }
    };

    connectWS();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        try { wsRef.current.close(); } catch {}
      }
    };
  }, []);

  // 3. Stream Play/Pause & Speed Controller
  const toggleStreaming = async () => {
    const nextState = !isStreaming;
    setIsStreaming(nextState);
    await controlStreamApi(nextState, streamSpeed);
  };

  const handleSpeedChange = async (speed) => {
    setStreamSpeed(speed);
    await controlStreamApi(isStreaming, speed);
  };

  // 4. Investigation Actions
  const handlePerformAction = async (txId, action, note) => {
    const updatedTx = await submitTransactionActionApi(txId, action, note);
    if (updatedTx) {
      setTransactions((prev) => prev.map(t => t.id === txId ? { ...t, ...updatedTx } : t));
      setSelectedTx(prev => prev && prev.id === txId ? { ...prev, ...updatedTx } : prev);
      fetchMetrics();
      return updatedTx;
    }
  };

  // 5. Rule Actions
  const handleToggleRule = async (ruleId, enabled) => {
    const updated = await toggleRuleApi(ruleId, enabled);
    if (updated) {
      setRules((prev) => prev.map(r => r.id === ruleId ? { ...r, ...updated } : r));
    }
  };

  const handleCreateRule = async (newRule) => {
    const created = await createRuleApi(newRule);
    if (created) {
      setRules((prev) => [...prev, created]);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    const res = await deleteRuleApi(ruleId);
    if (res?.success) {
      setRules((prev) => prev.filter(r => r.id !== ruleId));
    }
  };

  // 6. Attack Simulator Trigger
  const handleTriggerAttack = async (attackType, count) => {
    setIsAttacking(true);
    try {
      const data = await triggerAttackApi(attackType, count);
      fetchMetrics();
      return data;
    } finally {
      setIsAttacking(false);
    }
  };

  // 7. Custom API Screening Evaluation
  const handleEvaluateCustomTx = async (payload) => {
    const scoredTx = await evaluateCustomTxApi(payload);
    if (scoredTx) {
      setTransactions((prev) => [scoredTx, ...prev.slice(0, 150)]);
      setSelectedTx(scoredTx);
      fetchMetrics();
      return scoredTx;
    }
    return null;
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
    <div className="min-h-screen w-full overflow-x-hidden flex flex-col bg-[#080B11] text-[#F8FAFC]">
      <Navbar
        activeScreen={typeof activeTab === 'number' ? activeTab : (activeTab === 'situation' ? 1 : activeTab === 'graph' ? 2 : activeTab === 'drift' ? 3 : 4)}
        setActiveScreen={setActiveTab}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        alertCount={alertCount}
      />

      <main className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex-1 py-4 sm:py-6">
        {(activeTab === 'situation' || activeTab === 1) && (
          <SituationRoom
            onNavigateToGraph={(nodeId) => {
              setTargetGraphNodeId(nodeId || '174085');
              setActiveTab('graph');
            }}
            onNavigateToAlerts={() => {
              setActiveTab('alerts');
            }}
            setActiveScreen={setActiveTab}
          />
        )}

        {(activeTab === 'graph' || activeTab === 2) && (
          <GraphCanvas
            targetNodeId={targetGraphNodeId}
            selectedNodeId={targetGraphNodeId}
            onSelectNodeId={(id) => setTargetGraphNodeId(id)}
            setSelectedNodeId={setTargetGraphNodeId}
            activeScreen={typeof activeTab === 'number' ? activeTab : (activeTab === 'situation' ? 1 : activeTab === 'graph' ? 2 : activeTab === 'drift' ? 3 : 4)}
            setActiveScreen={setActiveTab}
          />
        )}

        {(activeTab === 'drift' || activeTab === 3) && (
          <DriftMonitor 
            setActiveScreen={setActiveTab}
          />
        )}

        {(activeTab === 'alerts' || activeTab === 4) && (
          <AlertsQueue
            onSelectNode={(id) => {
              setTargetGraphNodeId(id);
              setActiveTab(2);
            }}
            onTargetNode={handleTargetNodeInGraph}
            selectedNodeId={targetGraphNodeId}
            setSelectedNodeId={setTargetGraphNodeId}
            setActiveScreen={setActiveTab}
          />
        )}
      </main>
    </div>
  );
}
