import React, { useState, useEffect } from 'react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ReferenceLine,
  ReferenceArea
} from 'recharts';
import { 
  Activity, 
  AlertTriangle, 
  TrendingDown, 
  TrendingUp, 
  ShieldAlert, 
  Calendar,
  Layers, 
  Info, 
  Clock, 
  Zap 
} from 'lucide-react';
import driftDataRaw from '../assets/drift.json';

export default function DriftMonitor() {
  const [data] = useState(driftDataRaw);
  const [showAdaptiveF1, setShowAdaptiveF1] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(typeof window !== 'undefined' && window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Pre-shutdown (35-42) and Post-shutdown (43-49) statistics
  const preShutdown = data.filter(d => d.timestep < 43);
  const postShutdown = data.filter(d => d.timestep >= 43);

  const avgPrAucPre = (preShutdown.reduce((acc, d) => acc + d.pr_auc, 0) / preShutdown.length).toFixed(3);
  const avgPrAucPost = (postShutdown.reduce((acc, d) => acc + d.pr_auc, 0) / postShutdown.length).toFixed(3);
  const shockDropPct = (((avgPrAucPre - avgPrAucPost) / avgPrAucPre) * 100).toFixed(1);

  // Format data for chart
  const chartData = data.map(d => ({
    timestep: d.timestep,
    timestepLabel: `T-${d.timestep}`,
    f1_fixed_th: Number(d.f1_fixed_th.toFixed(4)),
    pr_auc: Number(d.pr_auc.toFixed(4)),
    f1_adaptive_th: Number(d.f1_adaptive_th.toFixed(4)),
    n_illicit: d.n_illicit,
    total_nodes: d.total_nodes,
    illicit_rate: ((d.n_illicit / (d.total_nodes || 1)) * 100).toFixed(1)
  }));

  // Custom Recharts Dark Tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;

    const row = payload[0]?.payload;
    const isShutdownStep = row?.timestep === 43;

    return (
      <div style={{
        background: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(12px)',
        border: isShutdownStep ? '1px solid #EF4444' : '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '8px',
        padding: '0.85rem 1rem',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
        color: '#FFF',
        minWidth: '220px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#FFF' }}>
            Timestep {row?.timestep}
          </span>
          {isShutdownStep ? (
            <span style={{
              fontSize: '0.68rem',
              fontWeight: 800,
              padding: '2px 6px',
              borderRadius: '4px',
              background: 'rgba(239, 68, 68, 0.25)',
              color: '#F87171',
              border: '1px solid #EF4444'
            }}>
              🚨 CRITICAL DRIFT SHOCK
            </span>
          ) : (
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              {row?.timestep < 43 ? 'Pre-Shutdown Era' : 'Post-Shutdown Era'}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.78rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#06B6D4', fontWeight: 600 }}>Fixed F1 Score:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800 }}>{row?.f1_fixed_th}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#F59E0B', fontWeight: 600 }}>PR-AUC:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800 }}>{row?.pr_auc}</span>
          </div>
          {showAdaptiveF1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#A855F7', fontWeight: 600 }}>Adaptive F1:</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800 }}>{row?.f1_adaptive_th}</span>
            </div>
          )}
          <div style={{
            marginTop: '0.4rem',
            paddingTop: '0.4rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            color: 'var(--text-muted)',
            fontSize: '0.72rem'
          }}>
            <span>Illicit Nodes: {row?.n_illicit} / {row?.total_nodes}</span>
            <span>({row?.illicit_rate}%)</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Banner Header */}
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
            <Activity size={26} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Screen 4: Temporal Drift & Concept Shift Monitor</h2>
              <span style={{
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '0.72rem',
                fontWeight: 700,
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#F87171',
                border: '1px solid rgba(239, 68, 68, 0.3)'
              }}>
                Timesteps 35–49
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Recharts temporal evaluation tracking <strong style={{ color: '#06B6D4' }}>F1 (Fixed Threshold)</strong> and <strong style={{ color: '#F59E0B' }}>PR-AUC</strong> metrics across dark market seizure event.
            </p>
          </div>
        </div>

        {/* Toggle option */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <input
              type="checkbox"
              checked={showAdaptiveF1}
              onChange={(e) => setShowAdaptiveF1(e.target.checked)}
              style={{ accentColor: '#A855F7' }}
            />
            Show Adaptive F1 Curve
          </label>
        </div>
      </div>

      {/* KPI Shock Metric Cards */}
      <div className="kpi-grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Pre-Shutdown Performance */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Pre-Shutdown PR-AUC (T35-42)
            </span>
            <div style={{ padding: '4px', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.15)', color: '#10B981' }}>
              <TrendingUp size={16} />
            </div>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#34D399', marginTop: '0.5rem' }}>
            {avgPrAucPre}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            High predictive stability across initial baseline
          </div>
        </div>

        {/* Card 2: Post-Shutdown Shock */}
        <div className="glass-panel" style={{ padding: '1.25rem', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.72rem', color: '#F87171', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
              Post-Shutdown PR-AUC (T43-49)
            </span>
            <div style={{ padding: '4px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.2)', color: '#EF4444' }}>
              <TrendingDown size={16} />
            </div>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#EF4444', marginTop: '0.5rem' }}>
            {avgPrAucPost}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#FCA5A5', marginTop: '0.25rem' }}>
            Severe concept drift shock ({shockDropPct}% drop)
          </div>
        </div>

        {/* Card 3: Seizure Event Step */}
        <div className="glass-panel" style={{ padding: '1.25rem', background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.72rem', color: '#FBBF24', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
              Critical Inflection Point
            </span>
            <div style={{ padding: '4px', borderRadius: '6px', background: 'rgba(245, 158, 11, 0.2)', color: '#F59E0B' }}>
              <AlertTriangle size={16} />
            </div>
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#FFF', marginTop: '0.5rem' }}>
            Timestep 43
          </div>
          <div style={{ fontSize: '0.72rem', color: '#FBBF24', marginTop: '0.25rem', fontWeight: 600 }}>
            "Dark Market Shutdown" Seizure Action
          </div>
        </div>

        {/* Card 4: Graph Topology Shift */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Illicit Nodes Volume Collapse
            </span>
            <div style={{ padding: '4px', borderRadius: '6px', background: 'rgba(6, 182, 212, 0.15)', color: '#06B6D4' }}>
              <Layers size={16} />
            </div>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#38BDF8', marginTop: '0.5rem' }}>
            239 → 24
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            -89.9% sudden illicit transaction suppression
          </div>
        </div>
      </div>

      {/* Main Recharts Line Chart Visualization */}
      <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              Supervised GNN Performance Trajectory across Timesteps 35–49
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Vertical reference line highlights Timestep 43 concept drift shock where illicit dark market ecosystem dissolved.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <div style={{ width: '12px', height: '3px', background: '#06B6D4', borderRadius: '2px' }} />
              <span style={{ color: '#E2E8F0' }}>f1_fixed_th</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <div style={{ width: '12px', height: '3px', background: '#F59E0B', borderRadius: '2px' }} />
              <span style={{ color: '#E2E8F0' }}>pr_auc</span>
            </div>
            {showAdaptiveF1 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <div style={{ width: '12px', height: '3px', background: '#A855F7', borderRadius: '2px' }} />
                <span style={{ color: '#E2E8F0' }}>f1_adaptive_th</span>
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <div style={{ width: '12px', height: '1px', borderTop: '2px dashed #EF4444' }} />
              <span style={{ color: '#F87171' }}>Dark Market Shutdown (T-43)</span>
            </div>
          </div>
        </div>

        {/* Recharts Container */}
        <div className="w-full h-[300px] sm:h-[380px] min-h-[280px] relative mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 25, right: isMobile ? 12 : 30, left: isMobile ? -10 : 10, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" vertical={false} />
              
              <XAxis 
                dataKey="timestep" 
                stroke="#94A3B8"
                tick={{ fill: '#94A3B8', fontSize: isMobile ? 9 : 11, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(val) => `T-${val}`}
                domain={[35, 49]}
                type="number"
                tickCount={isMobile ? 8 : 15}
                interval={isMobile ? 1 : 0}
              />

              <YAxis 
                stroke="#94A3B8"
                domain={[0, 1.05]}
                tick={{ fill: '#94A3B8', fontSize: isMobile ? 9 : 11, fontFamily: 'var(--font-mono)' }}
                tickFormatter={(val) => val.toFixed(2)}
                width={isMobile ? 34 : 45}
              />

              <Tooltip content={<CustomTooltip />} />

              {/* Shaded Concept Drift Zone */}
              <ReferenceArea
                x1={43}
                x2={49}
                fill="rgba(239, 68, 68, 0.06)"
                strokeOpacity={0}
              />

              {/* Vertical Reference Line at Timestep 43 labeled "Dark Market Shutdown" */}
              <ReferenceLine
                x={43}
                stroke="#EF4444"
                strokeWidth={2.5}
                strokeDasharray="4 4"
                label={{
                  value: 'Dark Market Shutdown',
                  position: 'top',
                  fill: '#EF4444',
                  fontSize: 12,
                  fontWeight: 800,
                  offset: 12
                }}
              />

              {/* F1 Score Line (Fixed Threshold) */}
              <Line
                type="monotone"
                dataKey="f1_fixed_th"
                name="f1_fixed_th"
                stroke="#06B6D4"
                strokeWidth={3}
                dot={{ r: 4, fill: '#06B6D4', stroke: '#0B1120', strokeWidth: 2 }}
                activeDot={{ r: 7, fill: '#38BDF8', stroke: '#FFF', strokeWidth: 2 }}
              />

              {/* PR-AUC Line */}
              <Line
                type="monotone"
                dataKey="pr_auc"
                name="pr_auc"
                stroke="#F59E0B"
                strokeWidth={3}
                dot={{ r: 4, fill: '#F59E0B', stroke: '#0B1120', strokeWidth: 2 }}
                activeDot={{ r: 7, fill: '#FDE047', stroke: '#FFF', strokeWidth: 2 }}
              />

              {/* Optional Adaptive F1 Line */}
              {showAdaptiveF1 && (
                <Line
                  type="monotone"
                  dataKey="f1_adaptive_th"
                  name="f1_adaptive_th"
                  stroke="#A855F7"
                  strokeWidth={2.5}
                  strokeDasharray="5 5"
                  dot={{ r: 3, fill: '#A855F7' }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Informative explanation footer */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid rgba(255, 255, 255, 0.06)',
          borderRadius: '8px',
          padding: '0.85rem 1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
          fontSize: '0.75rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
            <Info size={16} color="#06B6D4" />
            <span>
              <strong>Concept Drift Finding:</strong> At timestep 43, international law enforcement seized the primary dark market hub. The static threshold model (fixed threshold = 0.5) suffered total degradation (F1 = 0.000) due to covariate shift.
            </span>
          </div>
          <div style={{ color: '#38BDF8', fontWeight: 600 }}>
            Source: Elliptic Temporal GNN Dataset
          </div>
        </div>

      </div>

    </div>
  );
}
