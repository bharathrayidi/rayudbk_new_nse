import React from 'react';

export default function Sidebar({
  activeShortcut,
  setActiveShortcut,
  setActiveMainView,
  searchQuery,
  setSearchQuery,
  filteredStocks,
  loadingStocks,
  selectedStock,
  setSelectedStock,
  watchlist,
  toggleWatchlist,
  isIndex,
  isOpen,
  setIsOpen
}) {
  
  const handleMenuClick = (shortcut, view) => {
    const isActive = activeShortcut === shortcut;
    setActiveShortcut(isActive ? 'all' : shortcut);
    setActiveMainView(isActive ? 'details' : view);
    setIsOpen?.(false);
  };

  return (
    <aside className={`fixed left-0 top-0 h-screen bg-surface-dim border-r border-surface-border flex flex-col pt-4 w-64 z-40 transition-transform duration-300 ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
      
      <div className="px-6 mb-6 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>analytics</span>
          <div>
            <h1 className="font-headline-md text-headline-md text-on-surface tracking-tight">NSE Analytics</h1>
            <p className="font-label-caps text-[10px] text-text-muted">Institutional Grade</p>
          </div>
        </div>
        <button className="lg:hidden text-text-muted hover:text-on-surface" onClick={() => setIsOpen?.(false)}>
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex flex-col gap-1 px-2 mb-6">
        <button 
          className={`px-4 py-3 flex items-center gap-3 transition-all rounded ${activeShortcut === 'all' && !['screener', 'macro', 'system_log'].includes(activeShortcut) ? 'bg-surface-container-high text-primary border-l-4 border-primary translate-x-1' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => { setActiveShortcut('all'); setActiveMainView('details'); setIsOpen?.(false); }}
        >
          <span className="material-symbols-outlined">dashboard</span>
          <span className="font-label-caps text-label-caps">Dashboard</span>
        </button>
        
        <button 
          className={`px-4 py-3 flex items-center gap-3 transition-all rounded ${activeShortcut === 'ai' ? 'bg-surface-container-high text-primary border-l-4 border-primary translate-x-1' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => handleMenuClick('ai', 'ai_table')}
        >
          <span className="material-symbols-outlined">auto_awesome</span>
          <span className="font-label-caps text-label-caps">Top AI Picks</span>
        </button>
        
        <button 
          className={`px-4 py-3 flex items-center gap-3 transition-all rounded ${activeShortcut === 'ai_perf' ? 'bg-surface-container-high text-primary border-l-4 border-primary translate-x-1' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => handleMenuClick('ai_perf', 'ai_performance')}
        >
          <span className="material-symbols-outlined">query_stats</span>
          <span className="font-label-caps text-label-caps">AI Performance</span>
        </button>
        
        <button 
          className={`px-4 py-3 flex items-center gap-3 transition-all rounded ${activeShortcut === 'gainers' ? 'bg-surface-container-high text-primary border-l-4 border-primary translate-x-1' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => handleMenuClick('gainers', 'gainers_table')}
        >
          <span className="material-symbols-outlined">trending_up</span>
          <span className="font-label-caps text-label-caps">Volume Gainers</span>
        </button>

        <button 
          className={`px-4 py-3 flex items-center gap-3 transition-all rounded ${activeShortcut === 'active' ? 'bg-surface-container-high text-primary border-l-4 border-primary translate-x-1' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => handleMenuClick('active', 'active_table')}
        >
          <span className="material-symbols-outlined">moving</span>
          <span className="font-label-caps text-label-caps">Most Active</span>
        </button>
      </nav>

      {/* Advanced Tools */}
      <div className="px-6 mb-2">
        <span className="font-label-caps text-[10px] text-text-muted uppercase tracking-wider">Advanced Tools</span>
      </div>
      <nav className="flex flex-col gap-1 px-2 mb-6 border-b border-surface-border pb-6">
        <button 
          className={`px-4 py-2 flex items-center gap-3 transition-all rounded ${activeShortcut === 'screener' ? 'text-primary bg-primary/10' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => handleMenuClick('screener', 'screener')}
        >
          <span className="material-symbols-outlined text-sm">filter_alt</span>
          <span className="font-label-caps text-xs">Master Screener</span>
        </button>
        <button 
          className={`px-4 py-2 flex items-center gap-3 transition-all rounded ${activeShortcut === 'macro' ? 'text-primary bg-primary/10' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => handleMenuClick('macro', 'macro')}
        >
          <span className="material-symbols-outlined text-sm">language</span>
          <span className="font-label-caps text-xs">Macro & FII Data</span>
        </button>
        <button 
          className={`px-4 py-2 flex items-center gap-3 transition-all rounded ${activeShortcut === 'system_log' ? 'text-primary bg-primary/10' : 'text-on-surface-variant hover:bg-surface-container'}`}
          onClick={() => handleMenuClick('system_log', 'system_log')}
        >
          <span className="material-symbols-outlined text-sm">terminal</span>
          <span className="font-label-caps text-xs">System Logs</span>
        </button>
      </nav>

      {/* Search & Stock List */}
      <div className="px-4 flex-grow flex flex-col min-h-0">
        <div className="relative mb-4">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm">search</span>
          <input
            type="text"
            className="w-full bg-surface-container border border-surface-border text-on-surface font-body-md text-sm px-9 py-2 rounded focus:border-primary outline-none transition-all placeholder:text-outline/50"
            placeholder="Search symbol..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="flex justify-between items-center mb-2 px-2">
          <span className="font-label-caps text-[10px] text-text-muted uppercase tracking-wider">
             {activeShortcut === 'gainers' ? 'Gainers' : activeShortcut === 'active' ? 'Most Active' : activeShortcut === 'ai' ? 'AI Picks' : 'Symbols'} ({filteredStocks.length})
          </span>
        </div>

        {loadingStocks ? (
          <div className="flex justify-center py-4">
            <span className="material-symbols-outlined animate-spin text-primary">sync</span>
          </div>
        ) : (
          <ul className="flex-1 overflow-y-auto overflow-x-hidden space-y-1 pr-1 custom-scrollbar pb-4">
            {filteredStocks.map(symbol => (
              <li key={symbol}>
                <button
                  className={`w-full text-left px-3 py-2 rounded flex justify-between items-center group transition-colors ${selectedStock === symbol ? 'bg-surface-container border-l-2 border-primary text-primary' : 'hover:bg-surface-subtle text-on-surface-variant'}`}
                  onClick={() => {
                    setSelectedStock(symbol);
                    setActiveMainView('details');
                    setIsOpen?.(false);
                  }}
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <span 
                      className={`material-symbols-outlined text-sm cursor-pointer ${watchlist.includes(symbol) ? 'text-tertiary' : 'text-outline hover:text-on-surface'}`}
                      style={{ fontVariationSettings: watchlist.includes(symbol) ? "'FILL' 1" : "'FILL' 0" }}
                      onClick={(e) => { e.stopPropagation(); toggleWatchlist(symbol, e); }}
                    >
                      star
                    </span>
                    <span className="font-data-tabular text-xs font-bold truncate">{symbol}</span>
                  </div>
                  {isIndex(symbol) ? (
                    <span className="text-[9px] bg-primary/10 text-primary px-1.5 py-0.5 rounded uppercase font-label-caps">Idx</span>
                  ) : (
                    <span className="material-symbols-outlined text-[14px] opacity-0 group-hover:opacity-100 transition-opacity">chevron_right</span>
                  )}
                </button>
              </li>
            ))}
            {filteredStocks.length === 0 && (
              <div className="text-center py-4">
                <span className="font-body-md text-xs text-outline">No matches found</span>
              </div>
            )}
          </ul>
        )}
      </div>
    </aside>
  );
}
