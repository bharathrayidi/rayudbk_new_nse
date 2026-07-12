import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, LoaderCircle } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, Legend, ReferenceLine } from 'recharts';
import { API_BASE } from '../App';

export default function MacroTerminal() {
  const [fiiDiiData, setFiiDiiData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/macro/fii-dii`)
      .then(res => res.json())
      .then(d => {
        // Sort ascending for chart
        setFiiDiiData(d.sort((a,b) => new Date(a.Date) - new Date(b.Date)));
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) return (
    <div className="loader-center">
      <LoaderCircle className="loader-spinner" size={48} />
      <div style={{marginTop: '16px'}}>Loading Macro Indicators...</div>
    </div>
  );

  return (
    <div className="data-table-container glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="chart-header" style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <span className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={20} color="#3b82f6" /> Smart Money Flow (FII & DII)
        </span>
        <span className="stock-type-tag">Institutional Analytics</span>
      </div>

      <div style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
        <div className="dashboard-grid">
          
          <div className="dashboard-widget glass-panel" style={{ gridColumn: 'span 3', height: '400px' }}>
            <h3 className="widget-title">FII / DII Daily Net Cash (Crores)</h3>
            {fiiDiiData.length > 0 ? (
              <ResponsiveContainer width="100%" height="90%">
                <BarChart data={fiiDiiData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="Date" stroke="var(--text-secondary)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-secondary)" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: 'rgba(20, 30, 45, 0.95)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                    labelStyle={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" />
                  <Bar dataKey="FII_Net" name="FII Net (Cr)" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="DII_Net" name="DII Net (Cr)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">No FII/DII Data Available</div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
