import React, { useState } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  AlertOctagon, 
  DollarSign, 
  Clock, 
  Search, 
  Filter, 
  ArrowUpRight, 
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Cpu,
  Globe,
  Flame,
  CheckCircle2,
  XCircle,
  AlertTriangle
} from 'lucide-react';

export default function MissionControl({ 
  transactions, 
  metrics, 
  onSelectTransaction,
  onTriggerSimulatedAttack,
  newestTxId
}) {
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTransactions = transactions.filter((tx) => {
    if (filterRisk === 'LOW' && tx.risk_level !== 'LOW') return false;
    if (filterRisk === 'MEDIUM' && tx.risk_level !== 'MEDIUM') return false;
    if (filterRisk === 'HIGH' && tx.risk_level !== 'HIGH') return false;
    if (filterRisk === 'CRITICAL' && tx.risk_level !== 'CRITICAL') return false;
    if (filterRisk === 'REVIEW' && tx.status !== 'UNDER_REVIEW') return false;
    if (filterRisk === 'DECLINED' && tx.status !== 'DECLINED' && tx.status !== 'MANUALLY_BLOCKED') return false;

    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      const match = 
        tx.id.toLowerCase().includes(q) ||
        tx.user_id.toLowerCase().includes(q) ||
        tx.merchant.toLowerCase().includes(q) ||
        tx.ip_address.includes(q) ||
        tx.card_last4.includes(q) ||
        tx.ip_country.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const getRiskBadgeClass = (level) => {
    switch (level) {
      case 'CRITICAL': return 'badge-critical';
      case 'HIGH': return 'badge-high';
      case 'MEDIUM': return 'badge-medium';
      default: return 'badge-low';
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'APPROVED':
      case 'MANUALLY_APPROVED':
        return { text: 'APPROVED', bg: 'rgba(16, 185, 129, 0.15)', color: '#34D399', icon: CheckCircle2 };
      case 'DECLINED':
      case 'MANUALLY_BLOCKED':
        return { text: 'BLOCKED', bg: 'rgba(239, 68, 68, 0.15)', color: '#F87171', icon: XCircle };
      default:
        return { text: 'IN REVIEW', bg: 'rgba(245, 158, 11, 0.15)', color: '#FBBF24', icon: AlertTriangle };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '1.5rem 0' }}>
      
      {/* Top Row: Executive KPI Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '1rem'
      }}>
        {/* KPI 1: Screened */}
        <div className="glass-panel" style={{ padding: '1.25rem', position: 'relative', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Screened
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(6, 182, 212, 0.12)', color: '#06B6D4' }}>
              <Cpu size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
              {metrics?.total_screened || transactions.length}
            </span>
            <span style={{ fontSize: '0.72rem', color: '#10B981', fontWeight: 600, display: 'flex', alignItems: 'center' }}>
              <ArrowUpRight size={12} /> 100% Real-time
            </span>
          </div>
          <div style={{ marginTop: '0.4rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Throughput: ~3.4 tx/sec peak
          </div>
        </div>

        {/* KPI 2: Fraud Rate */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Fraud Threat Rate
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.12)', color: '#EF4444' }}>
              <ShieldAlert size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#F87171' }}>
              {metrics?.fraud_rate_pct || 0}%
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              {metrics?.total_flagged || 0} flagged
            </span>
          </div>
          <div style={{ marginTop: '0.4rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Auto-Decline: {metrics?.total_declined || 0} attacks
          </div>
        </div>

        {/* KPI 3: Prevented Loss */}
        <div className="glass-panel glow-cyan" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Prevented Loss (USD)
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.12)', color: '#10B981' }}>
              <DollarSign size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#34D399' }}>
              ${(metrics?.total_loss_prevented_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div style={{ marginTop: '0.4rem', fontSize: '0.72rem', color: '#10B981', fontWeight: 600 }}>
            Zero false chargebacks recorded
          </div>
        </div>

        {/* KPI 4: Pending Review */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Analyst Backlog
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.12)', color: '#F59E0B' }}>
              <AlertOctagon size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#FBBF24' }}>
              {transactions.filter(t => t.status === 'UNDER_REVIEW').length}
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              active cases
            </span>
          </div>
          <div style={{ marginTop: '0.4rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Median review time: &lt; 2.5 min
          </div>
        </div>

        {/* KPI 5: ML Latency */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Scoring Latency
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.12)', color: '#818CF8' }}>
              <Clock size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#818CF8' }}>
              {metrics?.avg_scoring_latency_ms || 1.15} <span style={{ fontSize: '1.1rem' }}>ms</span>
            </span>
          </div>
          <div style={{ marginTop: '0.4rem', fontSize: '0.72rem', color: '#10B981', fontWeight: 600 }}>
            Sub-millisecond inference
          </div>
        </div>
      </div>

      {/* Action Banner: Attack Simulation Quick-Triggers */}
      <div className="glass-panel" style={{
        padding: '1rem 1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'linear-gradient(90deg, rgba(30, 41, 59, 0.7) 0%, rgba(17, 24, 39, 0.9) 100%)',
        borderLeft: '4px solid #06B6D4'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{
            padding: '8px',
            borderRadius: '8px',
            background: 'rgba(6, 182, 212, 0.15)',
            color: '#06B6D4'
          }}>
            <Flame size={20} />
          </div>
          <div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700 }}>Interactive Threat Simulation Engine</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Trigger specialized fraud attack vectors to test machine learning models and dynamic heuristic rules live.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => onTriggerSimulatedAttack('card_testing', 12)}
            className="btn-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.78rem', borderRadius: '6px' }}
          >
            ⚡ Card Testing (12x)
          </button>
          <button
            onClick={() => onTriggerSimulatedAttack('account_takeover', 6)}
            className="btn-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.78rem', borderRadius: '6px' }}
          >
            🛡️ Account Takeover (6x)
          </button>
          <button
            onClick={() => onTriggerSimulatedAttack('impossible_travel', 6)}
            className="btn-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.78rem', borderRadius: '6px' }}
          >
            ✈️ Impossible Travel (6x)
          </button>
          <button
            onClick={() => onTriggerSimulatedAttack('crypto_wash', 8)}
            className="btn-danger"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.78rem', borderRadius: '6px' }}
          >
            🚨 High-Yield Crypto Wash
          </button>
        </div>
      </div>

      {/* Main Section: Live Transaction Waterfall Feed */}
      <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        
        {/* Controls & Filter Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#06B6D4',
                boxShadow: '0 0 8px #06B6D4'
              }} className="pulse-dot" />
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Live Transaction Feed</h2>
            </div>
            <span style={{
              fontSize: '0.72rem',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '10px',
              background: 'rgba(255, 255, 255, 0.08)',
              color: 'var(--text-secondary)'
            }}>
              {filteredTransactions.length} events
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {/* Search Input */}
            <div style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center'
            }}>
              <Search size={15} color="#94A3B8" style={{ position: 'absolute', left: '10px' }} />
              <input
                type="text"
                placeholder="Search TxID, User, Merchant, IP..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  color: '#FFF',
                  fontSize: '0.8rem',
                  padding: '0.45rem 0.75rem 0.45rem 2rem',
                  outline: 'none',
                  width: '240px'
                }}
              />
            </div>

            {/* Filter Tabs */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              background: 'rgba(15, 23, 42, 0.6)',
              padding: '3px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.08)'
            }}>
              {['ALL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'REVIEW', 'DECLINED'].map((r) => (
                <button
                  key={r}
                  onClick={() => setFilterRisk(r)}
                  style={{
                    border: 'none',
                    padding: '0.35rem 0.65rem',
                    borderRadius: '5px',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: filterRisk === r ? 'rgba(6, 182, 212, 0.25)' : 'transparent',
                    color: filterRisk === r ? '#38BDF8' : 'var(--text-secondary)',
                    transition: 'all 0.15s'
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Live Waterfall Table */}
        <div style={{ overflowX: 'auto', maxHeight: '620px' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            textAlign: 'left',
            fontSize: '0.82rem'
          }}>
            <thead>
              <tr style={{
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                color: 'var(--text-muted)',
                fontSize: '0.72rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                <th style={{ padding: '0.75rem 1rem' }}>Transaction ID</th>
                <th style={{ padding: '0.75rem 1rem' }}>User / Card</th>
                <th style={{ padding: '0.75rem 1rem' }}>Merchant</th>
                <th style={{ padding: '0.75rem 1rem' }}>Amount</th>
                <th style={{ padding: '0.75rem 1rem' }}>IP & Geolocation</th>
                <th style={{ padding: '0.75rem 1rem' }}>Risk Score</th>
                <th style={{ padding: '0.75rem 1rem' }}>Decision</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No transactions match current filters.
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((tx) => {
                  const isNewest = tx.id === newestTxId;
                  const statusInfo = getStatusBadge(tx.status);
                  const StatusIcon = statusInfo.icon;
                  const riskClass = getRiskBadgeClass(tx.risk_level);

                  return (
                    <tr
                      key={tx.id}
                      className={isNewest ? "new-row-flash" : ""}
                      onClick={() => onSelectTransaction(tx)}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                        cursor: 'pointer',
                        transition: 'background 0.15s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      {/* ID & Timestamp */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <div style={{ fontWeight: 600, color: '#F1F5F9', fontFamily: 'var(--font-mono)' }}>
                          {tx.id}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {new Date(tx.timestamp).toLocaleTimeString()}
                        </div>
                      </td>

                      {/* User & Card */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{tx.user_id}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                          •••• {tx.card_last4} ({tx.card_type.toUpperCase()})
                        </div>
                      </td>

                      {/* Merchant & MCC */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <div style={{ fontWeight: 600 }}>{tx.merchant}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                          {tx.merchant_category.replace('_', ' ')}
                        </div>
                      </td>

                      {/* Amount */}
                      <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.9rem' }}>
                        ${tx.amount.toFixed(2)}
                      </td>

                      {/* IP & Geo */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <span style={{
                            padding: '1px 5px',
                            borderRadius: '3px',
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            background: tx.ip_country !== tx.billing_country ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                            color: tx.ip_country !== tx.billing_country ? '#F87171' : '#CBD5E1'
                          }}>
                            {tx.ip_country}
                          </span>
                          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                            {tx.ip_address}
                          </span>
                        </div>
                        {tx.is_vpn_or_proxy && (
                          <span style={{ fontSize: '0.65rem', color: '#F87171', fontWeight: 600 }}>
                            • VPN/TOR Detected
                          </span>
                        )}
                      </td>

                      {/* Risk Score */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <span className={riskClass} style={{
                            padding: '2px 8px',
                            borderRadius: '12px',
                            fontWeight: 700,
                            fontSize: '0.72rem',
                            minWidth: '55px',
                            textAlign: 'center'
                          }}>
                            {tx.risk_score} / 100
                          </span>
                          
                          {/* Mini visual bar */}
                          <div style={{
                            width: '45px',
                            height: '5px',
                            borderRadius: '3px',
                            background: 'rgba(255, 255, 255, 0.1)',
                            overflow: 'hidden'
                          }}>
                            <div style={{
                              width: `${tx.risk_score}%`,
                              height: '100%',
                              background: tx.risk_score >= 80 ? '#EF4444' : (tx.risk_score >= 40 ? '#F59E0B' : '#10B981')
                            }} />
                          </div>
                        </div>
                      </td>

                      {/* Decision Status */}
                      <td style={{ padding: '0.85rem 1rem' }}>
                        <div style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          background: statusInfo.bg,
                          color: statusInfo.color
                        }}>
                          <StatusIcon size={12} />
                          <span>{statusInfo.text}</span>
                        </div>
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectTransaction(tx);
                          }}
                          className="btn-secondary"
                          style={{
                            padding: '0.35rem 0.7rem',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem'
                          }}
                        >
                          <span>Inspect</span>
                          <ChevronRight size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
