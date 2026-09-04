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
    <div className="w-full flex flex-col gap-6 pb-12">
      
      {/* 1. Hero Header Banner with CTA */}
      <div className="glass-panel w-full p-4 sm:p-6 rounded-2xl flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-[#0d1527] to-[#0a0f1d] border border-cyan-500/20 shadow-[0_0_30px_rgba(6,182,212,0.05)]">
        
        {/* Left: Text & Badges */}
        <div className="flex flex-col gap-2 max-w-2xl min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg sm:text-2xl font-bold text-white tracking-tight">
              1. Situation Room &amp; Executive Telemetry
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] sm:text-xs font-semibold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 whitespace-nowrap">
              Perimeter Active
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Autonomous monitoring of Elliptic cryptocurrency transaction graph. Tracking 203,769 entities across timesteps 35–49 with temporal drift supervision.
          </p>
        </div>

        {/* Right: CTA Action Button */}
        <button 
          onClick={() => onNavigateToGraph('174515')}
          className="w-full md:w-auto shrink-0 flex items-center justify-center gap-2 px-4 py-2.5 sm:px-5 sm:py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs sm:text-sm transition-all duration-150 shadow-[0_0_20px_rgba(6,182,212,0.3)] active:scale-95 min-w-0"
        >
          <Sparkles size={18} className="shrink-0" />
          <span className="truncate">Launch Deep Investigation (Cluster #174515)</span>
          <ArrowRight size={17} className="shrink-0" />
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
            Extreme label sparsity &amp; high class imbalance
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
      <div className="charts-grid grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Card A: Risk Composition Donut Chart */}
        <div className="glass-panel p-4 sm:p-6 flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <div>
              <h3 className="text-sm sm:text-base font-extrabold text-white">Risk Composition &amp; Class Breakdown</h3>
              <p className="text-xs text-slate-400">
                Visual breakdown: 2% Illicit, 21% Licit, 77% Unlabeled background
              </p>
            </div>
          </div>

          <div className="w-full h-[240px] sm:h-[300px] relative flex items-center justify-center">
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
            <div className="absolute flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xl sm:text-2xl font-black font-mono text-white">
                203.7k
              </span>
              <span className="text-[10px] text-slate-400 font-bold tracking-wider">
                TOTAL NODES
              </span>
            </div>
          </div>

          {/* Donut Legend */}
          <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-white/10">
            {datasetSplitData.map((item, idx) => (
              <div key={idx} className="flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: item.color }} />
                  <span className="text-[11px] text-slate-300 truncate">{item.name.split(' ')[0]}</span>
                </div>
                <div className="text-xs sm:text-sm font-bold font-mono" style={{ color: item.color }}>
                  {item.pct}% <span className="text-[10px] text-slate-400 font-normal">({item.value.toLocaleString()})</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Card B: Temporal Trajectory Sparkline */}
        <div className="glass-panel p-4 sm:p-6 flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-extrabold text-white">Temporal Trajectory Sparkline</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                  t=35 &rarr; t=49
                </span>
              </div>
              <p className="text-xs text-slate-400">
                F1 score (cyan) and PR-AUC (amber) plunge at timestep 43 dark market seizure
              </p>
            </div>

            <div className="flex items-center gap-3 text-xs shrink-0">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-1 bg-cyan-400 rounded-sm" />
                <span className="text-slate-300">F1 Fixed</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-1 bg-amber-400 rounded-sm" />
                <span className="text-slate-300">PR-AUC</span>
              </div>
            </div>
          </div>

          <div className="w-full h-[240px] sm:h-[300px] relative">
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
                      <div className="bg-slate-900/95 border border-white/10 rounded-lg p-2.5 text-xs text-white shadow-xl">
                        <div className="font-bold text-slate-200">Timestep {d.timestep}</div>
                        <div className="text-cyan-400">F1 Fixed: {d.f1_fixed_th}</div>
                        <div className="text-amber-400">PR-AUC: {d.pr_auc}</div>
                        {d.timestep === 43 && <div className="text-red-400 font-bold mt-1">&bull; Dark Market Seizure Shock</div>}
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

          <div className="flex flex-col sm:flex-row sm:justify-between items-start sm:items-center text-xs text-slate-400 border-t border-white/10 pt-3 mt-1 gap-1">
            <span>Pre-Seizure Stability (t=35&ndash;42): Avg F1 0.88</span>
            <span className="text-red-400 font-bold">Post-Seizure Shock (t=43&ndash;49): Avg F1 0.02</span>
          </div>
        </div>

      </div>

      {/* 4. Bottom Section: Recent High-Risk Alerts Preview (Defensive Data Table) */}
      <div className="glass-panel p-4 sm:p-6 w-full flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm sm:text-base font-extrabold text-white">Recent High-Risk Intercepts Preview</h3>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-red-500/15 text-red-400 border border-red-500/30 whitespace-nowrap">
                5 Active Flags
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Top priority transactions from alerts queue requiring immediate graph inspection
            </p>
          </div>

          <button
            onClick={onNavigateToAlerts}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/35 text-cyan-400 transition-all cursor-pointer w-fit"
          >
            <span>View Full Queue (50 Alerts)</span>
            <ArrowRight size={14} />
          </button>
        </div>

        {/* Responsive Wrapped Defensive Table */}
        <div className="w-full overflow-x-auto border border-white/10 rounded-xl no-scrollbar">
          <table className="w-full min-w-[650px] text-left text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 text-xs uppercase tracking-wider bg-white/[0.02]">
                <th className="p-3 sm:px-4 sm:py-3 whitespace-nowrap font-semibold">Node Identifier</th>
                <th className="p-3 sm:px-4 sm:py-3 whitespace-nowrap font-semibold">Timestep</th>
                <th className="p-3 sm:px-4 sm:py-3 whitespace-nowrap font-semibold">Risk Score</th>
                <th className="p-3 sm:px-4 sm:py-3 whitespace-nowrap font-semibold">Classification</th>
                <th className="p-3 sm:px-4 sm:py-3 whitespace-nowrap font-semibold text-right">Forensic Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {recentAlerts.map((alert) => (
                <tr
                  key={alert.node_id}
                  onClick={() => onNavigateToGraph(alert.node_id)}
                  className="hover:bg-cyan-500/[0.07] cursor-pointer transition-colors"
                >
                  <td className="p-3 sm:px-4 sm:py-3 whitespace-nowrap">
                    <span className="font-mono font-bold text-cyan-400">
                      #{alert.node_id}
                    </span>
                  </td>
                  <td className="p-3 sm:px-4 sm:py-3 whitespace-nowrap text-slate-300 font-mono text-xs">
                    T-{alert.timestep}
                  </td>
                  <td className="p-3 sm:px-4 sm:py-3 whitespace-nowrap">
                    <span className="font-mono font-bold text-red-400">
                      {(alert.risk_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="p-3 sm:px-4 sm:py-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      alert.true_label === 1 
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40' 
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}>
                      {alert.true_label === 1 ? 'ILLICIT / DARKNET' : 'UNDER REVIEW'}
                    </span>
                  </td>
                  <td className="p-3 sm:px-4 sm:py-3 whitespace-nowrap text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onNavigateToGraph(alert.node_id);
                      }}
                      className="px-2.5 py-1 rounded text-xs font-semibold bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-400 cursor-pointer inline-flex items-center gap-1 transition-all"
                    >
                      <span>Investigate in Graph</span>
                      <ArrowRight size={12} />
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
