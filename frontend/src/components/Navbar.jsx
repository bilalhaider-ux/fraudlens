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

  const isCritical = threatLevel === 'CRITICAL';
  const isNominal = threatLevel === 'NOMINAL';

  const badgeStyle = isCritical
    ? { container: 'bg-red-500/10 border-red-500/30 text-red-300', dot: 'bg-red-400 animate-ping', shortText: 'CRITICAL', fullText: 'DEFCON 1 - CRITICAL' }
    : isNominal
      ? { container: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300', dot: 'bg-emerald-400', shortText: 'NOMINAL', fullText: 'NOMINAL DEFENSE' }
      : { container: 'bg-amber-500/10 border-amber-500/30 text-amber-300', dot: 'bg-amber-400 animate-ping', shortText: 'ELEVATED', fullText: 'ELEVATED THREAT' };

  return (
    <header className="py-2.5 px-4 sm:px-6 lg:px-8 sticky top-0 z-[100] w-full border-b border-white/10 bg-[#0a0e17]/95 backdrop-blur-xl">
      <div className="w-full max-w-7xl mx-auto flex flex-col gap-2.5">
        
        {/* Top Row: Brand & System Status */}
        <div className="flex items-center justify-between w-full pb-2 border-b border-white/5">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 shrink-0">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm sm:text-base font-black tracking-wider text-white truncate">FRAUDLENS</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">ML v2.4</span>
              </div>
              <p className="text-[10px] sm:text-xs text-slate-400 truncate hidden xs:block">
                Autonomous Anomaly &amp; Risk Defense Platform
              </p>
            </div>
          </div>

          {/* Status Badge: Mobile compact dot, Desktop full text */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border shrink-0 ${badgeStyle.container}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${badgeStyle.dot}`}></span>
            <span className="text-[10px] sm:text-xs font-semibold whitespace-nowrap">
              <span className="sm:hidden">{badgeStyle.shortText}</span>
              <span className="hidden sm:inline">{badgeStyle.fullText}</span>
            </span>
          </div>
        </div>

        {/* Bottom Row: Navigation Tabs & Telemetry Controls */}
        <div className="flex items-center justify-between w-full gap-3 min-w-0">
          
          {/* Navigation Tabs — Horizontal scroll on mobile */}
          <nav className="flex overflow-x-auto flex-nowrap shrink-0 no-scrollbar whitespace-nowrap gap-1.5 sm:gap-2 pb-0.5 min-w-0">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 rounded-lg font-medium cursor-pointer transition-all duration-150 shrink-0 text-xs px-2.5 py-1.5 md:text-sm md:px-3.5 md:py-1.5 whitespace-nowrap ${
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

      </div>
    </header>
  );
}
