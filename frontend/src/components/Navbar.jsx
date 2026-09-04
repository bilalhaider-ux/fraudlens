import React from 'react';
import { 
  ShieldAlert, 
  Network, 
  BarChart3, 
  AlertTriangle, 
  Play, 
  Pause, 
  Radio 
} from 'lucide-react';

export default function Navbar({ 
  activeTab, 
  setActiveTab, 
  wsConnected, 
  isStreaming, 
  toggleStreaming, 
  streamSpeed, 
  setStreamSpeed,
  threatLevel,
  alertCount
}) {
  const navItems = [
    { id: 'situation', label: '1. Situation Room', icon: ShieldAlert },
    { id: 'graph', label: '2. Investigation Graph', icon: Network },
    { id: 'drift', label: '3. Drift Monitor', icon: BarChart3 },
    { id: 'alerts', label: '4. Alerts Queue', icon: AlertTriangle, badge: alertCount ? String(alertCount) : '50' },
  ];

  const getThreatBadge = (level) => {
    switch (level) {
      case 'CRITICAL':
        return { bg: 'rgba(239, 68, 68, 0.2)', text: '#EF4444', border: '#EF4444', label: 'DEFCON 1 - CRITICAL' };
      case 'ELEVATED':
        return { bg: 'rgba(245, 158, 11, 0.2)', text: '#F59E0B', border: '#F59E0B', label: 'ELEVATED THREAT' };
      default:
        return { bg: 'rgba(16, 185, 129, 0.2)', text: '#10B981', border: '#10B981', label: 'NOMINAL DEFENSE' };
    }
  };

  const threat = getThreatBadge(threatLevel);

  return (
    <header className="py-2.5 md:py-3.5 px-4 sm:px-6 lg:px-8 sticky top-0 z-[100] w-full border-b border-white/10 bg-[#0a0e17]/92 backdrop-blur-xl">
      <div className="w-full max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-3 min-h-[3.25rem]">
        
        {/* Brand & Perimeter Status */}
        <div className="flex items-center justify-between md:justify-start gap-3 shrink-0 min-w-0">
          <div className="flex items-center gap-3">
            <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-indigo-500/20 border border-cyan-500/40 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.25)] shrink-0">
              <ShieldAlert size={22} className="text-cyan-400" />
              <div 
                className={`absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-red-500 shadow-[0_0_8px_#ef4444]'}`} 
              />
            </div>
            
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base sm:text-lg tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                  FRAUD<span className="text-cyan-400">LENS</span>
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 uppercase tracking-wider">
                  ML v2.4
                </span>
              </div>
              <p className="text-[11px] text-slate-400 truncate max-w-[220px] sm:max-w-none">
                Autonomous Anomaly & Risk Defense Platform
              </p>
            </div>
          </div>

          {/* Mobile Threat Indicator */}
          <div className="md:hidden flex items-center gap-1.5 px-2 py-1 rounded-full text-[11px] font-bold" style={{ background: threat.bg, color: threat.text, border: `1px solid ${threat.border}` }}>
            <div className="w-1.5 h-1.5 rounded-full pulse-dot" style={{ background: threat.text }} />
            <span className="truncate">{threat.label.split(' - ')[0]}</span>
          </div>
        </div>

        {/* Navigation Tabs — Horizontal scroll on mobile */}
        <nav className="flex overflow-x-auto flex-nowrap shrink-0 no-scrollbar whitespace-nowrap gap-1.5 sm:gap-2 pb-1 md:pb-0 min-w-0">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 rounded-lg font-medium cursor-pointer transition-all duration-150 shrink-0 text-xs px-2.5 py-1.5 md:text-sm md:px-3.5 md:py-2 whitespace-nowrap ${
                  isActive
                    ? 'border border-cyan-500/50 bg-cyan-500/15 text-cyan-400 font-bold shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                    : 'border border-transparent bg-transparent text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'
                }`}
              >
                <Icon size={15} className={isActive ? 'text-cyan-400' : 'text-slate-400'} />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-red-500 text-white shadow-[0_0_8px_rgba(239,68,68,0.5)]">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Live Controls & Telemetry */}
        <div className="hidden md:flex items-center gap-3 shrink-0">
          {/* Threat Indicator */}
          <div 
            className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold" 
            style={{ background: threat.bg, border: `1px solid ${threat.border}`, color: threat.text }}
          >
            <div className="w-1.5 h-1.5 rounded-full pulse-dot" style={{ background: threat.text }} />
            <span>{threat.label}</span>
          </div>

          {/* Stream Controller */}
          <div className="flex items-center gap-1.5 bg-white/[0.04] p-1 rounded-lg border border-white/10">
            <button
              onClick={toggleStreaming}
              title={isStreaming ? "Pause Live Feed" : "Resume Live Feed"}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold cursor-pointer transition-all ${
                isStreaming 
                  ? 'bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30' 
                  : 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30'
              }`}
            >
              {isStreaming ? <Pause size={12} /> : <Play size={12} />}
              <span>{isStreaming ? 'STREAMING' : 'PAUSED'}</span>
            </button>

            {/* Speed Selector */}
            <select
              value={streamSpeed}
              onChange={(e) => setStreamSpeed(Number(e.target.value))}
              className="bg-transparent border-none text-slate-300 text-xs font-semibold cursor-pointer outline-none px-1"
            >
              <option value={3.0} className="bg-slate-900 text-white">0.5x</option>
              <option value={2.0} className="bg-slate-900 text-white">1.0x</option>
              <option value={1.0} className="bg-slate-900 text-white">2.0x</option>
              <option value={0.4} className="bg-slate-900 text-white">5.0x</option>
            </select>
          </div>

          {/* Socket status */}
          <div className={`flex items-center gap-1 text-xs font-semibold ${wsConnected ? 'text-emerald-400' : 'text-red-400'}`}>
            <Radio size={13} className={wsConnected ? "pulse-dot" : ""} />
            <span>{wsConnected ? "LIVE WS" : "OFFLINE"}</span>
          </div>
        </div>

      </div>
    </header>
  );
}
