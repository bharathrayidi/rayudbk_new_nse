import React from 'react';
import { ChartLine, TrendingUp, Activity, Award, ChartColumnIncreasing, Search, Star, ChevronRight, Filter, Globe, Database } from 'lucide-react';

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
  isIndex
}) {
  return (
    <aside className="sidebar glass-panel">
      <div className="brand-section">
        <ChartLine size={28} className="brand-icon" />
        <h1 className="brand-title">NSE Analytics</h1>
      </div>

      {/* Shortcut Filters */}
      <div className="shortcuts-panel">
        <div className="stock-list-title">Market Shortcuts</div>
        <button
          className={`shortcut-btn ${activeShortcut === 'gainers' ? 'active' : ''}`}
          onClick={() => {
            const isActive = activeShortcut === 'gainers';
            setActiveShortcut(isActive ? 'all' : 'gainers');
            setActiveMainView(isActive ? 'details' : 'gainers_table');
          }}
          style={{
            borderColor: activeShortcut === 'gainers' ? 'var(--success-color)' : '',
            background: activeShortcut === 'gainers' ? 'rgba(74, 222, 128, 0.15)' : ''
          }}
        >
          <TrendingUp size={16} /> Show Volume Gainers
        </button>

        <button
          className={`shortcut-btn ${activeShortcut === 'active' ? 'active' : ''}`}
          onClick={() => {
            const isActive = activeShortcut === 'active';
            setActiveShortcut(isActive ? 'all' : 'active');
            setActiveMainView(isActive ? 'details' : 'active_table');
          }}
          style={{
            borderColor: activeShortcut === 'active' ? 'var(--accent-color)' : '',
            background: activeShortcut === 'active' ? 'rgba(88, 166, 255, 0.15)' : '',
            color: activeShortcut === 'active' ? 'var(--accent-color)' : '#9ec2ff'
          }}
        >
          <Activity size={16} /> Show Most Active
        </button>

        <button
          className={`shortcut-btn ${activeShortcut === 'ai' ? 'active' : ''}`}
          onClick={() => {
            const isActive = activeShortcut === 'ai';
            setActiveShortcut(isActive ? 'all' : 'ai');
            setActiveMainView(isActive ? 'details' : 'ai_table');
          }}
          style={{
            borderColor: activeShortcut === 'ai' ? '#d946ef' : '',
            background: activeShortcut === 'ai' ? 'rgba(217, 70, 239, 0.15)' : '',
            color: activeShortcut === 'ai' ? '#d946ef' : '#e879f9',
            marginTop: '8px'
          }}
        >
          <Award size={16} /> Top AI Picks
        </button>

        <button
          className={`shortcut-btn ${activeShortcut === 'ai_perf' ? 'active' : ''}`}
          onClick={() => {
            setActiveShortcut('ai_perf');
            setActiveMainView('ai_performance');
          }}
          style={{
            borderColor: activeShortcut === 'ai_perf' ? '#22c55e' : '',
            background: activeShortcut === 'ai_perf' ? 'rgba(34, 197, 94, 0.15)' : '',
            color: activeShortcut === 'ai_perf' ? '#22c55e' : '#86efac',
            marginTop: '8px'
          }}
        >
          <ChartColumnIncreasing size={16} /> AI Performance
        </button>
        
        <div className="stock-list-title" style={{ marginTop: '24px' }}>Advanced Terminals</div>
        <button
          className={`shortcut-btn ${activeShortcut === 'screener' ? 'active' : ''}`}
          onClick={() => {
            setActiveShortcut('screener');
            setActiveMainView('screener');
          }}
          style={{
            borderColor: activeShortcut === 'screener' ? '#38bdf8' : '',
            background: activeShortcut === 'screener' ? 'rgba(56, 189, 248, 0.15)' : '',
            color: activeShortcut === 'screener' ? '#38bdf8' : '#7dd3fc',
            marginTop: '8px'
          }}
        >
          <Filter size={16} /> Master Screener
        </button>

        <button
          className={`shortcut-btn ${activeShortcut === 'macro' ? 'active' : ''}`}
          onClick={() => {
            setActiveShortcut('macro');
            setActiveMainView('macro');
          }}
          style={{
            borderColor: activeShortcut === 'macro' ? '#818cf8' : '',
            background: activeShortcut === 'macro' ? 'rgba(129, 140, 248, 0.15)' : '',
            color: activeShortcut === 'macro' ? '#818cf8' : '#a5b4fc',
            marginTop: '8px'
          }}
        >
          <Globe size={16} /> Macro & FII Data
        </button>

        <button
          className={`shortcut-btn ${activeShortcut === 'system_log' ? 'active' : ''}`}
          onClick={() => {
            setActiveShortcut('system_log');
            setActiveMainView('system_log');
          }}
          style={{
            borderColor: activeShortcut === 'system_log' ? '#10b981' : '',
            background: activeShortcut === 'system_log' ? 'rgba(16, 185, 129, 0.15)' : '',
            color: activeShortcut === 'system_log' ? '#10b981' : '#6ee7b7',
            marginTop: '8px'
          }}
        >
          <Database size={16} /> System Ingestion Log
        </button>
      </div>

      {/* Search */}
      <div className="search-box-container">
        <Search size={18} className="search-icon" />
        <input
          type="text"
          className="search-input"
          placeholder="Search stock or index..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="stock-list-title">
        {activeShortcut === 'gainers' ? 'Volume Gainers' : activeShortcut === 'active' ? 'Most Active' : activeShortcut === 'ai' ? 'Top AI Picks' : 'All Symbols'} ({filteredStocks.length})
      </div>

      {loadingStocks ? (
        <div className="loader-center">
          <div className="loader-spinner" />
        </div>
      ) : (
        <ul className="stock-list">
          {filteredStocks.map(symbol => (
            <li key={symbol}>
              <button
                className={`stock-item ${selectedStock === symbol ? 'active' : ''}`}
                onClick={() => {
                  setSelectedStock(symbol);
                  setActiveMainView('details');
                }}
              >
                <div className="stock-item-left">
                  <button 
                    className={`star-btn ${watchlist.includes(symbol) ? 'active' : ''}`} 
                    onClick={(e) => toggleWatchlist(symbol, e)}
                    title={watchlist.includes(symbol) ? "Remove from Watchlist" : "Add to Watchlist"}
                  >
                    <Star size={14} fill={watchlist.includes(symbol) ? "currentColor" : "none"} />
                  </button>
                  <span>{symbol}</span>
                </div>
                {isIndex(symbol)
                  ? <span className="badge-index">Index</span>
                  : <ChevronRight size={14} className="chevron-icon" />
                }
              </button>
            </li>
          ))}
          {filteredStocks.length === 0 && (
            <div className="empty-state">
              <span className="empty-title" style={{ fontSize: '13px' }}>No matches found</span>
            </div>
          )}
        </ul>
      )}
    </aside>
  );
}
