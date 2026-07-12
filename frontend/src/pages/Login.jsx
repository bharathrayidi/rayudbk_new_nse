import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    
    try {
      const endpoint = '/api/auth/login';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }
      
      // Save token and authenticate
      login(data.access_token);
      navigate('/app');
      
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface text-on-surface flex flex-col min-h-screen overflow-x-hidden font-body-md">
      <main className="flex-grow flex items-center justify-center relative overflow-hidden px-4 md:px-margin-mobile py-12">
        {/* Atmospheric Background Element */}
        <div className="absolute inset-0 pointer-events-none opacity-20 overflow-hidden">
          <div className="absolute -top-1/2 -left-1/4 w-[150%] h-[150%] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent"></div>
        </div>

        {/* Login Card */}
        <div className="tonal-layer w-full max-w-[400px] p-6 md:p-10 rounded-xl shadow-2xl relative z-10 glow-hover transition-shadow duration-500">
          
          {/* Brand Logo Area */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 bg-primary rounded flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-on-primary text-3xl">query_stats</span>
            </div>
            <h1 className="font-display-lg text-2xl md:text-headline-md tracking-tighter text-on-surface text-center">NSE Analytics</h1>
            <p className="font-body-md text-text-muted mt-2 text-center text-sm md:text-base">Institutional Grade Intelligence</p>
          </div>

          {errorMsg && (
            <div className="bg-bearish/20 border border-bearish text-bearish text-sm p-3 rounded mb-6 text-center font-body-md">
              {errorMsg}
            </div>
          )}

          <form className="space-y-6" onSubmit={handleLogin}>
            {/* Username Field */}
            <div className="space-y-2">
              <label className="font-label-caps text-label-caps text-on-surface-variant uppercase" htmlFor="username">Username</label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-lg">person</span>
                <input 
                  id="username"
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-surface-container-lowest border border-surface-border text-on-surface font-body-md text-sm md:text-body-md px-10 py-3 rounded outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all placeholder:text-outline/50" 
                  placeholder="Admin Username" 
                  required 
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <div className="flex justify-between items-end">
                <label className="font-label-caps text-label-caps text-on-surface-variant uppercase" htmlFor="password">Password</label>
                <a href="#" className="font-label-caps text-label-caps text-primary hover:text-secondary transition-colors">Forgot Password?</a>
              </div>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-lg">lock</span>
                <input 
                  id="password"
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-surface-container-lowest border border-surface-border text-on-surface font-body-md text-sm md:text-body-md px-10 py-3 rounded outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all placeholder:text-outline/50" 
                  placeholder="••••••••••••" 
                  required 
                />
              </div>
            </div>

            {/* Submit Button */}
            <button disabled={loading} type="submit" className={`w-full bg-primary text-on-primary py-3 rounded font-body-md font-bold text-sm md:text-base transition-all mt-4 ${loading ? 'opacity-50' : 'glow-primary hover:opacity-80'}`}>
              {loading ? 'Authenticating...' : 'Secure Sign In'}
              {!loading && <span className="material-symbols-outlined text-sm ml-2 align-middle">arrow_forward</span>}
            </button>
          </form>

          <div className="mt-8 text-center border-t border-surface-border pt-6">
            <p className="font-body-md text-sm text-text-muted">
              Restricted Access. Admins Only.
            </p>
          </div>
        </div>
      </main>

      <footer className="w-full py-6 px-margin-mobile md:px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-4 bg-surface-dim border-t border-surface-border text-center md:text-left z-10">
        <div className="flex items-center gap-2">
          <span className="font-headline-md text-base text-primary">NSE Analytics</span>
          <span className="text-text-muted hidden md:inline">|</span>
          <p className="font-label-caps text-[10px] text-text-muted">© 2024 Institutional Trade Intelligence.</p>
        </div>
        <div className="flex gap-4 items-center flex-wrap justify-center">
          <a className="text-text-muted hover:text-secondary transition-colors font-label-caps text-[10px]" href="#">Terms of Service</a>
          <a className="text-text-muted hover:text-secondary transition-colors font-label-caps text-[10px]" href="#">Privacy Policy</a>
          <a className="text-text-muted hover:text-secondary transition-colors font-label-caps text-[10px]" href="#">Contact Support</a>
        </div>
      </footer>
    </div>
  );
}
