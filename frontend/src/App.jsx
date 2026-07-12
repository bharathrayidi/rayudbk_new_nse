import React, { useState, useEffect, Component } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
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
  Star,
  Menu
} from 'lucide-react';
import { LineChart, Line, XAxis as RechartsXAxis, YAxis as RechartsYAxis, Tooltip as RechartsTooltip, ResponsiveContainer as RechartsContainer, BarChart, Bar, Cell } from 'recharts';
import Sidebar from './components/Sidebar';
import AdvancedScreener from './components/AdvancedScreener';
import MacroTerminal from './components/MacroTerminal';
import IngestionLog from './components/IngestionLog';

export const API_BASE = 'https://rayudbk-nse-backend.onrender.com/api';

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
  const navigate = useNavigate();
  const { logout } = useAuth();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  // AI Performance State
  const [aiPerformance, setAiPerformance] = useState([]);
  
  // History Table Sort State
  const [historySortConfig, setHistorySortConfig] = useState({ key: 'formatted_date', direction: 'desc' });
  
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
    <th className="p-4 font-label-caps text-label-caps text-text-muted border-b border-surface-border text-right cursor-pointer hover:text-on-surface transition-colors" onClick={() => handleSort(key)}>
      <div className="flex flex-col items-end gap-1">
        <span className="flex items-center gap-1">
          {label} 
          <span className="text-[10px] opacity-50">{sortConfig.key === key ? (sortConfig.direction === 'asc' ? '▲' : '▼') : '↕'}</span>
        </span>
        <input 
          type="text" 
          className="w-24 bg-surface-dim border border-surface-border text-on-surface font-body-md text-[10px] px-2 py-1 rounded focus:border-primary outline-none" 
          placeholder={`Filter...`}
          value={filters[key] || ''}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => handleFilterChange(key, e.target.value)}
        />
      </div>
    </th>
  );

  const renderSortHeaderLeft = (label, key) => (
    <th className="p-4 font-label-caps text-label-caps text-text-muted border-b border-surface-border text-left cursor-pointer hover:text-on-surface transition-colors" onClick={() => handleSort(key)}>
      <div className="flex flex-col items-start gap-1">
        <span className="flex items-center gap-1">
          {label} 
          <span className="text-[10px] opacity-50">{sortConfig.key === key ? (sortConfig.direction === 'asc' ? '▲' : '▼') : '↕'}</span>
        </span>
        <input 
          type="text" 
          className="w-24 bg-surface-dim border border-surface-border text-on-surface font-body-md text-[10px] px-2 py-1 rounded focus:border-primary outline-none" 
          placeholder={`Filter...`}
          value={filters[key] || ''}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => handleFilterChange(key, e.target.value)}
        />
      </div>
    </th>
  );

  if (backendOffline) {
    return (
      <div className="min-h-screen bg-background text-on-surface flex flex-col items-center justify-center p-8 text-center gap-6">
        <span className="material-symbols-outlined text-[64px] text-bearish opacity-70">wifi_off</span>
        <h2 className="font-headline-md text-2xl font-bold">Backend Not Running</h2>
        <p className="text-text-muted max-w-md leading-relaxed font-body-md">
          The FastAPI backend at <code className="bg-primary/10 text-primary px-2 py-0.5 rounded text-sm">{API_BASE}</code> is not reachable.
          <br /><br />
          Start it with:<br />
          <code className="text-bullish text-sm mt-2 block bg-surface-dim border border-surface-border p-2 rounded">python -m uvicorn backend.server:app --port 8000 --reload</code>
        </p>
        <button
          className="flex items-center gap-2 px-6 py-3 bg-primary-container text-on-primary-container rounded-lg font-body-md font-bold hover:brightness-110 transition-all mt-4"
          onClick={loadInitialData}
        >
          <span className="material-symbols-outlined text-sm">refresh</span>
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="bg-background text-on-surface font-body-md min-h-screen flex flex-col">
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
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />

      {/* ── MAIN CONTENT ── */}
      <main className="lg:ml-64 flex-1 flex flex-col p-4 md:p-8 h-screen overflow-y-auto overflow-x-hidden">
        
        {/* Top App Bar / System Status Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 md:p-6 bg-surface-subtle border border-surface-border rounded-xl mb-6 flex-shrink-0">
          <div className="flex items-center gap-3 flex-wrap">
            <button className="lg:hidden text-on-surface hover:text-primary flex items-center justify-center p-1" onClick={() => setIsSidebarOpen(true)}>
              <span className="material-symbols-outlined">menu</span>
            </button>
            <span className={`status-dot ${backendOffline ? 'bg-bearish' : 'bg-bullish animate-pulse'}`}></span>
            <span className="font-label-caps text-[10px] md:text-label-caps text-on-surface">Backend Status: <span className={backendOffline ? 'text-bearish' : 'text-bullish'}>{backendOffline ? 'Offline' : 'Connected'}</span></span>
            <span className="text-surface-border hidden md:inline">|</span>
            <span className="font-label-caps text-[10px] md:text-label-caps text-text-muted hidden md:inline">Endpoint:</span>
            <code className="bg-surface-container px-2 py-0.5 rounded font-data-tabular text-[10px] md:text-[11px] text-primary truncate max-w-[200px] md:max-w-none">{API_BASE}</code>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={loadInitialData}
              className="flex items-center gap-2 px-3 py-1.5 md:px-4 md:py-2 bg-primary-container text-on-primary-container rounded font-label-caps text-[10px] md:text-label-caps hover:brightness-110 active:scale-95 transition-all w-full md:w-auto justify-center"
            >
              <span className="material-symbols-outlined text-sm">refresh</span>
              Reconnect / Refresh
            </button>
            <button 
              onClick={handleLogout}
              className="flex items-center gap-2 px-3 py-1.5 md:px-4 md:py-2 bg-bearish/10 text-bearish border border-bearish/20 rounded font-label-caps text-[10px] md:text-label-caps hover:bg-bearish hover:text-on-error-container active:scale-95 transition-all w-full md:w-auto justify-center"
            >
              <span className="material-symbols-outlined text-sm">logout</span>
              Logout
            </button>
          </div>
        </header>
        {activeMainView === 'screener' ? (
          <AdvancedScreener onSelectStock={(sym) => { setSelectedStock(sym); setActiveMainView('details'); }} />
        ) : activeMainView === 'macro' ? (
          <MacroTerminal />
        ) : activeMainView === 'system_log' ? (
          <IngestionLog />
        ) : activeMainView === 'gainers_table' || activeMainView === 'active_table' || activeMainView === 'ai_table' || activeMainView === 'ai_performance' ? (
          <div className="glass-panel p-4 md:p-6 rounded-xl w-full border border-surface-border flex-1 flex flex-col min-h-0">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 md:mb-6">
              <h2 className="font-headline-md text-xl md:text-headline-md text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">
                  {activeMainView === 'ai_table' || activeMainView === 'ai_performance' ? 'psychology' : 'trending_up'}
                </span>
                {activeMainView === 'gainers_table' ? 'Top Volume Gainers' : 
                 activeMainView === 'active_table' ? 'Most Active Equities' : 
                 activeMainView === 'ai_performance' ? 'AI Predictions Evaluation' : 'Top AI Picks For Tomorrow'}
              </h2>
              <span className="bg-primary/10 text-primary px-3 py-1 rounded-full font-label-caps text-[10px] tracking-wider uppercase border border-primary/20 w-max">
                {activeMainView === 'ai_table' ? 'Machine Learning Predictions' : 
                 activeMainView === 'ai_performance' ? 'Backtesting & Tracking' : 'Market Snapshot'}
              </span>
            </div>
            <div className="overflow-x-auto flex-1 custom-scrollbar">
              <table className="w-full text-left border-collapse min-w-[800px] md:min-w-[1000px]">

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
                      <tr key={idx} onClick={() => { setSelectedStock(stock.Symbol); setActiveMainView('details'); }} className="group hover:bg-surface-container transition-colors cursor-pointer">
                        <td className="p-4 text-on-surface font-bold whitespace-nowrap border-b border-surface-border/50">{stock.Prediction_Date}</td>
                        <td className="p-4 text-on-surface font-bold whitespace-nowrap border-b border-surface-border/50">{stock.Symbol}</td>
                        <td className="p-4 text-right font-mono border-b border-surface-border/50" style={{ color: '#d946ef' }}>
                          {stock['Surge_Prob_%']}%
                        </td>
                        <td className="p-4 text-right border-b border-surface-border/50" style={{ fontSize: '12px', color: (stock['Confidence'] || '').includes('HIGH') ? '#4ade80' : '#facc15' }}>
                          {stock['Confidence']}
                        </td>
                        <td className="p-4 text-right font-mono font-bold border-b border-surface-border/50" style={{
                          color: stock['Realized_Return_%'] > 0 ? '#4ade80' : stock['Realized_Return_%'] < 0 ? '#f87171' : '#94a3b8'
                        }}>
                          {stock['Realized_Return_%'] !== null ? `${stock['Realized_Return_%'] > 0 ? '+' : ''}${stock['Realized_Return_%']}%` : 'Pending'}
                        </td>
                      </tr>
                    ))
                  ) : activeMainView === 'ai_table' ? (
                    processedData.map((stock, idx) => (
                      <tr key={idx} onClick={() => { setSelectedStock(stock.Symbol); setActiveMainView('details'); }} className="group hover:bg-surface-container transition-colors cursor-pointer">
                        <td className="p-4 text-on-surface font-bold whitespace-nowrap border-b border-surface-border/50">{stock.Symbol}</td>
                        <td className={`p-4 text-right font-mono border-b border-surface-border/50 ${stock['Latest_Return_%'] >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                          {stock['Latest_Return_%'] > 0 ? '+' : ''}{stock['Latest_Return_%']}%
                        </td>
                        <td className="p-4 text-right font-mono border-b border-surface-border/50" style={{
                          color: stock['RSI'] > 70 ? '#f87171' : stock['RSI'] < 30 ? '#4ade80' : '#e2e8f0'
                        }}>
                          {stock['RSI'] ?? '—'}
                        </td>
                        <td className="p-4 text-right font-mono border-b border-surface-border/50">{stock['Volume_Surge_x'] ?? stock['VolumeSurge'] ?? '—'}x</td>
                        <td className={`p-4 text-right font-mono border-b border-surface-border/50 ${ (stock['Corp_Ann_Sentiment'] ?? 0) > 0 ? 'text-bullish' : (stock['Corp_Ann_Sentiment'] ?? 0) < 0 ? 'text-bearish' : '' }`}>
                          {stock['Corp_Ann_Sentiment'] ?? '—'}
                        </td>
                        <td className={`p-4 text-right font-mono border-b border-surface-border/50 ${ (stock['News_Sentiment'] ?? 0) > 0 ? 'text-bullish' : (stock['News_Sentiment'] ?? 0) < 0 ? 'text-bearish' : '' }`}>
                          {stock['News_Sentiment'] ?? '—'}
                        </td>
                        <td className="p-4 text-right border-b border-surface-border/50" style={{ fontSize: '11px', color: '#94a3b8', maxWidth: '140px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {stock['Patterns_Detected'] || '—'}
                        </td>
                        <td className="p-4 text-right font-mono border-b border-surface-border/50" style={{ color: '#d946ef', fontWeight: 'bold' }}>
                          {stock['Surge_Prob_%'] ?? stock['Prediction_Surge_Prob_%']}%
                        </td>
                        <td className="p-4 text-right border-b border-surface-border/50" style={{
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
                      <tr key={idx} onClick={() => { setSelectedStock(stock.symbol); setActiveMainView('details'); }} className="group hover:bg-surface-container transition-colors cursor-pointer">
                        <td className="p-4 text-on-surface font-bold whitespace-nowrap border-b border-surface-border/50">{stock.symbol}</td>
                        <td className="p-4 text-text-muted text-sm border-b border-surface-border/50 truncate max-w-[200px]">{stock.companyName}</td>
                        <td className="p-4 text-right font-mono border-b border-surface-border/50">
                          {stock.ltp ? parseFloat(stock.ltp).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}
                        </td>
                        <td className={`p-4 text-right font-mono border-b border-surface-border/50 ${parseFloat(stock.pChange) >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                          {parseFloat(stock.pChange) > 0 ? '+' : ''}{stock.pChange}%
                        </td>
                        <td className="p-4 text-right font-mono border-b border-surface-border/50">{parseInt(stock.volume || 0).toLocaleString('en-IN')}</td>
                        {activeMainView === 'gainers_table' && (
                          <td className="p-4 text-right font-mono border-b border-surface-border/50">
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
            <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
              <div className="flex flex-col gap-1">
                <h2 className="font-headline-md text-2xl md:text-3xl text-on-surface flex items-center gap-3">
                  {selectedStock}
                  <button 
                    className={`transition-colors ${watchlist.includes(selectedStock) ? 'text-primary' : 'text-outline hover:text-primary'}`} 
                    onClick={() => toggleWatchlist(selectedStock)}
                    title={watchlist.includes(selectedStock) ? "Remove from Watchlist" : "Add to Watchlist"}
                  >
                    <Star size={24} fill={watchlist.includes(selectedStock) ? "currentColor" : "none"} />
                  </button>
                </h2>
                <div className="font-label-caps text-xs text-text-muted flex items-center gap-2">
                  {isIndex(selectedStock) ? 'NSE Stock Market Index' : 'NSE Equity Share'}
                  &bull;
                  <span>Updated: {metrics.lastUpdated}</span>
                </div>
              </div>
              <div className="flex flex-col items-start md:items-end">
                <span className="font-display-lg text-3xl md:text-4xl text-on-surface tracking-tight">
                  ₹{metrics.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className={`font-label-caps text-sm flex items-center gap-1 mt-1 ${metrics.changePercent >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                  {metrics.changePercent >= 0 ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
                  {metrics.changePercent >= 0 ? '+' : ''}{metrics.changePercent.toFixed(2)}%
                </span>
              </div>
            </header>

            {/* Metrics Grid */}
            <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-surface-subtle border border-surface-border p-4 rounded-xl flex flex-col gap-1">
                <span className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase">Traded Volume</span>
                <span className="font-data-tabular text-lg md:text-xl text-on-surface font-bold">{metrics.volume.toLocaleString('en-IN')}</span>
              </div>
              <div className="bg-surface-subtle border border-surface-border p-4 rounded-xl flex flex-col gap-1">
                <span className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase">Average Close Price</span>
                <span className="font-data-tabular text-lg md:text-xl text-on-surface font-bold">
                  ₹{metrics.averagePrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="bg-surface-subtle border border-surface-border p-4 rounded-xl flex flex-col gap-1 col-span-2">
                <span className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase">52-Week Range Indicator</span>
                <div className="w-full mt-3">
                  <div className="h-1.5 w-full bg-surface-border rounded-full relative">
                    <div className="h-full bg-primary/30 rounded-full absolute top-0 left-0" style={{ width: `${get52WeekPercentage()}%` }} />
                    <div className="w-3 h-3 bg-primary rounded-full absolute top-1/2 -translate-y-1/2 -ml-1.5 border-2 border-background" style={{ left: `${get52WeekPercentage()}%` }} />
                  </div>
                  <div className="flex justify-between font-label-caps text-[10px] text-text-muted mt-2">
                    <span>52W L: ₹{metrics.low_52week.toLocaleString('en-IN')}</span>
                    <span>52W H: ₹{metrics.high_52week.toLocaleString('en-IN')}</span>
                  </div>
                </div>
              </div>
              
              {metrics.aiSurgeProb !== undefined && metrics.aiSurgeProb !== null && (
                <>
                  <div className="bg-surface-subtle border border-surface-border border-l-4 border-l-[#d946ef] p-4 rounded-xl flex flex-col gap-1 shadow-[0_0_15px_rgba(217,70,239,0.1)]">
                    <span className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase">Surge Probability (AI v2)</span>
                    <span className="font-data-tabular text-lg md:text-xl font-bold" style={{ color: '#d946ef' }}>{metrics.aiSurgeProb}%</span>
                    {metrics.aiSignalStrength && (
                      <span className="text-[10px] font-label-caps font-bold mt-1 text-bullish">
                        Strength: {metrics.aiSignalStrength}
                      </span>
                    )}
                  </div>
                  <div className="bg-surface-subtle border border-surface-border p-4 rounded-xl flex flex-col gap-1">
                    <span className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase">Detected Patterns</span>
                    <span className="font-body-md text-sm text-on-surface leading-tight mt-1">
                      {metrics.aiPatterns || "None detected"}
                    </span>
                  </div>
                </>
              )}
            </section>

            {/* Deep-Dive Integration Grid */}
            {deepDive && (
              <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
                {/* Fundamentals */}
                {deepDive.fundamentals && (
                  <div className="bg-surface-subtle border border-surface-border p-5 rounded-xl flex flex-col gap-3">
                    <h3 className="font-headline-md text-lg text-on-surface flex items-center gap-2 mb-2 pb-2 border-b border-surface-border"><Award size={18}/> Fundamentals</h3>
                    <div className="flex justify-between items-center"><span className="font-body-md text-sm text-text-muted">P/E Ratio</span><span className="font-data-tabular text-sm text-on-surface font-medium">{deepDive.fundamentals.PE_Ratio ?? 'N/A'}</span></div>
                    <div className="flex justify-between items-center"><span className="font-body-md text-sm text-text-muted">P/B Ratio</span><span className="font-data-tabular text-sm text-on-surface font-medium">{deepDive.fundamentals.PB_Ratio ?? 'N/A'}</span></div>
                    <div className="flex justify-between items-center"><span className="font-body-md text-sm text-text-muted">ROE</span><span className="font-data-tabular text-sm text-on-surface font-medium">{deepDive.fundamentals.ROE ? `${deepDive.fundamentals.ROE}%` : 'N/A'}</span></div>
                    <div className="flex justify-between items-center"><span className="font-body-md text-sm text-text-muted">Debt to Equity</span><span className="font-data-tabular text-sm text-on-surface font-medium">{deepDive.fundamentals.Debt_to_Equity ?? 'N/A'}</span></div>
                  </div>
                )}
                
                {/* Sentiment */}
                {deepDive.sentiment && (
                  <div className="bg-surface-subtle border border-surface-border p-5 rounded-xl flex flex-col gap-3">
                    <h3 className="font-headline-md text-lg text-on-surface flex items-center gap-2 mb-2 pb-2 border-b border-surface-border"><Activity size={18}/> Real-Time Sentiment</h3>
                    <div className="flex justify-between items-center">
                      <span className="font-body-md text-sm text-text-muted">News Sentiment</span>
                      <span className={`font-data-tabular text-sm font-medium ${deepDive.sentiment.News_Sentiment > 0 ? 'text-bullish' : deepDive.sentiment.News_Sentiment < 0 ? 'text-bearish' : 'text-on-surface'}`}>
                        {deepDive.sentiment.News_Sentiment}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="font-body-md text-sm text-text-muted">Social Sentiment</span>
                      <span className={`font-data-tabular text-sm font-medium ${deepDive.sentiment.Social_Sentiment > 0 ? 'text-bullish' : deepDive.sentiment.Social_Sentiment < 0 ? 'text-bearish' : 'text-on-surface'}`}>
                        {deepDive.sentiment.Social_Sentiment}
                      </span>
                    </div>
                    <div className="flex justify-between items-center mt-2">
                      <span className="font-body-md text-xs text-text-muted">Last Updated</span>
                      <span className="font-data-tabular text-xs text-outline">{deepDive.sentiment.Date}</span>
                    </div>
                  </div>
                )}

                {/* Microstructure */}
                {deepDive.microstructure && (
                  <div className="bg-surface-subtle border border-surface-border p-5 rounded-xl flex flex-col gap-3">
                    <h3 className="font-headline-md text-lg text-on-surface flex items-center gap-2 mb-2 pb-2 border-b border-surface-border"><ChartLine size={18}/> Microstructure</h3>
                    <div className="flex justify-between items-center">
                      <span className="font-body-md text-sm text-text-muted">Bid-Ask Spread</span>
                      <span className="font-data-tabular text-sm text-on-surface font-medium">{deepDive.microstructure.Bid_Ask_Spread ?? 'N/A'}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="font-body-md text-sm text-text-muted">Order Imbalance</span>
                      <span className={`font-data-tabular text-sm font-medium ${deepDive.microstructure.Order_Book_Imbalance > 0 ? 'text-bullish' : 'text-bearish'}`}>
                        {deepDive.microstructure.Order_Book_Imbalance ?? 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="font-body-md text-sm text-text-muted">Volume Profile</span>
                      <span className="font-data-tabular text-sm text-on-surface font-medium">{deepDive.microstructure.Volume_Profile ?? 'N/A'}</span>
                    </div>
                  </div>
                )}

                {/* Recent Deals */}
                {deepDive.deals && deepDive.deals.length > 0 && (
                  <div className="bg-surface-subtle border border-surface-border p-5 rounded-xl flex flex-col gap-3 md:col-span-2 xl:col-span-3">
                    <h3 className="font-headline-md text-lg text-on-surface flex items-center gap-2 mb-2 pb-2 border-b border-surface-border"><Globe size={18}/> Recent Bulk & Block Deals</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse min-w-[600px]">
                        <thead>
                          <tr>
                            <th className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase border-b border-surface-border pb-2">Date</th>
                            <th className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase border-b border-surface-border pb-2">Client Name</th>
                            <th className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase border-b border-surface-border pb-2">Buy/Sell</th>
                            <th className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase border-b border-surface-border pb-2 text-right">Quantity</th>
                            <th className="font-label-caps text-[10px] md:text-xs text-text-muted uppercase border-b border-surface-border pb-2 text-right">Price (₹)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {deepDive.deals.map((deal, i) => (
                            <tr key={i} className="group hover:bg-surface-container transition-colors">
                              <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50">{deal.Date}</td>
                              <td className="font-body-md text-sm py-2 border-b border-surface-border/50">{deal['Client Name']}</td>
                              <td className={`font-label-caps text-xs py-2 border-b border-surface-border/50 ${deal['Buy/Sell'] === 'BUY' ? 'text-bullish' : 'text-bearish'}`}>{deal['Buy/Sell']}</td>
                              <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 text-right">{parseInt(deal.Quantity).toLocaleString('en-IN')}</td>
                              <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 text-right">{parseFloat(deal.Price).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* Tabs */}
            <nav className="flex gap-2 border-b border-surface-border mb-6 overflow-x-auto pb-1 scrollbar-hide">
              <button className={`flex items-center gap-2 px-4 py-2 font-label-caps text-xs md:text-sm transition-colors rounded-t-lg whitespace-nowrap ${activeTab === 'chart' ? 'bg-surface-subtle text-primary border-b-2 border-primary' : 'text-text-muted hover:text-on-surface hover:bg-surface-container'}`} onClick={() => setActiveTab('chart')}>
                <ChartLine size={18} /> Interactive Chart
              </button>
              <button className={`flex items-center gap-2 px-4 py-2 font-label-caps text-xs md:text-sm transition-colors rounded-t-lg whitespace-nowrap ${activeTab === 'table' ? 'bg-surface-subtle text-primary border-b-2 border-primary' : 'text-text-muted hover:text-on-surface hover:bg-surface-container'}`} onClick={() => setActiveTab('table')}>
                <FileText size={18} /> Historical Data Table
              </button>
              <button className={`flex items-center gap-2 px-4 py-2 font-label-caps text-xs md:text-sm transition-colors rounded-t-lg whitespace-nowrap ${activeTab === 'announcements' ? 'bg-surface-subtle text-primary border-b-2 border-primary' : 'text-text-muted hover:text-on-surface hover:bg-surface-container'}`} onClick={() => setActiveTab('announcements')}>
                <FileText size={18} /> Corporate Announcements ({announcements.length})
              </button>
              <button className={`flex items-center gap-2 px-4 py-2 font-label-caps text-xs md:text-sm transition-colors rounded-t-lg whitespace-nowrap ${activeTab === 'news' ? 'bg-surface-subtle text-primary border-b-2 border-primary' : 'text-text-muted hover:text-on-surface hover:bg-surface-container'}`} onClick={() => setActiveTab('news')}>
                <Newspaper size={18} /> Live News Feed
              </button>
            </nav>

            {/* Tab Panels */}
            <section className="flex-1 mb-10">
              {/* Chart Tab */}
              {activeTab === 'chart' && (
                <div className="bg-surface-subtle border border-surface-border p-5 rounded-xl h-[500px] flex flex-col">
                  <div className="flex justify-between items-center mb-4">
                    <span className="font-headline-md text-lg text-on-surface">Chronological Daily Prices</span>
                    <span className="font-label-caps text-xs text-text-muted flex gap-2 items-center">1-Year History</span>
                  </div>
                  {history.length > 0 ? (
                    <ResponsiveContainer width="100%" height="90%">
                      <AreaChart data={[...history].sort((a, b) => new Date(a.formatted_date) - new Date(b.formatted_date))} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#818cf8" stopOpacity={0.0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="formatted_date" stroke="#94a3b8" fontSize={11} tickLine={false} dy={10} />
                        <YAxis domain={['auto', 'auto']} stroke="#94a3b8" fontSize={11} tickLine={false} orientation="right" />
                        <Tooltip
                          contentStyle={{
                            background: '#1e293b',
                            borderColor: '#334155',
                            borderRadius: '8px',
                            color: '#f8fafc',
                            fontSize: '12px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                          }}
                          labelStyle={{ fontWeight: 'bold', marginBottom: '4px', color: '#94a3b8' }}
                        />
                        <Area type="monotone" dataKey="Close" stroke="#818cf8" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex flex-col items-center justify-center flex-1 text-center h-full">
                      <span className="font-headline-md text-lg text-text-muted">No Chart Data Available</span>
                    </div>
                  )}
                </div>
              )}

              {/* Data Table Tab */}
              {activeTab === 'table' && (
                <div className="bg-surface-subtle border border-surface-border p-5 rounded-xl flex flex-col h-[500px]">
                  <div className="flex justify-between items-center mb-4">
                    <span className="font-headline-md text-lg text-on-surface">Historical Daily Prices</span>
                  </div>
                  <div className="overflow-x-auto flex-1 scrollbar-thin scrollbar-thumb-surface-border scrollbar-track-transparent">
                    <table className="w-full text-left border-collapse min-w-[600px]">
                      <thead>
                        <tr>
                          {['formatted_date', 'Open', 'High', 'Low', 'Close', 'Volume'].map((key) => {
                            const labels = {
                              formatted_date: 'Date',
                              Open: 'Open',
                              High: 'High',
                              Low: 'Low',
                              Close: 'Close',
                              Volume: 'Volume'
                            };
                            return (
                              <th 
                                key={key}
                                className={`font-label-caps text-[10px] md:text-xs text-text-muted uppercase border-b border-surface-border pb-2 sticky top-0 bg-surface-subtle z-10 cursor-pointer hover:text-on-surface transition-colors ${key !== 'formatted_date' ? 'text-right' : ''}`}
                                onClick={() => {
                                  let direction = 'asc';
                                  if (historySortConfig.key === key && historySortConfig.direction === 'asc') direction = 'desc';
                                  setHistorySortConfig({ key, direction });
                                }}
                              >
                                {labels[key]} <span className="opacity-50 text-[10px] ml-1">{historySortConfig.key === key ? (historySortConfig.direction === 'asc' ? '▲' : '▼') : '↕'}</span>
                              </th>
                            );
                          })}
                        </tr>
                      </thead>
                      <tbody>
                        {[...history].sort((a, b) => {
                          const { key, direction } = historySortConfig;
                          let aVal = a[key];
                          let bVal = b[key];
                          
                          if (key === 'formatted_date') {
                            aVal = new Date(a.formatted_date).getTime();
                            bVal = new Date(b.formatted_date).getTime();
                          } else {
                            aVal = parseFloat(String(a[key] || 0).replace(/,/g, ''));
                            bVal = parseFloat(String(b[key] || 0).replace(/,/g, ''));
                          }
                          
                          if (aVal < bVal) return direction === 'asc' ? -1 : 1;
                          if (aVal > bVal) return direction === 'asc' ? 1 : -1;
                          return 0;
                        }).map((row, idx) => (
                          <tr key={idx} className="group hover:bg-surface-container transition-colors">
                            <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 font-bold">{row.formatted_date}</td>
                            <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 text-right">₹{parseFloat(String(row.Open || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 text-right text-bullish">₹{parseFloat(String(row.High || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 text-right text-bearish">₹{parseFloat(String(row.Low || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 text-right text-primary">₹{parseFloat(String(row.Close || 0).replace(/,/g, '')).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                            <td className="font-data-tabular text-sm py-2 border-b border-surface-border/50 text-right">{parseInt(String(row.Volume || 0).replace(/,/g, '')).toLocaleString('en-IN')}</td>
                          </tr>
                        ))}
                        {history.length === 0 && (
                          <tr>
                            <td colSpan="6" className="text-center p-8 text-text-muted font-body-md">
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
                <div className="flex flex-col gap-4">
                  {announcements.map((ann, idx) => (
                    <div key={idx} className="bg-surface-subtle border border-surface-border p-5 rounded-xl flex flex-col gap-2 transition-colors hover:border-surface-border-hover">
                      <div className="flex flex-col md:flex-row justify-between md:items-center gap-2 mb-1 pb-2 border-b border-surface-border/50">
                        <span className="font-headline-md text-base text-on-surface leading-snug">{ann.desc}</span>
                        <span className="font-data-tabular text-xs text-text-muted whitespace-nowrap flex items-center bg-surface-container px-2 py-1 rounded-md">
                          <Calendar size={12} className="mr-1.5 text-primary" />
                          {ann.sort_date}
                        </span>
                      </div>
                      <p className="font-body-md text-sm text-text-muted leading-relaxed whitespace-pre-wrap">{ann.desc_details}</p>
                      {ann.attachment && (
                        <a href={ann.attachment} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 font-label-caps text-xs text-primary hover:text-primary/80 mt-3 bg-primary/10 hover:bg-primary/20 px-3 py-1.5 rounded-full transition-colors w-fit border border-primary/20">
                          <Award size={14} /> View NSE Official Circular
                        </a>
                      )}
                    </div>
                  ))}
                  {announcements.length === 0 && (
                    <div className="flex flex-col items-center justify-center p-12 text-center h-[300px] bg-surface-subtle border border-surface-border rounded-xl">
                      <FileText size={48} className="text-surface-border mb-4 opacity-50" />
                      <span className="font-headline-md text-xl text-on-surface mb-2">No Announcements Logged</span>
                      <p className="font-body-md text-text-muted">Corporate announcements will appear here when fetched from the exchange.</p>
                    </div>
                  )}
                </div>
              )}

              {/* News Tab */}
              {activeTab === 'news' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {news.map((item, idx) => (
                    <a key={idx} href={item.link} target="_blank" rel="noopener noreferrer" className="bg-surface-subtle border border-surface-border p-5 rounded-xl flex flex-col justify-between gap-4 hover:border-primary/50 hover:-translate-y-1 transition-all duration-300 group shadow-sm hover:shadow-primary/5">
                      <h4 className="font-headline-md text-sm text-on-surface leading-snug group-hover:text-primary transition-colors">{item.title}</h4>
                      <div className="flex justify-between items-center font-label-caps text-[10px] text-text-muted border-t border-surface-border/50 pt-3">
                        <span className="flex items-center text-primary/80">
                          <Globe size={11} className="mr-1" />
                          {item.source}
                        </span>
                        <span>{new Date(item.pubDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                      </div>
                    </a>
                  ))}
                  {news.length === 0 && (
                    <div className="flex flex-col items-center justify-center p-12 text-center h-[300px] bg-surface-subtle border border-surface-border rounded-xl col-span-1 md:col-span-2 lg:col-span-3">
                      <Newspaper size={48} className="text-surface-border mb-4 opacity-50" />
                      <span className="font-headline-md text-xl text-on-surface mb-2">No News Available</span>
                      <p className="font-body-md text-text-muted">Could not fetch Google News feed articles at this moment.</p>
                    </div>
                  )}
                </div>
              )}
            </section>
          </>
        ) : !loadingStocks && !loadingDetails ? (
          <div className="flex flex-col items-center justify-center p-12 text-center h-[400px] mt-10">
            <ChartLine size={64} className="text-surface-border mb-4 opacity-30" />
            <span className="font-headline-md text-xl text-on-surface mb-2">Select a Stock Ticker to Begin</span>
            <p className="font-body-md text-text-muted max-w-md">Choose any stock or index symbol from the sidebar to inspect its history, charts, filings, and live news.</p>
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
