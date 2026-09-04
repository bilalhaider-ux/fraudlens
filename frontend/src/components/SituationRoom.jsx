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
import { ArrowRight } from 'lucide-react';
import rawAlerts from '../assets/alerts.json';
import rawDrift from '../assets/drift.json';

export default function SituationRoom({ setActiveScreen, onNavigateToGraph, onNavigateToAlerts }) {
  const navigateToScreen2 = (nodeId = '174515') => {
    if (typeof onNavigateToGraph === 'function') {
      onNavigateToGraph(nodeId);
    }
    if (typeof setActiveScreen === 'function') {
      setActiveScreen(2);
    }
  };

  const navigateToScreen4 = () => {
    if (typeof onNavigateToAlerts === 'function') {
      onNavigateToAlerts();
    }
    if (typeof setActiveScreen === 'function') {
      setActiveScreen(4);
    }
  };

  // 1. Dataset Split Data for Donut Chart
  const datasetSplitData = [
    { name: 'Illicit Entities', value: 4545, pct: 2.2, color: '#F43F5E' },
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
    <div className="w-full max-w-7xl mx-auto flex flex-col gap-5 py-4 px-3 sm:px-6">
      
      {/* Screen 1 Hero Banner */}
      <div className="w-full p-5 sm:p-6 rounded-2xl flex flex-col md:flex-row md:items-center md:justify-between gap-5 bg-gradient-to-r from-[#0d1527] to-[#0a0f1d] border border-cyan-500/20 shadow-[0_0_30px_rgba(6,182,212,0.05)]">
        
        {/* Left: Shield Emblem + Description */}
        <div className="flex items-start gap-4 max-w-2xl min-w-0">
          <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0 mt-0.5">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>

          <div className="flex flex-col gap-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                1. Situation Room & Executive Telemetry
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 whitespace-nowrap">
                Perimeter Active
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Autonomous monitoring of Elliptic cryptocurrency transaction graph. Tracking 203,769 entities across timesteps 35–49 with temporal drift supervision.
            </p>
          </div>
        </div>

        {/* Right: CTA Button */}
        <button 
          onClick={() => navigateToScreen2('174515')}
          className="w-full md:w-auto shrink-0 flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs sm:text-sm transition-all duration-150 shadow-[0_0_20px_rgba(6,182,212,0.3)] active:scale-95 cursor-pointer whitespace-nowrap"
        >
          <span>Launch Deep Investigation (Cluster #174515)</span>
          <span className="text-base font-bold">&rarr;</span>
        </button>

      </div>

      {/* 2. Core Operational Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Total Monitored Entities</span>
            <span className="text-cyan-400">⚡</span>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-black text-white">203,769</span>
            <p className="text-[11px] text-cyan-400/80 mt-1">234,355 directed edges</p>
            <p className="text-[10px] text-slate-500">Full Elliptic Bitcoin temporal dataset</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Ground Truth Split</span>
            <span className="text-rose-400">🛡️</span>
          </div>
          <div className="mt-3">
            <div className="text-xs sm:text-sm font-bold flex gap-2">
              <span className="text-rose-400">4,545 Illicit (2%)</span>
              <span className="text-emerald-400">42,019 Licit (21%)</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">157,205 Unknown (77%)</p>
            <p className="text-[10px] text-slate-500">Extreme label sparsity &amp; high class imbalance</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1424] border border-rose-500/20 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Model Health Status</span>
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
          </div>
          <div className="mt-3">
            <div className="px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-semibold">
              CRITICAL DRIFT DETECTED (t=43)
            </div>
            <p className="text-[10px] text-slate-500 mt-2">Covariate shift triggered by Dark Market shutdown</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Pre vs Post-Drift F1</span>
            <span className="text-amber-400">📉</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-400">0.86</span>
            <span className="text-slate-500">&rarr;</span>
            <span className="text-2xl font-bold text-rose-600">0.00</span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Requires dynamic threshold adaptation</p>
        </div>
      </div>

      {/* 3. Temporal Stability Trajectory & Sparkline Section */}
      <div className="w-full p-4 sm:p-6 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-white/5 pb-3">
          <div>
            <h2 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
              Temporal Trajectory Sparkline
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-400 border border-rose-500/30">
                t=35 &rarr; t=49
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              F1 Score (cyan) and PR-AUC (amber) plunge at timestep 43 dark market seizure.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="flex items-center gap-1.5 text-cyan-400">
              <span className="w-2.5 h-0.5 bg-cyan-400 inline-block"></span> F1 Fixed
            </span>
            <span className="flex items-center gap-1.5 text-amber-400">
              <span className="w-2.5 h-0.5 bg-amber-400 inline-block"></span> PR-AUC
            </span>
          </div>
        </div>

        {/* Recharts Interactive Line Chart */}
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
                      {d.timestep === 43 && <div className="text-rose-400 font-bold mt-1">&bull; Dark Market Seizure Shock</div>}
                    </div>
                  );
                }}
              />
              <ReferenceLine 
                x={43} 
                stroke="#F43F5E" 
                strokeDasharray="3 3"
                strokeWidth={2}
                label={{
                  value: 't=43 Shutdown',
                  position: 'top',
                  fill: '#F43F5E',
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

        {/* Stability Metrics Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-white/5 text-xs">
          <div className="flex items-center justify-between sm:justify-start sm:gap-4">
            <span className="text-slate-400">Pre-Seizure Stability (t=35–42):</span>
            <span className="font-mono font-bold text-emerald-400">Avg F1 0.88</span>
          </div>
          <div className="flex items-center justify-between sm:justify-start sm:gap-4">
            <span className="text-slate-400">Post-Seizure Shock (t=43–49):</span>
            <span className="font-mono font-bold text-rose-400">Avg F1 0.02</span>
          </div>
        </div>
      </div>

      {/* 4. Risk Composition Donut Card */}
      <div className="w-full p-4 sm:p-6 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col gap-4">
        <div className="flex justify-between items-center mb-1">
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
        <div className="grid grid-cols-3 gap-2 pt-3 border-t border-white/10">
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

      {/* 5. Defensive Data Table: Recent High-Risk Alerts Preview */}
      <div className="w-full p-4 sm:p-6 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm sm:text-base font-extrabold text-white">Recent High-Risk Intercepts Preview</h3>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 whitespace-nowrap">
                5 Active Flags
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Top priority transactions from alerts queue requiring immediate graph inspection
            </p>
          </div>

          <button
            onClick={navigateToScreen4}
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
                  onClick={() => navigateToScreen2(alert.node_id)}
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
                    <span className="font-mono font-bold text-rose-400">
                      {(alert.risk_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="p-3 sm:px-4 sm:py-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      alert.true_label === 1 
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' 
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}>
                      {alert.true_label === 1 ? 'ILLICIT / DARKNET' : 'UNDER REVIEW'}
                    </span>
                  </td>
                  <td className="p-3 sm:px-4 sm:py-3 whitespace-nowrap text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigateToScreen2(alert.node_id);
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
