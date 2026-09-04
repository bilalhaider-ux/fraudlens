import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  User, 
  CreditCard, 
  MapPin, 
  Smartphone, 
  Clock, 
  ArrowRight, 
  FileText, 
  Send, 
  Zap, 
  HelpCircle,
  Activity,
  Layers,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Fingerprint,
  Network
} from 'lucide-react';
import confetti from 'canvas-confetti';
import GraphCanvas from './GraphCanvas';

export default function InvestigationWorkbench({ 
  transactions, 
  selectedTx, 
  onSelectTx, 
  onPerformAction,
  targetNodeId
}) {
  const [viewMode, setViewMode] = useState('graph');
  const [analystNote, setAnalystNote] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (targetNodeId) {
      setViewMode('graph');
    }
  }, [targetNodeId]);

  // If no transaction is explicitly selected, pick the highest risk one
  const currentTx = selectedTx || transactions.find(t => t.risk_level === 'CRITICAL' || t.risk_level === 'HIGH') || transactions[0];

  const handleAction = async (actionType) => {
    if (!currentTx) return;
    setActionLoading(true);
    try {
      await onPerformAction(currentTx.id, actionType, analystNote || `Action: ${actionType} executed by Analyst`);
      setAnalystNote('');
      if (actionType === 'APPROVE') {
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.7 }
        });
      }
    } finally {
      setActionLoading(false);
    }
  };

  const getRiskColor = (score) => {
    if (score >= 85) return '#EF4444';
    if (score >= 65) return '#F97316';
    if (score >= 35) return '#F59E0B';
    return '#10B981';
  };

  if (!currentTx && viewMode === 'dossier') {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>No transactions available for investigation.</p>
      </div>
    );
  }

  const scoreColor = currentTx ? getRiskColor(currentTx.risk_score) : '#10B981';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '1.5rem 0' }}>
      
      {/* Top View Selector: Graph Canvas vs Transaction Case File */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <button
          onClick={() => setViewMode('graph')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.6rem 1.1rem',
            borderRadius: '8px',
            fontSize: '0.82rem',
            fontWeight: 700,
            cursor: 'pointer',
            border: viewMode === 'graph' ? '1px solid #06B6D4' : '1px solid rgba(255, 255, 255, 0.1)',
            background: viewMode === 'graph' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(15, 23, 42, 0.6)',
            color: viewMode === 'graph' ? '#38BDF8' : 'var(--text-secondary)'
          }}
        >
          <Network size={16} />
          <span>Screen 2: Graph Canvas (Cytoscape.js)</span>
        </button>

        <button
          onClick={() => setViewMode('dossier')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.6rem 1.1rem',
            borderRadius: '8px',
            fontSize: '0.82rem',
            fontWeight: 700,
            cursor: 'pointer',
            border: viewMode === 'dossier' ? '1px solid #06B6D4' : '1px solid rgba(255, 255, 255, 0.1)',
            background: viewMode === 'dossier' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(15, 23, 42, 0.6)',
            color: viewMode === 'dossier' ? '#38BDF8' : 'var(--text-secondary)'
          }}
        >
          <FileText size={16} />
          <span>Transaction Dossier & XAI Reason Codes</span>
        </button>
      </div>

      {viewMode === 'graph' ? (
        <GraphCanvas targetNodeId={targetNodeId} />
      ) : (
        <>
          {/* Investigation Header & Case Selector */}
          <div className="glass-panel" style={{
        padding: '1.25rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: `${scoreColor}22`,
            border: `1px solid ${scoreColor}55`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: scoreColor
          }}>
            <ShieldAlert size={26} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Case File: {currentTx.id}</h2>
              <span style={{
                padding: '2px 8px',
                borderRadius: '6px',
                fontSize: '0.72rem',
                fontWeight: 700,
                background: currentTx.status.includes('APPROVED') ? 'rgba(16, 185, 129, 0.2)' : (currentTx.status.includes('BLOCKED') || currentTx.status === 'DECLINED' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)'),
                color: currentTx.status.includes('APPROVED') ? '#34D399' : (currentTx.status.includes('BLOCKED') || currentTx.status === 'DECLINED' ? '#F87171' : '#FBBF24')
              }}>
                {currentTx.status.replace('_', ' ')}
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Screened {new Date(currentTx.timestamp).toLocaleString()} • Latency: {currentTx.latency_ms} ms
            </p>
          </div>
        </div>

        {/* Quick Navigator among flagged cases */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Flagged Cases:</span>
          <div style={{ display: 'flex', gap: '0.35rem', overflowX: 'auto', maxWidth: '380px', padding: '2px' }}>
            {transactions.filter(t => t.risk_score >= 40).slice(0, 5).map(t => (
              <button
                key={t.id}
                onClick={() => onSelectTx(t)}
                style={{
                  padding: '0.3rem 0.6rem',
                  borderRadius: '6px',
                  border: t.id === currentTx.id ? '1px solid #06B6D4' : '1px solid rgba(255, 255, 255, 0.1)',
                  background: t.id === currentTx.id ? 'rgba(6, 182, 212, 0.2)' : 'rgba(15, 23, 42, 0.6)',
                  color: t.id === currentTx.id ? '#38BDF8' : 'var(--text-secondary)',
                  fontSize: '0.72rem',
                  fontFamily: 'var(--font-mono)',
                  cursor: 'pointer'
                }}
              >
                {t.id.slice(0, 7)} ({t.risk_score})
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Grid: Left Column (Risk Analysis & XAI), Right Column (Dossier & Actions) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) minmax(360px, 1.4fr)', gap: '1.5rem' }}>
        
        {/* Left Column: Risk Gauge & Explainable AI Reason Codes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Risk Score Meter Card */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Composite Risk Score
            </span>

            {/* Circular Risk Score Display */}
            <div style={{
              position: 'relative',
              width: '160px',
              height: '160px',
              margin: '1.25rem 0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <svg width="160" height="160" viewBox="0 0 160 160" style={{ transform: 'rotate(-90deg)' }}>
                <circle
                  cx="80"
                  cy="80"
                  r="65"
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeWidth="12"
                  fill="transparent"
                />
                <circle
                  cx="80"
                  cy="80"
                  r="65"
                  stroke={scoreColor}
                  strokeWidth="12"
                  strokeDasharray={408.4}
                  strokeDashoffset={408.4 - (408.4 * currentTx.risk_score) / 100}
                  strokeLinecap="round"
                  fill="transparent"
                  style={{ transition: 'stroke-dashoffset 0.8s ease-in-out' }}
                />
              </svg>
              <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '2.4rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: scoreColor }}>
                  {currentTx.risk_score}
                </span>
                <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)' }}>OUT OF 100</span>
              </div>
            </div>

            <div style={{
              display: 'inline-block',
              padding: '4px 14px',
              borderRadius: '20px',
              fontSize: '0.8rem',
              fontWeight: 800,
              background: `${scoreColor}22`,
              color: scoreColor,
              border: `1px solid ${scoreColor}44`,
              letterSpacing: '0.05em'
            }}>
              {currentTx.risk_level} RISK LEVEL
            </div>

            {/* Score Component Breakdown */}
            <div style={{
              marginTop: '1.25rem',
              width: '100%',
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '0.5rem',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              paddingTop: '1rem'
            }}>
              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>ML Supervised</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#38BDF8' }}>
                  {(currentTx.ml_probability * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Rule Boost</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#FBBF24' }}>
                  +{currentTx.rule_score_boost} pts
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Decision Engine</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: currentTx.risk_score > 60 ? '#F87171' : '#34D399' }}>
                  {currentTx.risk_score > 80 ? 'AUTO-BLOCK' : (currentTx.risk_score > 35 ? 'MANUAL' : 'AUTO-PASS')}
                </div>
              </div>
            </div>
          </div>

          {/* Explainable AI (XAI) Attribution & Reason Codes */}
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <Activity size={18} color="#06B6D4" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Explainable AI (XAI) Reason Codes</h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {currentTx.reason_codes.length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
                  No high-risk anomaly vectors detected.
                </div>
              ) : (
                currentTx.reason_codes.map((rc, idx) => (
                  <div
                    key={`rc-${rc.factor || idx}-${idx}`}
                    style={{
                      background: rc.direction === 'RISK_DECREASE' ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                      borderLeft: `3px solid ${rc.direction === 'RISK_DECREASE' ? '#10B981' : '#EF4444'}`,
                      borderRadius: '0 8px 8px 0',
                      padding: '0.75rem 1rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                        {rc.factor}
                      </span>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 800,
                        fontFamily: 'var(--font-mono)',
                        color: rc.direction === 'RISK_DECREASE' ? '#34D399' : '#F87171'
                      }}>
                        {rc.impact}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      {rc.description}
                    </p>
                  </div>
                ))
              )}
            </div>

            {/* Triggered Policy Rules */}
            {currentTx.triggered_rules && currentTx.triggered_rules.length > 0 && (
              <div style={{ marginTop: '1.25rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '1rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  Triggered Policy Rules ({currentTx.triggered_rules.length}):
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.5rem' }}>
                  {currentTx.triggered_rules.map((rule, idx) => (
                    <span
                      key={`rule-${typeof rule === 'object' ? rule.id : rule}-${idx}`}
                      style={{
                        fontSize: '0.7rem',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        background: 'rgba(239, 68, 68, 0.15)',
                        color: '#F87171',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        fontWeight: 600
                      }}
                    >
                      {rule}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>

        {/* Right Column: Transaction Dossier & Investigation Action Desk */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Dossier Card */}
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <User size={18} color="#06B6D4" />
              Transaction & Entity Dossier
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              
              {/* Customer Profile */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                  Customer Profile
                </div>
                <div style={{ fontWeight: 700, fontSize: '0.88rem' }}>{currentTx.user_id}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  30-Day Avg Spend: <strong style={{ color: '#FFF' }}>${currentTx.avg_user_amount_30d.toFixed(2)}</strong>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Spend Delta: <strong style={{ color: currentTx.amount > currentTx.avg_user_amount_30d * 3 ? '#F87171' : '#34D399' }}>
                    {(currentTx.amount / currentTx.avg_user_amount_30d).toFixed(1)}x baseline
                  </strong>
                </div>
              </div>

              {/* Payment Details */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                  Payment Method
                </div>
                <div style={{ fontWeight: 700, fontSize: '0.88rem' }}>
                  •••• {currentTx.card_last4} ({currentTx.card_type.toUpperCase()})
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Card BIN: <span className="font-mono">{currentTx.card_bin}</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Currency: {currentTx.currency} • Amount: <strong style={{ color: '#FFF' }}>${currentTx.amount.toFixed(2)}</strong>
                </div>
              </div>

              {/* Geolocation & Routing */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                  Geolocation Telemetry
                </div>
                <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>
                  IP: <span className="font-mono">{currentTx.ip_address}</span> ({currentTx.ip_country})
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Billing / Shipping: {currentTx.billing_country} / {currentTx.shipping_country}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Geo Distance Delta: <strong style={{ color: currentTx.distance_from_billing_km > 500 ? '#F87171' : '#FFF' }}>
                    {currentTx.distance_from_billing_km.toLocaleString()} km
                  </strong>
                </div>
              </div>

              {/* Hardware & Device Fingerprint */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
                  Device & Velocity
                </div>
                <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>
                  Type: <span style={{ textTransform: 'capitalize' }}>{currentTx.device_type.replace('_', ' ')}</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Fingerprint: <span className="font-mono">{currentTx.device_fingerprint.slice(0, 14)}...</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Velocity 1h / 24h: <strong style={{ color: currentTx.velocity_1h > 3 ? '#F87171' : '#FFF' }}>
                    {currentTx.velocity_1h} tx / {currentTx.velocity_24h} tx
                  </strong>
                </div>
              </div>

            </div>
          </div>

          {/* Analyst Action Desk */}
          <div className="glass-panel" style={{ padding: '1.25rem', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={18} color="#06B6D4" />
              Analyst Investigation Workbench
            </h3>

            {/* Note input */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                Analyst Notes / Audit Justification:
              </label>
              <textarea
                placeholder="Enter investigation rationale (e.g. Verified cardholder over phone, suspicious IP range matching known compromised botnet...)"
                value={analystNote}
                onChange={(e) => setAnalystNote(e.target.value)}
                rows={3}
                style={{
                  width: '100%',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  color: '#FFF',
                  padding: '0.65rem',
                  fontSize: '0.8rem',
                  outline: 'none',
                  resize: 'none'
                }}
              />
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
              <button
                onClick={() => handleAction('APPROVE')}
                disabled={actionLoading}
                className="btn-success"
                style={{
                  padding: '0.7rem',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem'
                }}
              >
                <CheckCircle size={16} />
                <span>Approve (Mark Safe)</span>
              </button>

              <button
                onClick={() => handleAction('BLOCK')}
                disabled={actionLoading}
                className="btn-danger"
                style={{
                  padding: '0.7rem',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem'
                }}
              >
                <XCircle size={16} />
                <span>Decline & Block Card</span>
              </button>

              <button
                onClick={() => handleAction('ESCALATE')}
                disabled={actionLoading}
                className="btn-secondary"
                style={{
                  padding: '0.7rem',
                  borderRadius: '8px',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem'
                }}
              >
                <AlertTriangle size={16} color="#F59E0B" />
                <span>Escalate to AML</span>
              </button>
            </div>

            {/* Existing Audit Notes */}
            {currentTx.notes && currentTx.notes.length > 0 && (
              <div style={{ marginTop: '1.25rem', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '0.75rem' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Audit History Trail:</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                  {currentTx.notes.map((n, idx) => (
                    <div key={`audit-note-${n.analyst}-${n.timestamp}-${idx}`} style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.5rem 0.75rem', borderRadius: '6px', fontSize: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.68rem' }}>
                        <span>Analyst: <strong>{n.analyst}</strong></span>
                        <span>{new Date(n.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <div style={{ marginTop: '0.2rem', color: 'var(--text-secondary)' }}>{n.note}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>

        </div>

      </div>
        </>
      )}

    </div>
  );
}
