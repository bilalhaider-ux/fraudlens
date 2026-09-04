import React from 'react';

const TAB_MAP = {
  1: 'situation',
  2: 'graph',
  3: 'drift',
  4: 'alerts',
  'situation': 1,
  'graph': 2,
  'drift': 3,
  'alerts': 4
};

export default function Navbar({ 
  activeScreen, 
  setActiveScreen, 
  activeTab, 
  setActiveTab, 
  alertCount = 50 
}) {
  const currentScreen = activeScreen !== undefined 
    ? (typeof activeScreen === 'number' ? activeScreen : TAB_MAP[activeScreen] || 1)
    : (typeof activeTab === 'number' ? activeTab : TAB_MAP[activeTab] || 1);

  const handleSelectScreen = (id) => {
    if (typeof setActiveScreen === 'function') {
      setActiveScreen(id);
    }
    if (typeof setActiveTab === 'function') {
      setActiveTab(TAB_MAP[id] || id);
    }
  };

  const navItems = [
    { id: 1, label: '1. Situation Room', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
    { id: 2, label: '2. Investigation Graph', icon: 'M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z' },
    { id: 3, label: '3. Drift Monitor', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    { id: 4, label: '4. Alerts Queue', badge: alertCount, icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' }
  ];

  return (
    <header className="sticky top-0 z-50 w-full bg-[#080d1a]/90 backdrop-blur-md border-b border-white/10 px-3 sm:px-6 py-2.5 flex flex-col gap-2">
      {/* Top Bar: Brand & System Status */}
      <div className="flex items-center justify-between w-full min-w-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="text-sm sm:text-base font-black tracking-wider text-white">FRAUDLENS</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">ML v2.4</span>
            </div>
            <span className="text-[10px] text-slate-400 truncate hidden xs:block">
              Autonomous Anomaly &amp; Risk Defense Platform
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
          <span className="text-[10px] sm:text-xs font-semibold text-amber-300 whitespace-nowrap">
            <span className="sm:hidden">ELEVATED</span>
            <span className="hidden sm:inline">ELEVATED THREAT</span>
          </span>
        </div>
      </div>

      {/* Bottom Row: Fully Touch-Scrollable Tab Rail */}
      <nav className="w-full overflow-x-auto flex flex-nowrap items-center gap-2 py-1 scrollbar-none touch-pan-x">
        {navItems.map((item) => {
          const isActive = currentScreen === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleSelectScreen(item.id)}
              className={`shrink-0 flex items-center gap-2 px-3.5 py-2 min-h-[40px] rounded-xl text-xs sm:text-sm font-medium transition-all duration-150 cursor-pointer whitespace-nowrap ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                  : 'bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10 border border-white/5'
              }`}
            >
              <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} />
              </svg>
              <span>{item.label}</span>
              {item.badge && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-rose-500 text-white shrink-0">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
