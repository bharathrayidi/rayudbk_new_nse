import React, { useState, useEffect } from 'react';
import { Database, CheckCircle, Clock, PlayCircle, Loader2 } from 'lucide-react';
import { API_BASE } from '../App';

export default function IngestionLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pipelineStatus, setPipelineStatus] = useState({ is_running: false, last_started: null });

  const fetchLogs = () => {
    fetch(`${API_BASE}/system/log`)
      .then(res => res.json())
      .then(d => {
        if (!d.error) setLogs(d);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  const fetchStatus = () => {
    fetch(`${API_BASE}/system/pipeline-status`)
      .then(res => res.json())
      .then(d => {
        if (!d.error) setPipelineStatus(d);
      })
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchLogs();
    fetchStatus();
    
    // Poll status and logs every 5 seconds if running
    const interval = setInterval(() => {
      fetchStatus();
      fetchLogs();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const runPipeline = () => {
    if (pipelineStatus.is_running) return;
    
    fetch(`${API_BASE}/system/run-pipeline`, { method: 'POST' })
      .then(res => res.json())
      .then(d => {
        fetchStatus();
      })
      .catch(err => console.error(err));
  };

  return (
    <div className="data-table-container glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="chart-header" style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={20} color="#10b981" /> System Ingestion Log
          </span>
          <span className="stock-type-tag">Data Pipeline Health</span>
        </div>
        
        <button 
          onClick={runPipeline}
          disabled={pipelineStatus.is_running}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            background: pipelineStatus.is_running ? 'rgba(255,255,255,0.1)' : 'rgba(16, 185, 129, 0.2)',
            color: pipelineStatus.is_running ? '#9ca3af' : '#10b981',
            border: `1px solid ${pipelineStatus.is_running ? 'rgba(255,255,255,0.1)' : '#10b981'}`,
            padding: '8px 16px', borderRadius: '6px', cursor: pipelineStatus.is_running ? 'not-allowed' : 'pointer',
            fontWeight: 600, fontSize: '13px'
          }}
        >
          {pipelineStatus.is_running ? (
            <><Loader2 size={16} className="spin-anim" /> Pipeline Running...</>
          ) : (
            <><PlayCircle size={16} /> Run Pipeline Now</>
          )}
        </button>
      </div>
      
      <div className="table-wrapper" style={{ flex: 1, padding: '24px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>Loading system logs...</div>
        ) : (
          <table className="nse-data-table">
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Ingestion Script (Job Name)</th>
                <th style={{ textAlign: 'left' }}>Last Updated Date</th>
                <th style={{ textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, idx) => (
                <tr key={idx}>
                  <td className="symbol-cell font-bold">{log.job_name}</td>
                  <td>{log.last_updated_date}</td>
                  <td style={{ textAlign: 'center', color: log.status === 'SUCCESS' ? '#4ade80' : '#f87171' }}>
                    {log.status === 'SUCCESS' ? <CheckCircle size={16} style={{ margin: '0 auto' }} /> : log.status}
                  </td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan="3" style={{ textAlign: 'center', padding: '40px' }} className="text-secondary">
                    No ingestion logs found. Run the data pipeline to generate logs.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
