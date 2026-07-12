import React, { useState, useEffect, useMemo } from 'react';
import { Filter, ChevronRight, LoaderCircle } from 'lucide-react';
import { API_BASE } from '../App';

export default function AdvancedScreener({ onSelectStock }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Sorting and Filtering
  const [sortConfig, setSortConfig] = useState({ key: 'Symbol', direction: 'asc' });
  const [filters, setFilters] = useState({});

  useEffect(() => {
    fetch(`${API_BASE}/screener`)
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Process Data
  const processedData = React.useMemo(() => {
    let filtered = data;
    // Apply filters
    Object.keys(filters).forEach(key => {
      const query = filters[key].toLowerCase();
      if (!query) return;
      filtered = filtered.filter(item => {
        const val = item[key];
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(query);
      });
    });

    // Apply sorting
    if (sortConfig.key) {
      filtered.sort((a, b) => {
        let aVal = a[sortConfig.key];
        let bVal = b[sortConfig.key];
        
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;
        
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          return sortConfig.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }
        return sortConfig.direction === 'asc' ? (aVal < bVal ? -1 : 1) : (bVal < aVal ? -1 : 1);
      });
    }
    return filtered;
  }, [data, sortConfig, filters]);

  const renderSortHeader = (label, key, align = 'right') => (
    <th className={`sortable-th ${align === 'right' ? 'text-right' : ''}`} onClick={() => handleSort(key)}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: align === 'right' ? 'flex-end' : 'flex-start' }}>
        <span style={{ fontSize: '11px', color: '#9ec2ff' }}>
          {label} {sortConfig.key === key ? (sortConfig.direction === 'asc' ? '▲' : '▼') : '↕'}
        </span>
        <input 
          type="text" 
          className="filter-input" 
          placeholder={`Filter...`}
          value={filters[key] || ''}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => handleFilterChange(key, e.target.value)}
          style={{ width: '80px', marginTop: '4px', padding: '2px 4px', fontSize: '10px' }}
        />
      </div>
    </th>
  );

  if (loading) return (
    <div className="loader-center">
      <LoaderCircle className="loader-spinner" size={48} />
      <div style={{marginTop: '16px'}}>Loading Master Screener...</div>
    </div>
  );

  return (
    <div className="data-table-container glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="chart-header" style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <span className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Filter size={20} color="#d946ef" /> Master Data Screener
        </span>
        <span className="stock-type-tag">Showing {processedData.length} of {data.length} Equities</span>
      </div>
      
      <div className="table-wrapper" style={{ flex: 1, overflow: 'auto' }}>
        <table className="nse-data-table" style={{ width: '100%', minWidth: '1200px' }}>
          <thead style={{ position: 'sticky', top: 0, background: 'var(--panel-bg)', zIndex: 10 }}>
            <tr>
              {renderSortHeader('Symbol', 'Symbol', 'left')}
              {renderSortHeader('P/E', 'PE_Ratio')}
              {renderSortHeader('ROE %', 'ROE')}
              {renderSortHeader('RSI', 'RSI')}
              {renderSortHeader('MACD', 'MACD_Histogram')}
              {renderSortHeader('BB Pos', 'BB_Position')}
              {renderSortHeader('News Sent.', 'News_Sentiment')}
              {renderSortHeader('Social Sent.', 'Social_Sentiment')}
              <th className="text-right" style={{ width: '60px' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {processedData.map((stock, idx) => (
              <tr key={idx} onClick={() => onSelectStock(stock.Symbol)} style={{ cursor: 'pointer' }}>
                <td className="symbol-cell font-bold">{stock.Symbol}</td>
                <td className="text-right font-mono">{stock.PE_Ratio ? Number(stock.PE_Ratio).toFixed(2) : '-'}</td>
                <td className="text-right font-mono" style={{ color: stock.ROE > 15 ? '#4ade80' : stock.ROE < 0 ? '#f87171' : '' }}>
                  {stock.ROE ? `${Number(stock.ROE).toFixed(2)}%` : '-'}
                </td>
                <td className="text-right font-mono" style={{ color: stock.RSI < 30 ? '#4ade80' : stock.RSI > 70 ? '#f87171' : '' }}>
                  {stock.RSI ? Number(stock.RSI).toFixed(2) : '-'}
                </td>
                <td className="text-right font-mono" style={{ color: stock.MACD_Histogram > 0 ? '#4ade80' : stock.MACD_Histogram < 0 ? '#f87171' : '' }}>
                  {stock.MACD_Histogram ? Number(stock.MACD_Histogram).toFixed(3) : '-'}
                </td>
                <td className="text-right font-mono">{stock.BB_Position || '-'}</td>
                <td className="text-right font-mono" style={{ color: stock.News_Sentiment > 0.2 ? '#4ade80' : stock.News_Sentiment < -0.2 ? '#f87171' : '' }}>
                  {stock.News_Sentiment ? Number(stock.News_Sentiment).toFixed(2) : '-'}
                </td>
                <td className="text-right font-mono" style={{ color: stock.Social_Sentiment > 0.2 ? '#4ade80' : stock.Social_Sentiment < -0.2 ? '#f87171' : '' }}>
                  {stock.Social_Sentiment ? Number(stock.Social_Sentiment).toFixed(2) : '-'}
                </td>
                <td className="text-right">
                  <ChevronRight size={16} color="var(--accent-color)" />
                </td>
              </tr>
            ))}
            {processedData.length === 0 && (
              <tr>
                <td colSpan="9" className="text-center p-8 text-secondary">No stocks match the given filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
