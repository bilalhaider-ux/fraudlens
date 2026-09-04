import React, { useState } from 'react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ReferenceLine 
} from 'recharts';
import rawDrift from '../assets/drift.json';

export default function SituationRoom({ setActiveScreen, onNavigateToGraph }) {
  const [showLeakAudit, setShowLeakAudit] = useState(false);

  const handleLaunchInvestigation = () => {
    if (typeof onNavigateToGraph === 'function') {
      onNavigateToGraph('174085');
    }
    if (typeof setActiveScreen === 'function') {
      setActiveScreen(2);
    }
  };

  const timesteps = Array.isArray(rawDrift) ? rawDrift : (rawDrift?.timesteps || []);
  const sparklineData = timesteps.map(d => ({
    timestep: d.timestep,
    f1: Number((d.f1 !== undefined ? d.f1 : d.f1_fixed_th || 0).toFixed(3)),
    recall: Number((d.recall !== undefined ? d.recall : d.pr_auc || 0).toFixed(3)),
  }));

  return (
    <div className="w-full max-w-7xl mx-auto flex flex-col gap-5 py-4 px-3 sm:px-6">
      
      {/* 1. Hero Executive Telemetry Banner */}
      <div className="w-full p-4 sm:p-6 rounded-2xl flex flex-col md:flex-row md:items-center md:justify-between gap-5 bg-gradient-to-r from-[#0d1527] to-[#0a0f1d] border border-cyan-500/20 shadow-[0_0_30px_rgba(6,182,212,0.05)]">
        <div className="flex items-start gap-3.5 sm:gap-4 max-w-2xl min-w-0">
          <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0 mt-0.5">
            <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div className="flex flex-col gap-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-base sm:text-xl md:text-2xl font-bold text-white tracking-tight">
                1. Situation Room & Executive Telemetry
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 whitespace-nowrap">
                Perimeter Active
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Autonomous monitoring of Elliptic cryptocurrency transaction graph. Tracking 203,769 entities across timesteps 35–49 with causal zero-leakage supervision.
            </p>
          </div>
        </div>

        <button 
          onClick={handleLaunchInvestigation}
          className="w-full md:w-auto shrink-0 flex items-center justify-center gap-2 px-4 py-2.5 sm:px-5 sm:py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs sm:text-sm transition-all duration-150 shadow-[0_0_20px_rgba(6,182,212,0.3)] active:scale-95 cursor-pointer whitespace-nowrap"
        >
          <span>Launch Deep Investigation (Seed #174085)</span>
          <span className="text-base font-bold">&rarr;</span>
        </button>
      </div>

      {/* 2. Operational Metrics Grid (With Zero-Leakage Macro F1) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Macro F1 + Leak-Free Modal Trigger */}
        <div className="p-4 rounded-xl bg-[#0d1424] border border-cyan-500/30 flex flex-col justify-between relative">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <div className="flex items-center gap-1.5">
              <span>Champion Macro F1</span>
              <button 
                onClick={() => setShowLeakAudit(!showLeakAudit)}
                className="w-4 h-4 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center text-[10px] hover:bg-cyan-500/40 transition-colors"
                title="Zero-Leakage Audit Details"
              >
                i
              </button>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Zero-Leak
            </span>
          </div>

          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-black text-cyan-400">0.5322</span>
              <span className="text-xs text-emerald-400 font-mono font-medium">+6.57 pts</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Honest literature baseline: 0.4665</p>
            <p className="text-[10px] text-slate-500">Beats Weber et al. without test-label leakage</p>
          </div>

          {/* Micro-Audit Popup */}
          {showLeakAudit && (
            <div className="absolute top-12 left-2 right-2 z-30 p-3 rounded-xl bg-[#080d1a] border border-cyan-500/50 shadow-2xl text-xs text-slate-300">
              <div className="flex justify-between items-center mb-1 font-bold text-cyan-400">
                <span>Zero-Leakage Protocol</span>
                <button onClick={() => setShowLeakAudit(false)} className="text-slate-400 hover:text-white">✕</button>
              </div>
              <p className="text-[11px] leading-relaxed text-slate-400">
                <strong className="text-slate-200">Strict Temporal Split:</strong> Literature models claiming &gt;0.95 F1 query future test labels via transductive graph walks. FraudLens enforces 100% causal separation (train: t&lt;35, blind stream: t&ge;35).
              </p>
            </div>
          )}
        </div>

        {/* Card 2: Ground Truth & Recovery */}
        <div className="p-4 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Syndicate Recovery</span>
            <span className="text-cyan-400 font-mono text-[10px]">Engine 2</span>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-black text-white">76.45%</span>
              <span className="text-xs text-cyan-400 font-mono">Hit@50</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Single-seed localized PPR expansion</p>
            <p className="text-[10px] text-slate-500">Recovers multi-hop evasive laundering rings</p>
          </div>
        </div>

        {/* Card 3: Model Health Status */}
        <div className="p-4 rounded-xl bg-[#0d1424] border border-rose-500/20 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Model Health Status</span>
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
          </div>
          <div className="mt-3">
            <div className="px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-semibold">
              CRITICAL DRIFT DETECTED (t=43)
            </div>
            <p className="text-[10px] text-slate-400 mt-2">
              <strong className="text-rose-400">Post-Drift Recall: 57.4%</strong> (97 of 169 caught)
            </p>
          </div>
        </div>

        {/* Card 4: Pre vs Post Drift Performance */}
        <div className="p-4 rounded-xl bg-[#0d1424] border border-white/10 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Pre vs Post Drift F1</span>
            <span className="text-amber-400">📉</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">0.8483</span>
            <span className="text-slate-500">&rarr;</span>
            <span className="text-2xl font-bold text-amber-400">0.1709</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Literature post-drift collapses to 0.0860</p>
          <p className="text-[10px] text-emerald-400/90 font-medium">FraudLens sustains +98.7% edge</p>
        </div>

      </div>

      {/* 3. Benchmark & Integrity Audit Card (Arqam Spec) */}
      <div className="w-full p-4 sm:p-5 rounded-xl bg-[#0c121e] border border-white/10 flex flex-col gap-3 font-mono">
        <div className="flex items-center justify-between border-b border-white/10 pb-2">
          <span className="text-xs sm:text-sm font-bold text-white tracking-wide">
            BENCHMARK &amp; INTEGRITY AUDIT
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            [Zero-Leak]
          </span>
        </div>

        {/* Defensive Scroll Table */}
        <div className="w-full overflow-x-auto rounded-lg border border-white/5 scrollbar-none">
          <table className="w-full min-w-[540px] text-left text-xs border-collapse">
            <thead>
              <tr className="bg-white/5 text-slate-400 border-b border-white/10">
                <th className="py-2.5 px-3 font-semibold">System / Implementation</th>
                <th className="py-2.5 px-3 font-semibold">Macro F1</th>
                <th className="py-2.5 px-3 font-semibold">Post-Drift F1</th>
                <th className="py-2.5 px-3 font-semibold">Leak-Free?</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              <tr className="hover:bg-white/[0.02]">
                <td className="py-2 px-3 text-slate-400">Weber et al. (Baseline)</td>
                <td className="py-2 px-3 font-mono">0.4665</td>
                <td className="py-2 px-3 font-mono text-slate-400">0.0860</td>
                <td className="py-2 px-3">
                  <span className="text-[10px] text-slate-400 font-sans px-1.5 py-0.5 rounded bg-slate-800">Strict</span>
                </td>
              </tr>
              <tr className="hover:bg-white/[0.02] text-rose-300/80">
                <td className="py-2 px-3">Leaked Literature SOTA</td>
                <td className="py-2 px-3 font-mono">0.9680*</td>
                <td className="py-2 px-3 font-mono">0.9564*</td>
                <td className="py-2 px-3">
                  <span className="text-[10px] text-rose-400 font-sans px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">Transductive</span>
                </td>
              </tr>
              <tr className="bg-cyan-500/5 text-cyan-300 font-semibold border-t border-cyan-500/20">
                <td className="py-2.5 px-3 text-white flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                  FraudLens Champion
                </td>
                <td className="py-2.5 px-3 font-mono text-cyan-300">0.5322</td>
                <td className="py-2.5 px-3 font-mono text-cyan-300">0.1709</td>
                <td className="py-2.5 px-3">
                  <span className="text-[10px] text-emerald-400 font-sans px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30">Audited</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p className="text-[10px] text-slate-500 italic mt-0.5">
          *Literature &gt;0.95 F1 involves transductive query leakage on test labels. FraudLens operates under 100% causal out-of-time streaming.
        </p>
      </div>

      {/* 4. Temporal Trajectory Sparkline */}
      <div className="w-full p-4 sm:p-6 rounded-xl bg-[#0c121e] border border-white/10 flex flex-col gap-4 font-sans">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-white/5 pb-3">
          <div>
            <h2 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
              Temporal Trajectory Sparkline
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-400 border border-rose-500/30">
                t=35 &rarr; t=49
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              F1 Score (cyan) and Recall (amber) plunge at timestep 43 dark market seizure.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="flex items-center gap-1.5 text-cyan-400">
              <span className="w-2.5 h-0.5 bg-cyan-400 inline-block"></span> F1 Score
            </span>
            <span className="flex items-center gap-1.5 text-amber-400">
              <span className="w-2.5 h-0.5 bg-amber-400 inline-block"></span> Recall
            </span>
          </div>
        </div>

        {/* Recharts Interactive Line Chart */}
        <div className="w-full h-[220px] sm:h-[260px] relative">
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
                      <div className="text-cyan-400">F1: {d.f1}</div>
                      <div className="text-amber-400">Recall: {d.recall}</div>
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
                dataKey="f1" 
                stroke="#06B6D4" 
                strokeWidth={2.5} 
                dot={{ r: 2.5, fill: '#06B6D4' }}
              />
              <Line 
                type="monotone" 
                dataKey="recall" 
                stroke="#F59E0B" 
                strokeWidth={2.5} 
                dot={{ r: 2.5, fill: '#F59E0B' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Stability Metrics Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-white/5 text-xs font-mono">
          <div className="flex items-center justify-between sm:justify-start sm:gap-4">
            <span className="text-slate-400">Pre-Seizure Stability (t=35–42):</span>
            <span className="font-bold text-emerald-400">Avg F1 0.8483</span>
          </div>
          <div className="flex items-center justify-between sm:justify-start sm:gap-4">
            <span className="text-slate-400">Post-Seizure Shock (t=43–49):</span>
            <span className="font-bold text-rose-400">Avg F1 0.1709</span>
          </div>
        </div>
      </div>

    </div>
  );
}
