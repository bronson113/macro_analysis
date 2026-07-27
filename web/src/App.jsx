import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import StatCard from './components/StatCard';
import NewsFeed from './components/NewsFeed';
import StockMatrix from './components/StockMatrix';
import BigUpdate from './components/BigUpdate';
import TrendGraphs from './components/TrendGraphs';
import CheatSheet from './components/CheatSheet';
import { descriptions } from './utils/descriptions';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCheatSheetOpen, setIsCheatSheetOpen] = useState(false);

  useEffect(() => {
    const loadData = () => {
      fetch(import.meta.env.BASE_URL + 'data.json?t=' + new Date().getTime())
        .then(res => {
          if (!res.ok) throw new Error('Failed to load data.json');
          return res.json();
        })
        .then(json => {
          setData(json);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setError(err.message);
          setLoading(false);
        });
    };

    loadData(); // Initial load
    const intervalId = setInterval(loadData, 30000); // Poll every 30 seconds
    return () => clearInterval(intervalId);
  }, []);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="text-secondary animate-fade-in">Loading Macro Analysis Data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="loading-container" style={{ color: 'var(--status-negative)' }}>
        <h2>Error Loading Dashboard</h2>
        <p>{error}</p>
      </div>
    );
  }

  const { metadata, macro_quantitative: mq, recent_news_events, individual_stock_constituents } = data || {};

  return (
    <div className="container" style={{ position: 'relative' }}>
      <div style={{ position: 'absolute', top: '2rem', right: '0', zIndex: 10 }}>
        <button className="link-button" onClick={() => setIsCheatSheetOpen(true)} style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem 1rem', borderRadius: '4px' }}>
          &#9432; View Macro Cheat Sheet
        </button>
      </div>
      <Header metadata={metadata} />

      {/* Primary Focus: Graphs and the Big Update */}
      <TrendGraphs />
      <BigUpdate />

      {/* Secondary Focus: Quantitative Indicators */}
      {mq && (
        <div className="section animate-fade-in stagger-4">
          <div className="section-header">
            <h2>Current Indicators</h2>
          </div>
          <div className="grid grid-cols-4">
            <StatCard title="Fed Total Assets" value={mq.fed_total_assets?.value} date={mq.fed_total_assets?.date} unit="M" format="currency" description={descriptions.fed_total_assets} />
            <StatCard title="TGA Balance" value={mq.tga_balance?.value} date={mq.tga_balance?.date} unit="M" format="currency" description={descriptions.tga_balance} />
            <StatCard title="10Y Treasury Yield" value={mq.treasury_10y?.value} date={mq.treasury_10y?.date} format="percent" description={descriptions.treasury_10y} />
            <StatCard title="10Y-2Y Spread" value={mq.spread_10y_2y?.value} date={mq.spread_10y_2y?.date} format="percent" description={descriptions.spread_10y_2y} />
          </div>
        </div>
      )}

      {/* Deep Dive Data */}
      <div className="grid grid-cols-2" style={{ gap: '3rem', marginTop: '3rem' }}>
        <NewsFeed newsEvents={recent_news_events} />
        <StockMatrix stocks={individual_stock_constituents} />
      </div>

      <CheatSheet isOpen={isCheatSheetOpen} onClose={() => setIsCheatSheetOpen(false)} />
    </div>
  );
}

export default App;
