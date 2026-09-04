import React, { useState } from 'react';
import { 
  ShieldAlert, 
  Search, 
  ArrowRight, 
  Filter, 
  ExternalLink, 
  AlertTriangle, 
  CheckCircle2, 
  HelpCircle,
  Network,
  Clock,
  Crosshair
} from 'lucide-react';
import rawAlerts from '../assets/alerts.json';

export default function AlertsQueue({ onTargetNode, selectedNodeId }) {
  const [alerts] = useState(rawAlerts);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterLabel, setFilterLabel] = useState('ALL');
  const [sortField, setSortField] = useState('node_id');
  const [sortAsc, setSortAsc] = useState(true);

  const filteredAlerts = alerts.filter(item => {
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      if (!String(item.node_id).includes(q)) return false;
    }
    if (filterLabel === 'ILLICIT' && item.true_label !== 1) return false;
    if (filterLabel === 'OTHER' && item.true_label === 1) return false;
    return true;
  }).sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];
    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  const getLabelBadge = (label) => {
    if (label === 1) {
      return { text: 'CONFIRMED ILLICIT', bg: 'rgba(239, 68, 68, 0.2)', color: '#F87171', border: '#EF4444' };
    }
    if (label === 0) {
      return { text: 'CONFIRMED LICIT', bg: 'rgba(16, 185, 129, 0.2)', color: '#34D399', border: '#10B981' };
    }
    return { text: 'FLAGGED SUSPICIOUS', bg: 'rgba(245, 158, 11, 0.2)', color: '#FBBF24', border: '#F59E0B' };
  };

  const handleRowClick = (nodeId) => {
    if (onTargetNode) {
      onTargetNode(nodeId);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Banner */}
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
            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(245, 158, 11, 0.2) 100%)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#EF4444'
          }}>
            <ShieldAlert size={26} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Screen 5: High-Priority Alerts Queue</h2>
              <span style={{
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '0.72rem',
                fontWeight: 700,
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#F87171',
                border: '1px solid rgba(239, 68, 68, 0.3)'
              }}>
                {alerts.length} Flagged Entities
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Flagged high-risk nodes awaiting forensic review. <strong>Click any row</strong> to target that node directly on the Graph Canvas.
            </p>
          </div>
        </div>

        {/* Action Prompt */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 0.9rem',
          borderRadius: '8px',
          background: 'rgba(6, 182, 212, 0.12)',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          color: '#38BDF8',
          fontSize: '0.75rem',
          fontWeight: 600
        }}>
          <Crosshair size={16} />
          <span>Interactive: Click row to pivot to Graph Canvas</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel" style={{
        padding: '1rem 1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: '320px' }}>
            <Search size={15} color="#94A3B8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search by Node ID (e.g. 136280)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                color: '#FFF',
                padding: '0.55rem 0.75rem 0.55rem 2.2rem',
                fontSize: '0.8rem',
                outline: 'none'
              }}
            />
          </div>

          <select
            value={filterLabel}
            onChange={(e) => setFilterLabel(e.target.value)}
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              color: '#94A3B8',
              padding: '0.55rem 0.85rem',
              fontSize: '0.8rem',
              outline: 'none'
            }}
          >
            <option value="ALL">All Categories ({alerts.length})</option>
            <option value="ILLICIT">Confirmed Illicit Only</option>
            <option value="OTHER">Other Flagged</option>
          </select>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Showing <strong>{filteredAlerts.length}</strong> of {alerts.length} alerts
        </div>
      </div>

      {/* Alerts Table */}
      <div className="w-full overflow-x-auto border border-white/10 rounded-xl no-scrollbar">
        <table className="w-full min-w-[650px] text-left text-sm" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{
              background: 'rgba(255, 255, 255, 0.02)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              color: 'var(--text-muted)',
              fontSize: '0.72rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              <th className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>Node ID</th>
              <th className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>Timestep</th>
              <th className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>Risk Score</th>
              <th className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>Classification</th>
              <th className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>Forensic Priority</th>
              <th className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredAlerts.map((alert, index) => {
              const isSelected = String(selectedNodeId) === String(alert.node_id);
              const badge = getLabelBadge(alert.true_label);

              return (
                <tr
                  key={alert.node_id}
                  onClick={() => handleRowClick(alert.node_id)}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    background: isSelected 
                      ? 'rgba(6, 182, 212, 0.15)' 
                      : (index % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.01)'),
                    cursor: 'pointer',
                    transition: 'background 0.2s ease, transform 0.1s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'rgba(6, 182, 212, 0.08)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = index % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.01)';
                  }}
                >
                  {/* Node ID */}
                  <td className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span 
                        className="max-w-[120px] truncate"
                        title={`#${alert.node_id}`}
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 800,
                          fontSize: '0.9rem',
                          color: '#38BDF8',
                          display: 'inline-block'
                        }}
                      >
                        #{alert.node_id}
                      </span>
                      {isSelected && (
                        <span style={{
                          fontSize: '0.65rem',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background: '#06B6D4',
                          color: '#000',
                          fontWeight: 800
                        }}>
                          ACTIVE
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Timestep */}
                  <td className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)' }}>
                      <Clock size={14} color="#94A3B8" />
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>T-{alert.timestep}</span>
                    </div>
                  </td>

                  {/* Risk Score */}
                  <td className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{
                        width: '45px',
                        height: '5px',
                        background: 'rgba(255, 255, 255, 0.1)',
                        borderRadius: '3px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${Math.round(alert.risk_score * 100)}%`,
                          height: '100%',
                          background: '#EF4444'
                        }} />
                      </div>
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 800,
                        color: '#F87171'
                      }}>
                        {(alert.risk_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>

                  {/* Classification */}
                  <td className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>
                    <span style={{
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      background: badge.bg,
                      color: badge.color,
                      border: `1px solid ${badge.border}`
                    }}>
                      {badge.text}
                    </span>
                  </td>

                  {/* Priority */}
                  <td className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#FBBF24', fontSize: '0.75rem', fontWeight: 600 }}>
                      <AlertTriangle size={14} />
                      <span>High Priority Intercept</span>
                    </div>
                  </td>

                  {/* Action Button */}
                  <td className="whitespace-nowrap" style={{ padding: '0.9rem 1.25rem', textAlign: 'right' }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRowClick(alert.node_id);
                      }}
                      style={{
                        background: 'rgba(6, 182, 212, 0.15)',
                        border: '1px solid rgba(6, 182, 212, 0.4)',
                        color: '#38BDF8',
                        padding: '0.35rem 0.75rem',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.4rem'
                      }}
                    >
                      <span>Target in Graph</span>
                      <ArrowRight size={13} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

    </div>
  );
}
