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
    { id: 'alerts', label: '4. Alerts Queue', icon: AlertTriangle, badge: '50' },
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
    <header 
      className="py-2 md:py-4 px-4 sticky top-0 z-[100]"
      style={{
        background: 'rgba(10, 14, 23, 0.92)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
      }}
    >
      <div className="navbar-container">
        {/* Logo & Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            position: 'relative',
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(6, 182, 212, 0.25)'
          }}>
            <ShieldAlert size={24} color="#06B6D4" />
            <div style={{
              position: 'absolute',
              top: '-2px',
              right: '-2px',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: wsConnected ? '#10B981' : '#EF4444',
              boxShadow: wsConnected ? '0 0 8px #10B981' : '0 0 8px #EF4444'
            }} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ 
                fontWeight: 800, 
                fontSize: '1.25rem', 
                letterSpacing: '-0.02em',
                background: 'linear-gradient(to right, #FFFFFF, #94A3B8)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                FRAUD<span style={{ color: '#06B6D4', WebkitTextFillColor: '#06B6D4' }}>LENS</span>
              </span>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'rgba(99, 102, 241, 0.2)',
                color: '#818CF8',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                letterSpacing: '0.05em'
              }}>
                ML v2.4
              </span>
            </div>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', letterSpacing: '0.01em' }}>
              Autonomous Anomaly & Risk Defense Platform
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex overflow-x-auto flex-nowrap shrink-0 no-scrollbar whitespace-nowrap gap-2 pb-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 rounded-lg font-medium cursor-pointer transition-all duration-150 shrink-0 text-xs px-2.5 py-1.5 md:text-sm md:px-4 md:py-2 ${
                  isActive
                    ? 'border border-cyan-500/45 bg-cyan-500/15 text-[#38BDF8] font-bold'
                    : 'border border-transparent bg-transparent text-slate-400 hover:text-slate-200'
                }`}
                style={{
                  whiteSpace: 'nowrap',
                  position: 'relative'
                }}
              >
                <Icon size={16} color={isActive ? '#38BDF8' : '#94A3B8'} />
                <span>{item.label}</span>
                {item.badge && (
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '10px',
                    background: '#EF4444',
                    color: '#FFF',
                    boxShadow: '0 0 8px rgba(239, 68, 68, 0.5)'
                  }}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Live Controls & Telemetry */}
        <div className="navbar-telemetry">
          {/* Threat Indicator */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: '20px',
            background: threat.bg,
            border: `1px solid ${threat.border}`,
            fontSize: '0.72rem',
            fontWeight: 700,
            color: threat.text
          }}>
            <div style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: threat.text,
              boxShadow: `0 0 6px ${threat.text}`
            }} className="pulse-dot" />
            <span>{threat.label}</span>
          </div>

          {/* Stream Controller */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '0.25rem 0.4rem',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <button
              onClick={toggleStreaming}
              title={isStreaming ? "Pause Live Feed" : "Resume Live Feed"}
              style={{
                background: isStreaming ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                border: `1px solid ${isStreaming ? '#EF4444' : '#10B981'}`,
                color: isStreaming ? '#EF4444' : '#10B981',
                padding: '0.35rem 0.55rem',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                fontSize: '0.75rem',
                fontWeight: 600
              }}
            >
              {isStreaming ? <Pause size={13} /> : <Play size={13} />}
              <span>{isStreaming ? 'STREAMING' : 'PAUSED'}</span>
            </button>

            {/* Speed selector */}
            <select
              value={streamSpeed}
              onChange={(e) => setStreamSpeed(Number(e.target.value))}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                outline: 'none',
                padding: '0.2rem 0.4rem'
              }}
            >
              <option value={3.0} style={{ background: '#111827', color: '#FFF' }}>0.5x Slow</option>
              <option value={2.0} style={{ background: '#111827', color: '#FFF' }}>1.0x Normal</option>
              <option value={1.0} style={{ background: '#111827', color: '#FFF' }}>2.0x Fast</option>
              <option value={0.4} style={{ background: '#111827', color: '#FFF' }}>5.0x Turbo</option>
            </select>
          </div>

          {/* Socket status */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            fontSize: '0.75rem',
            color: wsConnected ? '#10B981' : '#EF4444'
          }}>
            <Radio size={14} className={wsConnected ? "pulse-dot" : ""} />
            <span style={{ fontWeight: 600 }}>{wsConnected ? "LIVE WS" : "OFFLINE"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
