import React from 'react';
import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="bg-surface text-on-surface flex flex-col min-h-screen font-body-md overflow-x-hidden">
      {/* TopNavBar */}
      <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop h-16 bg-surface/80 backdrop-blur-md border-b border-surface-border">
        <div className="flex items-center gap-4 md:gap-8">
          <span className="font-display-lg text-2xl md:text-display-lg font-bold text-on-surface tracking-tighter">NSE Analytics</span>
          <div className="hidden md:flex gap-6 items-center">
            <a className="text-primary font-bold border-b-2 border-primary pb-1 font-body-md transition-colors duration-200" href="#">Platform</a>
            <a className="text-on-surface-variant hover:text-primary transition-colors duration-200 font-body-md" href="#">AI Picks</a>
            <a className="text-on-surface-variant hover:text-primary transition-colors duration-200 font-body-md" href="#">Sentiment</a>
            <a className="text-on-surface-variant hover:text-primary transition-colors duration-200 font-body-md" href="#">Pricing</a>
          </div>
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          <Link to="/login" className="text-on-surface hover:text-primary transition-colors duration-200 font-body-md text-sm md:text-base px-2">Log In</Link>
          <Link to="/login" className="bg-primary text-on-primary px-3 py-1.5 md:px-4 md:py-2 rounded font-body-md font-bold glow-primary hover:opacity-80 transition-all text-sm md:text-base">Sign Up</Link>
        </div>
      </nav>

      <main className="pt-16 flex-grow">
        {/* Hero Section */}
        <section className="relative min-h-[70vh] md:min-h-[870px] flex items-center justify-center px-margin-mobile md:px-margin-desktop overflow-hidden py-12 md:py-0">
          <div className="relative z-10 text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/10 text-primary mb-6 md:mb-8 mx-auto">
              <span className="material-symbols-outlined text-[16px]">bolt</span>
              <span className="font-label-caps text-label-caps uppercase tracking-widest">Alpha v4.2 Now Live</span>
            </div>
            <h1 className="font-display-lg text-4xl md:text-[64px] leading-tight mb-4 md:mb-6 text-on-surface">Institutional Grade Intelligence for the Modern Trader</h1>
            <p className="text-text-muted text-base md:text-xl mb-8 md:mb-10 max-w-2xl mx-auto px-4">Leverage deep-learning algorithms and real-time sentiment analysis to anticipate market shifts with surgical precision.</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 px-4">
              <Link to="/login" className="w-full sm:w-auto bg-primary text-on-primary px-6 md:px-8 py-3 md:py-4 rounded-lg font-headline-md text-xl md:text-headline-md flex items-center justify-center gap-2 glow-primary transition-transform hover:scale-[1.02]">
                Get Started
                <span className="material-symbols-outlined">arrow_forward</span>
              </Link>
              <Link to="/app" className="w-full sm:w-auto border border-surface-border bg-surface-subtle/50 text-on-surface px-6 md:px-8 py-3 md:py-4 rounded-lg font-headline-md text-xl md:text-headline-md hover:bg-surface-container transition-colors text-center">
                View Live Feed
              </Link>
            </div>
          </div>
        </section>

        {/* Connectivity/Status Section */}
        <section className="py-8 md:py-12 border-y border-surface-border bg-surface-dim">
          <div className="max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-6 md:gap-8">
            <div className="flex items-center gap-4">
              <div className="w-2 h-2 rounded-full bg-bullish glow-primary animate-pulse"></div>
              <span className="font-label-caps text-label-caps text-on-surface">Data Engine: Live</span>
            </div>
            <div className="flex flex-wrap justify-center items-center gap-6 md:gap-8">
              <div className="flex flex-col items-center md:items-start">
                <span className="font-label-caps text-label-caps text-text-muted">LATENCY</span>
                <span className="font-data-tabular text-on-surface">14ms</span>
              </div>
              <div className="flex flex-col items-center md:items-start">
                <span className="font-label-caps text-label-caps text-text-muted">ACCURACY</span>
                <span className="font-data-tabular text-on-surface">91.4%</span>
              </div>
              <div className="flex flex-col items-center md:items-start">
                <span className="font-label-caps text-label-caps text-text-muted">UPTIME</span>
                <span className="font-data-tabular text-on-surface">99.99%</span>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="w-full py-8 px-margin-mobile md:px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-6 md:gap-4 bg-surface-dim border-t border-surface-border text-center md:text-left">
        <div className="flex flex-col items-center md:items-start gap-2">
          <span className="font-headline-md text-headline-md text-primary">NSE Analytics</span>
          <p className="font-label-caps text-label-caps text-text-muted">© 2024 NSE Analytics. Institutional Grade Intelligence.</p>
        </div>
        <div className="flex flex-wrap justify-center gap-4 md:gap-6 items-center">
          <a className="text-text-muted hover:text-secondary transition-colors font-label-caps text-label-caps" href="#">Terms of Service</a>
          <a className="text-text-muted hover:text-secondary transition-colors font-label-caps text-label-caps" href="#">Privacy Policy</a>
          <a className="text-text-muted hover:text-secondary transition-colors font-label-caps text-label-caps" href="#">API Documentation</a>
        </div>
      </footer>
    </div>
  );
}
