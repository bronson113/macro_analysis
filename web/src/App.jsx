import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import StatCard from './components/StatCard';
import NewsFeed from './components/NewsFeed';
import StockMatrix from './components/StockMatrix';
import BigUpdate from './components/BigUpdate';
import LlmAnalysis from './components/LlmAnalysis';
import TrendGraphs from './components/TrendGraphs';
import CheatSheet from './components/CheatSheet';
import { descriptions } from './utils/descriptions';
import { buildFreshnessStatus } from './utils/dashboardPresentation';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCheatSheetOpen, setIsCheatSheetOpen] = useState(false);
  const [reports, setReports] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(null);

  useEffect(() => {
    const loadData = () => {
      fetch(import.meta.env.BASE_URL + 'data.json?t=' + new Date().getTime())
        .then(res => {
          if (!res.ok) throw new Error('Failed to load data.json');
          return res.json();
        })
        .then(json => {
          setData(json);
          setLastRefresh(new Date());
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

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'reports/index.json?t=' + new Date().getTime())
      .then(res => {
        if (!res.ok) throw new Error('Failed to load report history.');
        return res.json();
      })
      .then(json => {
        setReports(Array.isArray(json) ? json : []);
      })
      .catch(err => {
        console.error(err);
        setReports([]);
      });
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
  const freshness = buildFreshnessStatus({ generatedAt: metadata?.generated_at });

  return (
    <div className="container">
      <Header
        metadata={metadata}
        reports={reports}
        lastRefresh={lastRefresh}
        onOpenCheatSheet={() => setIsCheatSheetOpen(true)}
      />

      <div className="dashboard-shell">
        <aside className="section-rail">
          <nav className="dashboard-toc" aria-label="Dashboard sections">
            <a href="#llm-analysis-heading"><span aria-hidden="true">01</span>Priority</a>
            <a href="#big-update-heading"><span aria-hidden="true">02</span>Daily Brief</a>
            <a href="#trends-heading"><span aria-hidden="true">03</span>Trends</a>
            <a href="#indicators-heading"><span aria-hidden="true">04</span>Indicators</a>
            <a href="#deep-dive-heading"><span aria-hidden="true">05</span>Deep Dive</a>
          </nav>

          <section className="data-status" aria-label="Data status">
            <p className="rail-label">Data status</p>
            <dl>
              <div>
                <dt>Feed</dt>
                <dd className={`status-${freshness.tone}`}>{freshness.label} · {freshness.ageLabel}</dd>
              </div>
              <div>
                <dt>Archive</dt>
                <dd>{reports.length ? `${reports.length} reports` : 'Unavailable'}</dd>
              </div>
            </dl>
          </section>
        </aside>

        <main className="dashboard-content">
          <LlmAnalysis />

          {/* Supporting automated data and report views */}
          <TrendGraphs />
          <BigUpdate reports={reports} />

          {/* Secondary Focus: Quantitative Indicators */}
          {mq && (
            <div className="section animate-fade-in stagger-4" id="indicators-heading">
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
          <div className="section" id="deep-dive-heading">
            <div className="section-header">
              <h2>Deep Dive</h2>
            </div>
            <div className="grid grid-cols-2 deep-dive-grid">
              <NewsFeed newsEvents={recent_news_events} />
              <StockMatrix stocks={individual_stock_constituents} />
            </div>
          </div>
        </main>
      </div>

      <CheatSheet isOpen={isCheatSheetOpen} onClose={() => setIsCheatSheetOpen(false)} />
    </div>
  );
}

export default App;
