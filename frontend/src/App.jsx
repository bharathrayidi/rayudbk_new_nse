import React, { useState, useEffect, Component } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Search,
  FileText,
  Newspaper,
  ChevronRight,
  ChartLine,
  Calendar,
  ArrowUpRight,
  Activity,
  Award,
  Globe,
  WifiOff,
  RotateCcw,
  ChartColumnIncreasing,
  LoaderCircle,
  Star
} from 'lucide-react';
import { LineChart, Line, XAxis as RechartsXAxis, YAxis as RechartsYAxis, Tooltip as RechartsTooltip, ResponsiveContainer as RechartsContainer, BarChart, Bar, Cell } from 'recharts';
import Sidebar from './components/Sidebar';
import AdvancedScreener from './components/AdvancedScreener';
import MacroTerminal from './components/MacroTerminal';
import IngestionLog from './components/IngestionLog';

export const API_BASE = 'https://ominous-system-4wwqp4g5xqjfxpx-8000.app.github.dev';

// ─── Error Boundary ────────────────────────────────────────────────────────────
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.error('App crashed:', error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100vh', gap: '16px',
          background: '#080c10', color: '#f0f6fc', fontFamily: 'Outfit, sans-serif', textAlign: 'center', padding: '32px'
        }}>
          <ChartColumnIncreasing size={56} style={{ color: '#f87171', opacity: 0.7 }} />
          <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#f87171' }}>Dashboard Render Error</h2>
          <p style={{ color: '#8b949e', maxWidth: '480px' }}>{this.state.error?.message || 'An unexpected error occurred.'}</p>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
            style={{
              padding: '10px 24px', borderRadius: '8px', background: '#58a6ff', border: 'none',
              color: '#fff', fontWeight: 600, cursor: 'pointer', fontSize: '14px'
            }}
          >
            Reload Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── Custom Hook for Sorting and Filtering ─────────────────────────────────────
function useSortableTable(data) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [filters, setFilters] = useState({});

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const processedData = React.useMemo(() => {
    let sortableItems = [...(data || [])];
    
    // Apply Filters
    Object.keys(filters).forEach(key => {
      const filterValue = filters[key].toLowerCase();
      if (!filterValue) return;
      sortableItems = sortableItems.filter(item => {
        const itemValue = item[key];
        if (itemValue === null || itemValue === undefined) return false;
        return String(itemValue).toLowerCase().includes(filterValue);
      });
    });

    // Apply Sorting
    if (sortConfig.key !== null) {
      sortableItems.sort((a, b) => {
        let aVal = a[sortConfig.key];
        let bVal = b[sortConfig.key];
        
        // Handle numeric parsing
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          const numA = parseFloat(aVal.replace(/,/g, ''));
          const numB = parseFloat(bVal.replace(/,/g, ''));
          if (!isNaN(numA) && !isNaN(numB)) {
            aVal = numA;
            bVal = numB;
          }
        }
        
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;
        
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableItems;
  }, [data, sortConfig, filters]);

  return { processedData, handleSort, sortConfig, handleFilterChange, filters };
}

// ─── Main App ────────────────────────────────────────────────────────────────
function App() {
  // Navigation & list states
  const [stocksList, setStocksList] = useState([]);
  const [filteredStocks, setFilteredStocks] = useState([]);
  const [volumeGainers, setVolumeGainers] = useState([]);
  const [mostActive, setMostActive] = useState([]);
  const [aiPicks, setAiPicks] = useState([]);
  const [selectedStock, setSelectedStock] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeShortcut, setActiveShortcut] = useState('ai');
  const [activeMainView, setActiveMainView] = useState('ai_table'); // 'details' | 'gainers_table' | 'active_table' | 'ai_table' | 'ai_performance'
  
  // AI Performance State
  const [aiPerformance, setAiPerformance] = useState([]);
  
  // Watchlist state (persisted)
  const [watchlist, setWatchlist] = useState(() => {
    const saved = localStorage.getItem('nse_watchlist');
    return saved ? JSON.parse(saved) : [];
  });
  
  const toggleWatchlist = (symbol, e) => {
    if (e) e.stopPropagation();
    setWatchlist(prev => {
      const newList = prev.includes(symbol) ? prev.filter(s => s !== symbol) : [...prev, symbol];
      localStorage.setItem('nse_watchlist', JSON.stringify(newList));
      return newList;
    });
  };

  // Market overview state
  const [marketOverview, setMarketOverview] = useState(null);

  // Tab control
  const [activeTab, setActiveTab] = useState('chart');

  // Data detail states
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [news, setNews] = useState([]);
  const [deepDive, setDeepDive] = useState(null);

  // Loading & error states
  const [loadingStocks, setLoadingStocks] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [backendOffline, setBackendOffline] = useState(false);

  // ── 1. Initial load ──────────────────────────────────────────────────────────
  useEffect(() => {
    loadInitialData();
  }, []);

  async function loadInitialData() {
    try {
      setLoadingStocks(true);
      setBackendOffline(false);

      const resStocks = await fetch(`${API_BASE}/stocks`);
      if (!resStocks.ok) throw new Error(`Server responded ${resStocks.status}`);
      const stocks = await resStocks.json();

      setStocksList(stocks);
      setFilteredStocks(stocks);
      if (stocks.length > 0) setSelectedStock(stocks[0]);

      // Load shortcuts silently — don't crash if these fail
      try {
        const [resGainers, resActive, resAi, resMarket] = await Promise.all([
          fetch(`${API_BASE}/volume-gainers`),
          fetch(`${API_BASE}/most-active`),
          fetch(`${API_BASE}/ai-picks`),
          fetch(`${API_BASE}/market/overview`)
        ]);
        if (resGainers.ok) setVolumeGainers(await resGainers.json());
        if (resActive.ok)  setMostActive(await resActive.json());
        if (resAi.ok) setAiPicks(await resAi.json());
        if (resMarket.ok) setMarketOverview(await resMarket.json());

        const resPerf = await fetch(`${API_BASE}/ai-performance`);
        if (resPerf.ok) setAiPerformance(await resPerf.json());
      } catch (_) { /* silent */ }

    } catch (err) {
      console.error('Backend unavailable:', err);
      setBackendOffline(true);
    } finally {
      setLoadingStocks(false);
    }
  }

  // ── 2. Filter stocks ─────────────────────────────────────────────────────────
  useEffect(() => {
    let result = stocksList;
    if (activeShortcut === 'gainers') {
      const gainerSymbols = volumeGainers.map(g => g.symbol);
      result = result.filter(s => gainerSymbols.includes(s));
    }
    else if (activeShortcut === 'active') {
      const activeSymbols = mostActive.map(g => g.symbol);
      result = result.filter(s => activeSymbols.includes(s));
    }
    else if (activeShortcut === 'ai') {
      const aiSymbols = aiPicks.map(a => a.Symbol);
      result = result.filter(s => aiSymbols.includes(s));
    }
    
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(s => s.toLowerCase().includes(q));
    }
    setFilteredStocks(result);
  }, [searchQuery, activeShortcut, stocksList, volumeGainers, mostActive, aiPicks]);

  // ── 3. Load stock details ────────────────────────────────────────────────────
  useEffect(() => {
    if (!selectedStock) return;
    async function loadStockDetails() {
      setLoadingDetails(true);
      setErrorMsg('');
      try {
        const [resMetrics, resHistory, resAnnouncements, resNews, resDeepDive] = await Promise.all([
          fetch(`${API_BASE}/stock/${selectedStock}/metrics`),
          fetch(`${API_BASE}/stock/${selectedStock}/history`),
          fetch(`${API_BASE}/stock/${selectedStock}/announcements`),
          fetch(`${API_BASE}/stock/${selectedStock}/news`),
          fetch(`${API_BASE}/stock/${selectedStock}/deep-dive`)
        ]);
        if (!resMetrics.ok || !resHistory.ok) {
          throw new Error(`Failed to load data for ${selectedStock}`);
        }
        setMetrics(await resMetrics.json());
        setHistory(await resHistory.json());
        setAnnouncements(resAnnouncements.ok ? await resAnnouncements.json() : []);
        setNews(resNews.ok ? await resNews.json() : []);
        setDeepDive(resDeepDive.ok ? await resDeepDive.json() : null);
      } catch (err) {
        console.error('Error fetching details:', err);
        setErrorMsg(err.message);
        setMetrics(null);
        setDeepDive(null);
      } finally {
        setLoadingDetails(false);
      }
    }
    loadStockDetails();
  }, [selectedStock]);

  const isIndex = s => ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'].includes(s);

  const get52WeekPercentage = () => {
    if (!metrics) return 0;
    const { ltp, high_52week, low_52week } = metrics;
    const range = high_52week - low_52week;
    if (range <= 0) return 50;
    return Math.max(0, Math.min(100, ((ltp - low_52week) / range) * 100));
  };

  // ── Main Layout ──────────────────────────────────────────────────────────────

  const getTableData = () => {
    if (activeMainView === 'ai_performance') return aiPerformance;
    if (activeMainView === 'ai_table') return aiPicks;
    if (activeMainView === 'gainers_table') return volumeGainers;
    return mostActive;
  };
  
  const { processedData, handleSort, sortConfig, handleFilterChange, filters } = useSortableTable(getTableData());

  const renderSortHeader = (label, key) => (
    <th className="sortable-th text-right" onClick={() => handleSort(key)}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
        <span>{label} {sortConfig.key === key ? (sortConfig.direction === 'asc' ? '▲' : '▼') : '↕'}</span>
        <input 
          type="text" 
          className="filter-input" 
          placeholder={`Filter ${label}...`}
          value={filters[key] || ''}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => handleFilterChange(key, e.target.value)}
        />
      </div>
    </th>
  );

  const renderSortHeaderLeft = (label, key) => (
    <th className="sortable-th" onClick={() => handleSort(key)}>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span>{label} {sortConfig.key === key ? (sortConfig.direction === 'asc' ? '▲' : '▼') : '↕'}</span>
        <input 
          type="text" 
          className="filter-input" 
          placeholder={`Filter ${label}...`}
          value={filters[key] || ''}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => handleFilterChange(key, e.target.value)}
        />
      </div>
    </th>
  );

  if (backendOffline) {
    return (
      <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '24px', padding: '48px', textAlign: 'center' }}>
        <WifiOff size={64} style={{ color: '#f87171', opacity: 0.7 }} />
        <h2 style={{ fontSize: '24px', fontWeight: 700 }}>Backend Not Running</h2>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '480px', lineHeight: 1.6 }}>
          The FastAPI backend at <code style={{ color: 'var(--accent-color)', background: 'rgba(88,166,255,0.1)', padding: '2px 6px', borderRadius: '4px' }}>{API_BASE}</code> is not reachable.
          <br /><br />
          Start it with:<br />
          <code style={{ color: '#4ade80', fontSize: '13px' }}>python -m uvicorn backend.server:app --port 8000 --reload</code>
        </p>
        <button
          className="shortcut-btn"
          onClick={loadInitialData}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 28px', fontSize: '14px', width: 'auto' }}
        >
          <RotateCcw size={16} /> Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* ── SIDEBAR ── */}
      {/* ── SIDEBAR ── */}
      <Sidebar
        activeShortcut={activeShortcut}
        setActiveShortcut={setActiveShortcut}
        setActiveMainView={setActiveMainView}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        filteredStocks={filteredStocks}
        loadingStocks={loadingStocks}
        selectedStock={selectedStock}
        setSelectedStock={setSelectedStock}
        watchlist={watchlist}
        toggleWatchlist={toggleWatchlist}
        isIndex={isIndex}
      />

      {/* ── MAIN CONTENT ── */}
      <main className="main-content">
        {activeMainView === 'screener' ? (
          <AdvancedScreener onSelectStock={(sym) => { setSelectedStock(sym); setActiveMainView('details'); }} />
        ) : activeMainView === 'macro' ? (
          <MacroTerminal />
        ) : activeMainView === 'system_log' ? (
          <IngestionLog />
        ) : activeMainView === 'gainers_table' || activeMainView === 'active_table' || activeMainView === 'ai_table' || activeMainView === 'ai_performance' ? (
          <div className="data-table-container glass-panel">
            <div className="chart-header">
              <span className="chart-title">
                {activeMainView === 'gainers_table' ? 'Top Volume Gainers' : 
                 activeMainView === 'active_table' ? 'Most Active Equities' : 
                 activeMainView === 'ai_performance' ? 'AI Predictions Evaluation' : 'Top AI Picks For Tomorrow'}
              </span>
              <span className="stock-type-tag">
                {activeMainView === 'ai_table' ? 'Machine Learning Predictions' : 
                 activeMainView === 'ai_performance' ? 'Backtesting & Tracking' : 'Market Snapshot'}
              </span>
            </div>
            <div className="table-wrapper">
              <table className="nse-data-table">

                <thead>
                  {activeMainView === 'ai_performance' ? (
                    <tr>
                      {renderSortHeaderLeft('Date', 'Prediction_Date')}
                      {renderSortHeaderLeft('Symbol', 'Symbol')}
                      {renderSortHeader('Pred. Surge Prob', 'Surge_Prob_%')}
                      {renderSortHeader('Confidence', 'Confidence')}
                      {renderSortHeader('Actual Realized Return', 'Realized_Return_%')}
                    </tr>
                  ) : activeMainView === 'ai_table' ? (
                    <tr>
                      {renderSortHeaderLeft('Symbol', 'Symbol')}
                      {renderSortHeader('Return %', 'Latest_Return_%')}
                      {renderSortHeader('RSI', 'RSI')}
                      {renderSortHeader('Vol Surge', 'Volume_Surge_x')}
                      {renderSortHeader('Corp Ann', 'Corp_Ann_Sentiment')}
                      {renderSortHeader('News Sent.', 'News_Sentiment')}
                      {renderSortHeader('Patterns', 'Patterns_Detected')}
                      {renderSortHeader('Surge Prob %', 'Surge_Prob_%')}
                      {renderSortHeader('Confidence', 'Confidence')}
                    </tr>
                  ) : (
                    <tr>
                      {renderSortHeaderLeft('Symbol', 'symbol')}
                      {renderSortHeaderLeft('Company Name', 'companyName')}
                      {renderSortHeader('LTP (₹)', 'ltp')}
                      {renderSortHeader('Change', 'pChange')}
                      {renderSortHeader('Volume', 'volume')}
                      {activeMainView === 'gainers_table' && renderSortHeader('Turnover', 'turnover')}
                    </tr>
                  )}
                </thead>
                <tbody>
                  {activeMainView === 'ai_performance' ? (
                    processedData.map((stock, idx) => (
                      <tr key={idx} onClick={() => { setSelectedStock(stock.Symbol); setActiveMainView('details'); }}>
                        <td className="symbol-cell font-bold">{stock.Prediction_Date}</td>
                        <td className="symbol-cell font-bold">{stock.Symbol}</td>
                        <td className="text-right font-mono" style={{ color: '#d946ef' }}>
                          {stock['Surge_Prob_%']}%
                        </td>
                        <td className="text-right" style={{ fontSize: '12px', color: (stock['Confidence'] || '').includes('HIGH') ? '#4ade80' : '#facc15' }}>
                          {stock['Confidence']}
                        </td>
                        <td className="text-right font-mono font-bold" style={{
                          color: stock['Realized_Return_%'] > 0 ? '#4ade80' : stock['Realized_Return_%'] < 0 ? '#f87171' : '#94a3b8'
                        }}>
                          {stock['Realized_Return_%'] !== null ? `${stock['Realized_Return_%'] > 0 ? '+' : ''}${stock['Realized_Return_%']}%` : 'Pending'}
                        </td>
                      </tr>
                    ))
                  ) : activeMainView === 'ai_table' ? (
                    processedData.map((stock, idx) => (
                      <tr key={idx} onClick={() => { setSelectedStock(stock.Symbol); setActiveMainView('details'); }}>
                        <td className="symbol-cell font-bold">{stock.Symbol}</td>
                        <td className={`text-right font-mono ${stock['Latest_Return_%'] >= 0 ? 'positive' : 'negative'}`}>
                          {stock['Latest_Return_%'] > 0 ? '+' : ''}{stock['Latest_Return_%']}%
                        </td>
                        <td className="text-right font-mono" style={{
                          color: stock['RSI'] > 70 ? '#f87171' : stock['RSI'] < 30 ? '#4ade80' : '#e2e8f0'
                        }}>
                          {stock['RSI'] ?? '—'}
                        </td>
                        <td className="text-right font-mono">{stock['Volume_Surge_x'] ?? stock['VolumeSurge'] ?? '—'}x</td>
                        <td className={`text-right font-mono ${ (stock['Corp_Ann_Sentiment'] ?? 0) > 0 ? 'positive' : (stock['Corp_Ann_Sentiment'] ?? 0) < 0 ? 'negative' : '' }`}>
                          {stock['Corp_Ann_Sentiment'] ?? '—'}
                        </td>
                        <td className={`text-right font-mono ${ (stock['News_Sentiment'] ?? 0) > 0 ? 'positive' : (stock['News_Sentiment'] ?? 0) < 0 ? 'negative' : '' }`}>
                          {stock['News_Sentiment'] ?? '—'}
                        </td>
                        <td className="text-right" style={{ fontSize: '11px', color: '#94a3b8', maxWidth: '140px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {stock['Patterns_Detected'] || '—'}
                        </td>
                        <td className="text-right font-mono" style={{ color: '#d946ef', fontWeight: 'bold' }}>
                          {stock['Surge_Prob_%'] ?? stock['Prediction_Surge_Prob_%']}%
                        </td>
                        <td className="text-right" style={{
                          fontWeight: 600, fontSize: '12px',
                          color: (stock['Confidence'] || '').includes('HIGH') ? '#4ade80'
                               : (stock['Confidence'] || '').includes('MEDIUM') ? '#facc15' : '#94a3b8'
                        }}>
                          {stock['Confidence'] || '—'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    processedData.map((stock, idx) => (
                      <tr key={idx} onClick={() => { setSelectedStock(stock.symbol); setActiveMainView('details'); }}>
                        <td className="symbol-cell font-bold">{stock.symbol}</td>
                        <td className="company-cell">{stock.companyName}</td>
                        <td className="text-right font-mono">
                          {stock.ltp ? parseFloat(stock.ltp).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}
                        </td>
                        <td className={`text-right font-mono ${parseFloat(stock.pChange) >= 0 ? 'positive' : 'negative'}`}>
                          {parseFloat(stock.pChange) > 0 ? '+' : ''}{stock.pChange}%
                        </td>
                        <td className="text-right font-mono">{parseInt(stock.volume || 0).toLocaleString('en-IN')}</td>
                        {activeMainView === 'gainers_table' && (
                          <td className="text-right font-mono">
                            {stock.turnover ? parseFloat(stock.turnover).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                  {processedData.length === 0 && (
                    <tr>
                      <td colSpan="9" className="text-center p-8 text-secondary">
                        {activeMainView === 'ai_table' && aiPicks.length === 0 
                          ? "No AI predictions available. Run scheduler.py first." 
                          : "No matching data found."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : loadingDetails && !metrics ? (
          <div className="loader-center">
            <div className="loader-spinner" />
          </div>
        ) : errorMsg ? (
          <div className="empty-state">
            <ArrowUpRight size={48} className="empty-icon" />
            <span className="empty-title">Error Loading Stock Data</span>
            <p>{errorMsg}</p>
          </div>
        ) : metrics ? (
          <>
            {/* Stock Header */}
            <header className="stock-header">
              <div className="stock-title-section">
                <h2 className="stock-name-header" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {selectedStock}
                  <button 
                    className={`star-btn ${watchlist.includes(selectedStock) ? 'active' : ''}`} 
                    onClick={() => toggleWatchlist(selectedStock)}
                    title={watchlist.includes(selectedStock) ? "Remove from Watchlist" : "Add to Watchlist"}
                    style={{ transform: 'scale(1.2)' }}
                  >
                    <Star size={18} fill={watchlist.includes(selectedStock) ? "currentColor" : "none"} />
                  </button>
                </h2>
                <div className="stock-type-tag">
                  {isIndex(selectedStock) ? 'NSE Stock Market Index' : 'NSE Equity Share'}
                  &bull;
                  <span>Updated: {metrics.lastUpdated}</span>
                </div>
              </div>
              <div className="price-summary">
                <span className="price-val">
                  ₹{metrics.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className={`price-change ${metrics.changePercent >= 0 ? 'positive' : 'negative'}`}>
                  {metrics.changePercent >= 0 ? <TrendingUp size={20} /> : <TrendingDown size={20} />}
                  {metrics.changePercent >= 0 ? '+' : ''}{metrics.changePercent.toFixed(2)}%
                </span>
              </div>
            </header>

            {/* Metrics Grid */}
            <section className="metrics-grid">
              <div className="metric-card glass-panel">
                <span className="metric-label">Traded Volume</span>
                <span className="metric-value">{metrics.volume.toLocaleString('en-IN')}</span>
              </div>
              <div className="metric-card glass-panel">
                <span className="metric-label">Average Close Price</span>
                <span className="metric-value">
                  ₹{metrics.averagePrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="metric-card glass-panel" style={{ gridColumn: 'span 2' }}>
                <span className="metric-label">52-Week Range Indicator</span>
                <div className="fifty-two-week-slider">
                  <div className="fifty-two-week-track">
                    <div className="fifty-two-week-fill" style={{ width: `${get52WeekPercentage()}%` }} />
                    <div className="fifty-two-week-pointer" style={{ left: `${get52WeekPercentage()}%` }} />
                  </div>
                  <div className="fifty-two-week-labels">
                    <span>52W L: ₹{metrics.low_52week.toLocaleString('en-IN')}</span>
                    <span>52W H: ₹{metrics.high_52week.toLocaleString('en-IN')}</span>
                  </div>
                </div>
              </div>
              
              {metrics.aiSurgeProb !== undefined && metrics.aiSurgeProb !== null && (
                <>
                  <div className="metric-card glass-panel ai-highlight" style={{ borderLeft: '4px solid #d946ef' }}>
                    <span className="metric-label">Surge Probability (AI v2)</span>
                    <span className="metric-value" style={{ color: '#d946ef' }}>{metrics.aiSurgeProb}%</span>
                    {metrics.aiSignalStrength && (
                      <span style={{ fontSize: '12px', marginTop: '4px', opacity: 0.8, color: '#facc15' }}>
                        Strength: {metrics.aiSignalStrength}
                      </span>
                    )}
                  </div>
                  <div className="metric-card glass-panel">
                    <span className="metric-label">Detected Patterns</span>
                    <span className="metric-value" style={{ fontSize: '14px', lineHeight: '1.4' }}>
                      {metrics.aiPatterns || "None detected"}
                    </span>
                  </div>
                </>
              )}
            </section>

            {/* Deep-Dive Integration Grid */}
            {deepDive && (
              <section className="deep-dive-grid">
                {/* Fundamentals */}
                {deepDive.fundamentals && (
                  <div className="deep-dive-card glass-panel">
                    <h3 className="deep-dive-title"><Award size={16}/> Fundamentals</h3>
                    <div className="deep-dive-row"><span className="dd-label">P/E Ratio</span><span className="dd-value">{deepDive.fundamentals.PE_Ratio ?? 'N/A'}</span></div>
                    <div className="deep-dive-row"><span className="dd-label">P/B Ratio</span><span className="dd-value">{deepDive.fundamentals.PB_Ratio ?? 'N/A'}</span></div>
                    <div className="deep-dive-row"><span className="dd-label">ROE</span><span className="dd-value">{deepDive.fundamentals.ROE ? `${deepDive.fundamentals.ROE}%` : 'N/A'}</span></div>
                    <div className="deep-dive-row"><span className="dd-label">Debt to Equity</span><span className="dd-value">{deepDive.fundamentals.Debt_to_Equity ?? 'N/A'}</span></div>
                  </div>
                )}
                
                {/* Sentiment */}
                {deepDive.sentiment && (
                  <div className="deep-dive-card glass-panel">
                    <h3 className="deep-dive-title"><Activity size={16}/> Real-Time Sentiment</h3>
                    <div className="deep-dive-row">
                      <span className="dd-label">News Sentiment</span>
                      <span className={`dd-value ${deepDive.sentiment.News_Sentiment > 0 ? 'positive' : deepDive.sentiment.News_Sentiment < 0 ? 'negative' : ''}`}>
                        {deepDive.sentiment.News_Sentiment}
                      </span>
                    </div>
                    <div className="deep-dive-row">
                      <span className="dd-label">Social Sentiment</span>
                      <span className={`dd-value ${deepDive.sentiment.Social_Sentiment > 0 ? 'positive' : deepDive.sentiment.Social_Sentiment < 0 ? 'negative' : ''}`}>
                        {deepDive.sentiment.Social_Sentiment}
                      </span>
                    </div>
                    <div className="deep-dive-row">
                      <span className="dd-label">Last Updated</span>
                      <span className="dd-value" style={{fontSize:'12px', color:'#8b949e'}}>{deepDive.sentiment.Date}</span>
                    </div>
                  </div>
                )}

                {/* Microstructure */}
                {deepDive.microstructure && (
                  <div className="deep-dive-card glass-panel">
                    <h3 className="deep-dive-title"><ChartLine size={16}/> Microstructure</h3>
                    <div className="deep-dive-row">
                      <span className="dd-label">Bid-Ask Spread</span>
                      <span className="dd-value">{deepDive.microstructure.Bid_Ask_Spread ?? 'N/A'}</span>
                    </div>
                    <div className="deep-dive-row">
                      <span className="dd-label">Order Imbalance</span>
                      <span className={`dd-value ${deepDive.microstructure.Order_Book_Imbalance > 0 ? 'positive' : 'negative'}`}>
                        {deepDive.microstructure.Order_Book_Imbalance ?? 'N/A'}
                      </span>
                    </div>
                    <div className="deep-dive-row">
                      <span className="dd-label">Volume Profile</span>
                      <span className="dd-value">{deepDive.microstructure.Volume_Profile ?? 'N/A'}</span>
                    </div>
                  </div>
                )}

                {/* Recent Deals */}
                {deepDive.deals && deepDive.deals.length > 0 && (
                  <div className="deep-dive-card glass-panel" style={{ gridColumn: '1 / -1' }}>
                    <h3 className="deep-dive-title"><Globe size={16}/> Recent Bulk & Block Deals</h3>
                    <table className="deals-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Client Name</th>
                          <th>Buy/Sell</th>
                          <th style={{textAlign:'right'}}>Quantity</th>
                          <th style={{textAlign:'right'}}>Price (₹)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {deepDive.deals.map((deal, i) => (
                          <tr key={i}>
                            <td>{deal.Date}</td>
                            <td>{deal['Client Name']}</td>
                            <td className={deal['Buy/Sell'] === 'BUY' ? 'positive' : 'negative'}>{deal['Buy/Sell']}</td>
                            <td style={{textAlign:'right'}}>{parseInt(deal.Quantity).toLocaleString('en-IN')}</td>
                            <td style={{textAlign:'right'}}>{parseFloat(deal.Price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            )}

            {/* Tabs */}
            <nav className="tabs-navigation">
              <button className={`tab-btn ${activeTab === 'chart' ? 'active' : ''}`} onClick={() => setActiveTab('chart')}>
                <ChartLine size={18} /> Interactive Chart
              </button>
              <button className={`tab-btn ${activeTab === 'table' ? 'active' : ''}`} onClick={() => setActiveTab('table')}>
                <FileText size={18} /> Historical Data Table
              </button>
              <button className={`tab-btn ${activeTab === 'announcements' ? 'active' : ''}`} onClick={() => setActiveTab('announcements')}>
                <FileText size={18} /> Corporate Announcements ({announcements.length})
              </button>
              <button className={`tab-btn ${activeTab === 'news' ? 'active' : ''}`} onClick={() => setActiveTab('news')}>
                <Newspaper size={18} /> Live News Feed
              </button>
            </nav>

            {/* Tab Panels */}
            <section style={{ flex: 1 }}>
              {/* Chart Tab */}
              {activeTab === 'chart' && (
                <div className="chart-panel glass-panel">
                  <div className="chart-header">
                    <span className="chart-title">Chronological Daily Prices</span>
                    <span className="stock-type-tag">1-Year History</span>
                  </div>
                  {history.length > 0 ? (
                    <ResponsiveContainer width="100%" height="90%">
                      <AreaChart data={[...history].sort((a, b) => new Date(a.formatted_date) - new Date(b.formatted_date))} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--accent-color)" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="var(--accent-color)" stopOpacity={0.0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="formatted_date" stroke="var(--text-secondary)" fontSize={11} tickLine={false} dy={10} />
                        <YAxis domain={['auto', 'auto']} stroke="var(--text-secondary)" fontSize={11} tickLine={false} orientation="right" />
                        <Tooltip
                          contentStyle={{
                            background: 'rgba(20, 30, 45, 0.95)',
                            borderColor: 'var(--accent-color)',
                            borderRadius: '10px',
                            color: '#fff',
                            fontSize: '12px'
                          }}
                          labelStyle={{ fontWeight: 'bold', marginBottom: '4px' }}
                        />
                        <Area type="monotone" dataKey="Close" stroke="var(--accent-color)" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="empty-state">
                      <span className="empty-title">No Chart Data Available</span>
                    </div>
                  )}
                </div>
              )}

              {/* Data Table Tab */}
              {activeTab === 'table' && (
                <div className="data-table-container glass-panel" style={{ height: '500px' }}>
                  <div className="chart-header">
                    <span className="chart-title">Historical Daily Prices</span>
                  </div>
                  <div className="table-wrapper">
                    <table className="nse-data-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th className="text-right">Open</th>
                          <th className="text-right">High</th>
                          <th className="text-right">Low</th>
                          <th className="text-right">Close</th>
                          <th className="text-right">Volume</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...history].sort((a, b) => new Date(b.formatted_date) - new Date(a.formatted_date)).map((row, idx) => (
                          <tr key={idx}>
                            <td className="font-bold">{row.formatted_date}</td>
                            <td className="text-right font-mono">₹{parseFloat(String(row.Open || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="text-right font-mono" style={{ color: 'var(--success-color)' }}>₹{parseFloat(String(row.High || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="text-right font-mono" style={{ color: 'var(--danger-color)' }}>₹{parseFloat(String(row.Low || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="text-right font-mono">₹{parseFloat(String(row.Close || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="text-right font-mono">{parseInt(String(row.Volume || 0).replace(/,/g, '')).toLocaleString('en-IN')}</td>
                          </tr>
                        ))}
                        {history.length === 0 && (
                          <tr>
                            <td colSpan="6" className="text-center p-8 text-secondary">
                              No historical data available.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Announcements Tab */}
              {activeTab === 'announcements' && (
                <div className="announcements-container">
                  {announcements.map((ann, idx) => (
                    <div key={idx} className="announcement-card glass-panel">
                      <div className="announcement-header">
                        <span className="announcement-title">{ann.desc}</span>
                        <span className="announcement-date">
                          <Calendar size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                          {ann.sort_date}
                        </span>
                      </div>
                      <p className="announcement-details">{ann.desc_details}</p>
                      {ann.attachment && (
                        <a href={ann.attachment} target="_blank" rel="noopener noreferrer" className="attachment-btn">
                          <Award size={14} /> View NSE Official Circular
                        </a>
                      )}
                    </div>
                  ))}
                  {announcements.length === 0 && (
                    <div className="empty-state glass-panel">
                      <FileText size={48} className="empty-icon" />
                      <span className="empty-title">No Announcements Logged</span>
                      <p>Corporate announcements will appear here when fetched from the exchange.</p>
                    </div>
                  )}
                </div>
              )}

              {/* News Tab */}
              {activeTab === 'news' && (
                <div className="news-grid">
                  {news.map((item, idx) => (
                    <a key={idx} href={item.link} target="_blank" rel="noopener noreferrer" className="news-card glass-panel">
                      <h4 className="news-headline">{item.title}</h4>
                      <div className="news-meta">
                        <span className="news-source">
                          <Globe size={11} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                          {item.source}
                        </span>
                        <span>{new Date(item.pubDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                      </div>
                    </a>
                  ))}
                  {news.length === 0 && (
                    <div className="empty-state glass-panel" style={{ gridColumn: 'span 3' }}>
                      <Newspaper size={48} className="empty-icon" />
                      <span className="empty-title">No News Available</span>
                      <p>Could not fetch Google News feed articles at this moment.</p>
                    </div>
                  )}
                </div>
              )}
            </section>
          </>
        ) : !loadingStocks && !loadingDetails ? (
          <div className="empty-state">
            <ChartLine size={64} className="empty-icon" style={{ opacity: 0.3 }} />
            <span className="empty-title">Select a Stock Ticker to Begin</span>
            <p>Choose any stock or index symbol from the sidebar to inspect its history, charts, filings, and live news.</p>
          </div>
        ) : null}
      </main>
    </div>
  );
}

// ── Wrapped export with ErrorBoundary ────────────────────────────────────────
export default function AppWithBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
