import React from 'react';
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ReferenceLine 
} from 'recharts';
import { 
  ShieldAlert, 
  AlertTriangle, 
  Database, 
  TrendingDown, 
  ArrowRight, 
  Layers, 
  Sparkles,
  Clock,
  CheckCircle2
} from 'lucide-react';
import rawAlerts from '../assets/alerts.json';
import rawDrift from '../assets/drift.json';

export default function SituationRoom({ onNavigateToGraph, onNavigateToAlerts }) {
  // 1. Dataset Split Data for Donut Chart
  const datasetSplitData = [
    { name: 'Illicit Entities', value: 4545, pct: 2.2, color: '#EF4444' },
    { name: 'Licit Entities', value: 42019, pct: 20.6, color: '#10B981' },
    { name: 'Unlabeled / Background', value: 157205, pct: 77.2, color: '#64748B' },
  ];

  // 2. Sparkline Data for Drift Trajectory (Timesteps 35–49)
  const sparklineData = rawDrift.map(d => ({
    timestep: d.timestep,
    f1_fixed_th: Number(d.f1_fixed_th.toFixed(3)),
    pr_auc: Number(d.pr_auc.toFixed(3)),
  }));

  // 3. Compact 5 Alerts Preview
  const recentAlerts = rawAlerts.slice(0, 5);

  return (
    <div 
      className="min-h-screen overflow-y-auto pb-12 px-4 py-6 md:px-8" 
      style={{ 
        width: '100%', 
        minHeight: '100vh', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '1.75rem', 
        paddingBottom: '4rem' 
      }}
    >
      
      {/* 1. Hero Header Banner with CTA */}
      <div className="glass-panel" style={{
        padding: '1.5rem 1.75rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1.25rem',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(10, 14, 23, 0.98) 100%)',
        border: '1px solid rgba(6, 182, 212, 0.25)',
        boxShadow: '0 0 40px rgba(6, 182, 212, 0.08)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{
            width: '52px',
            height: '52px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.25) 0%, rgba(239, 68, 68, 0.25) 100%)',
            border: '1px solid rgba(6, 182, 212, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#06B6D4',
            boxShadow: '0 0 25px rgba(6, 182, 212, 0.25)',
            flexShrink: 0
          }}>
            <ShieldAlert size={28} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: '1.4rem', fontWeight: 900, letterSpacing: '-0.02em', margin: 0 }}>
                1. Situation Room & Executive Telemetry
              </h1>
              <span style={{
                padding: '3px 9px',
                borderRadius: '6px',
                fontSize: '0.72rem',
                fontWeight: 800,
                background: 'rgba(6, 182, 212, 0.15)',
                color: '#38BDF8',
                border: '1px solid rgba(6, 182, 212, 0.35)',
                letterSpacing: '0.04em'
              }}>
                PERIMETER ACTIVE
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.3rem', maxWidth: '750px' }}>
              Autonomous monitoring of Elliptic cryptocurrency transaction graph. Tracking 203,769 entities across timesteps 35–49 with temporal drift supervision.
            </p>
          </div>
        </div>

        {/* Primary Call-to-Action */}
        <button
          onClick={() => onNavigateToGraph('174515')}
          className="btn-primary"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem',
            padding: '0.85rem 1.6rem',
            borderRadius: '10px',
            fontSize: '0.9rem',
            fontWeight: 800,
            background: 'linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%)',
            color: '#FFF',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            whiteSpace: 'nowrap'
          }}
        >
          <Sparkles size={18} />
          <span>Launch Deep Investigation (Cluster #174515)</span>
          <ArrowRight size={17} />
        </button>
      </div>

      {/* 2. Hero 4 KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 kpi-grid">
        {/* KPI 1: Total Transactions Monitored */}
        <div className="glass-panel" style={{ padding: '1.35rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Total Monitored Entities
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(6, 182, 212, 0.15)', color: '#06B6D4' }}>
              <Database size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.65rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '2.1rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: '#FFF' }}>
              203,769
            </span>
          </div>
          <div style={{ fontSize: '0.78rem', color: '#38BDF8', fontWeight: 600, marginTop: '0.2rem' }}>
            234,355 directed edges
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Full Elliptic Bitcoin temporal dataset
          </div>
        </div>

        {/* KPI 2: Dataset Ground Truth Split */}
        <div className="glass-panel" style={{ padding: '1.35rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Dataset Ground Truth Split
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', color: '#F87171' }}>
              <Layers size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.65rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <div style={{ fontSize: '0.92rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#FFF' }}>
              <span style={{ color: '#EF4444' }}>4,545 Illicit (2%)</span>
              <span style={{ color: 'var(--text-muted)', margin: '0 6px' }}>|</span>
              <span style={{ color: '#10B981' }}>42,019 Licit (21%)</span>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#94A3B8', fontFamily: 'var(--font-mono)' }}>
              157,205 Unknown (77%)
            </div>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            Extreme label sparsity & high class imbalance
          </div>
        </div>

        {/* KPI 3: Model Health Status with pulse */}
        <div className="glass-panel" style={{ padding: '1.35rem', border: '1px solid rgba(239, 68, 68, 0.4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#F87171', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Model Health Status
            </span>
            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: '#EF4444',
              boxShadow: '0 0 12px #EF4444'
            }} />
          </div>
          <div style={{ marginTop: '0.65rem' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '4px 10px',
              borderRadius: '6px',
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid #EF4444',
              color: '#F87171',
              fontWeight: 800,
              fontSize: '0.78rem'
            }}>
              <AlertTriangle size={14} />
              <span>CRITICAL DRIFT DETECTED (t=43)</span>
            </div>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#FCA5A5', marginTop: '0.45rem' }}>
            Covariate shift triggered by Dark Market shutdown
          </div>
        </div>

        {/* KPI 4: Pre-Drift vs Post-Drift F1 */}
        <div className="glass-panel" style={{ padding: '1.35rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Pre-Drift vs Post-Drift F1
            </span>
            <div style={{ padding: '6px', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.15)', color: '#F59E0B' }}>
              <TrendingDown size={18} />
            </div>
          </div>
          <div style={{ marginTop: '0.65rem', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.9rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: '#EF4444' }}>
              0.86 → 0.00
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#FBBF24', fontWeight: 700, marginTop: '0.2rem' }}>
            Dark Market Event Shock
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Requires dynamic threshold adaptation
          </div>
        </div>
      </div>

      {/* 3. Responsive 2-Column Grid: Donut Chart & Drift Sparkline */}
      <div className="charts-grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Card A: Risk Composition Donut Chart */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>Risk Composition & Class Breakdown</h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Visual breakdown: 2% Illicit, 21% Licit, 77% Unlabeled background
              </p>
            </div>
          </div>

          <div 
            className="h-[240px] sm:h-[300px]" 
            style={{ 
              width: '100%', 
              position: 'relative', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <Pie
                  data={datasetSplitData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={92}
                  paddingAngle={3}
                  stroke="rgba(15, 23, 42, 0.9)"
                  strokeWidth={2}
                >
                  {datasetSplitData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val, name) => [`${val.toLocaleString()} entities`, name]}
                  contentStyle={{
                    background: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    color: '#FFF'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>

            {/* Centered Donut Badge */}
            <div style={{
              position: 'absolute',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              pointerEvents: 'none'
            }}>
              <span style={{ fontSize: '1.45rem', fontWeight: 900, fontFamily: 'var(--font-mono)', color: '#FFF' }}>
                203.7k
              </span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.05em' }}>
                TOTAL NODES
              </span>
            </div>
          </div>

          {/* Donut Legend */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.5rem',
            marginTop: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            {datasetSplitData.map((item, idx) => (
              <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.color }} />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{item.name.split(' ')[0]}</span>
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: item.color }}>
                  {item.pct}% <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>({item.value.toLocaleString()})</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Card B: Temporal Trajectory Sparkline */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>Temporal Trajectory Sparkline</h3>
                <span style={{
                  padding: '2px 7px',
                  borderRadius: '4px',
                  background: 'rgba(239, 68, 68, 0.2)',
                  color: '#F87171',
                  fontSize: '0.68rem',
                  fontWeight: 800
                }}>
                  t=35 &rarr; t=49
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                F1 score (cyan) and PR-AUC (amber) plunge at timestep 43 dark market seizure
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', fontSize: '0.72rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <div style={{ width: '10px', height: '3px', background: '#06B6D4', borderRadius: '2px' }} />
                <span style={{ color: '#94A3B8' }}>F1 Fixed</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <div style={{ width: '10px', height: '3px', background: '#F59E0B', borderRadius: '2px' }} />
                <span style={{ color: '#94A3B8' }}>PR-AUC</span>
              </div>
            </div>
          </div>

          <div className="h-[240px] sm:h-[300px]" style={{ width: '100%', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparklineData} margin={{ top: 20, right: 25, left: -15, bottom: 10 }}>
                <XAxis 
                  dataKey="timestep" 
                  stroke="#64748B" 
                  tick={{ fontSize: 10, fill: '#94A3B8' }}
                  tickFormatter={(val) => `t=${val}`}
                />
                <YAxis 
                  domain={[0, 1.05]} 
                  stroke="#64748B" 
                  tick={{ fontSize: 10, fill: '#94A3B8' }}
                  tickFormatter={(val) => val.toFixed(1)}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const d = payload[0].payload;
                    return (
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.95)',
                        border: d.timestep === 43 ? '1px solid #EF4444' : '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '6px',
                        padding: '0.5rem 0.75rem',
                        fontSize: '0.72rem',
                        color: '#FFF'
                      }}>
                        <div style={{ fontWeight: 800 }}>Timestep {d.timestep}</div>
                        <div style={{ color: '#06B6D4' }}>F1 Fixed: {d.f1_fixed_th}</div>
                        <div style={{ color: '#F59E0B' }}>PR-AUC: {d.pr_auc}</div>
                        {d.timestep === 43 && <div style={{ color: '#EF4444', fontWeight: 800, marginTop: '2px' }}>&bull; Dark Market Seizure Shock</div>}
                      </div>
                    );
                  }}
                />
                <ReferenceLine 
                  x={43} 
                  stroke="#EF4444" 
                  strokeDasharray="3 3"
                  strokeWidth={2}
                  label={{
                    value: 't=43 Shutdown',
                    position: 'top',
                    fill: '#EF4444',
                    fontSize: 10,
                    fontWeight: 800
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="f1_fixed_th" 
                  stroke="#06B6D4" 
                  strokeWidth={2.5} 
                  dot={{ r: 2.5, fill: '#06B6D4' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="pr_auc" 
                  stroke="#F59E0B" 
                  strokeWidth={2.5} 
                  dot={{ r: 2.5, fill: '#F59E0B' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            paddingTop: '0.75rem'
          }}>
            <span>Pre-Seizure Stability (t=35&ndash;42): Avg F1 0.88</span>
            <span style={{ color: '#F87171', fontWeight: 700 }}>Post-Seizure Shock (t=43&ndash;49): Avg F1 0.02</span>
          </div>
        </div>

      </div>

      {/* 4. Bottom Section: Recent High-Risk Alerts Preview (5 Rows) */}
      <div className="glass-panel" style={{ padding: '1.5rem', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>Recent High-Risk Intercepts Preview</h3>
              <span style={{
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '0.7rem',
                fontWeight: 700,
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#F87171',
                border: '1px solid rgba(239, 68, 68, 0.3)'
              }}>
                5 Active Flags
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Top priority transactions from alerts queue requiring immediate graph inspection
            </p>
          </div>

          <button
            onClick={onNavigateToAlerts}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.5rem 1rem',
              borderRadius: '7px',
              fontSize: '0.78rem',
              fontWeight: 700,
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.35)',
              color: '#38BDF8',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <span>View Full Queue (50 Alerts)</span>
            <ArrowRight size={14} />
          </button>
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                color: 'var(--text-muted)',
                fontSize: '0.72rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                <th style={{ padding: '0.75rem 1rem' }}>Node Identifier</th>
                <th style={{ padding: '0.75rem 1rem' }}>Timestep</th>
                <th style={{ padding: '0.75rem 1rem' }}>Risk Score</th>
                <th style={{ padding: '0.75rem 1rem' }}>Classification</th>
                <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Forensic Action</th>
              </tr>
            </thead>
            <tbody>
              {recentAlerts.map((alert) => (
                <tr
                  key={alert.node_id}
                  onClick={() => onNavigateToGraph(alert.node_id)}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    cursor: 'pointer',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(6, 182, 212, 0.08)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '0.75rem 1rem' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#38BDF8' }}>
                      #{alert.node_id}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem 1rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                    T-{alert.timestep}
                  </td>
                  <td style={{ padding: '0.75rem 1rem' }}>
                    <span style={{ fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#EF4444' }}>
                      {(alert.risk_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem 1rem' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '0.68rem',
                      fontWeight: 800,
                      background: alert.true_label === 1 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                      color: alert.true_label === 1 ? '#F87171' : '#FBBF24',
                      border: alert.true_label === 1 ? '1px solid #EF4444' : '1px solid #F59E0B'
                    }}>
                      {alert.true_label === 1 ? 'ILLICIT / DARKNET' : 'UNDER REVIEW'}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onNavigateToGraph(alert.node_id);
                      }}
                      style={{
                        padding: '0.35rem 0.75rem',
                        borderRadius: '5px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        background: 'rgba(6, 182, 212, 0.15)',
                        border: '1px solid rgba(6, 182, 212, 0.4)',
                        color: '#38BDF8',
                        cursor: 'pointer'
                      }}
                    >
                      Investigate in Graph &rarr;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
