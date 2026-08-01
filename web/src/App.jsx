import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import StatCard from './components/StatCard';
import NewsFeed from './components/NewsFeed';
import StockMatrix from './components/StockMatrix';
import BigUpdate from './components/BigUpdate';
import EditorialReview from './components/EditorialReview';
import TrendGraphs from './components/TrendGraphs';
import CheatSheet from './components/CheatSheet';
import EvidenceAssessment from './components/EvidenceAssessment';
import { descriptions } from './utils/descriptions';
import { buildFreshnessStatus, DASHBOARD_SECTIONS } from './utils/dashboardPresentation';
import { buildSourceHealthView } from './utils/sourceHealthPresentation';

function SourceHealthSection({ records = [] }) {
  return (
    <section className="section source-health-section animate-fade-in" id="source-health-heading" aria-labelledby="source-health-heading-title">
      <div className="section-header">
        <div>
          <p className="section-kicker">Data provenance</p>
          <h2 id="source-health-heading-title">Source Health</h2>
        </div>
      </div>
      <p className="source-health-intro">Latest fetch outcomes are shown as provenance signals. A stale or failed source is not treated as current evidence.</p>
      {records.length ? (
        <div className="source-health-grid">
          {records.map((record, index) => {
            const view = buildSourceHealthView(record);
            return (
              <article className="source-health-card paper-panel" key={`${record.source || 'source'}-${record.fetch_key || index}`}>
                <h3>{view.sourceLabel}</h3>
                <dl>
                  <div>
                    <dt>Status</dt>
                    <dd className={`source-health-status ${view.statusTone}`}>
                      {view.statusLabel} · {view.freshnessLabel}
                    </dd>
                  </div>
                  <div>
                    <dt>Error category</dt>
                    <dd>{view.errorLabel}</dd>
                  </div>
                  <div>
                    <dt>Message</dt>
                    <dd>{view.message}</dd>
                  </div>
                  <div>
                    <dt>Fetched</dt>
                    <dd>{view.fetchTimeLabel}</dd>
                  </div>
                </dl>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="source-health-empty paper-panel">No source-health results are available for this payload.</div>
      )}
    </section>
  );
}

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

  const {
    metadata,
    macro_quantitative: mq,
    recent_news_events,
    individual_stock_constituents,
    evidence_assessments,
    source_health: sourceHealth,
  } = data || {};
  const freshness = buildFreshnessStatus({ generatedAt: metadata?.generated_at });
  const sectionContent = {
    editorial: <EditorialReview />,
    dailyBrief: <BigUpdate reports={reports} />,
    evidence: <EvidenceAssessment assessments={evidence_assessments} />,
    trends: <TrendGraphs />,
    indicators: mq ? (
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
    ) : null,
    deepDive: (
      <div className="section" id="deep-dive-heading">
        <div className="section-header">
          <h2>Deep Dive</h2>
        </div>
        <div className="grid grid-cols-2 deep-dive-grid">
          <NewsFeed newsEvents={recent_news_events} />
          <StockMatrix stocks={individual_stock_constituents} />
        </div>
      </div>
    ),
    sourceHealth: <SourceHealthSection records={sourceHealth || []} />,
  };

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
            {DASHBOARD_SECTIONS.map(({ key, headingId, navLabel }, index) => (
              <a href={`#${headingId}`} key={key}>
                <span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>{navLabel}
              </a>
            ))}
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
          {DASHBOARD_SECTIONS.map(({ key }) => (
            <React.Fragment key={key}>{sectionContent[key]}</React.Fragment>
          ))}
        </main>
      </div>

      <CheatSheet isOpen={isCheatSheetOpen} onClose={() => setIsCheatSheetOpen(false)} />
    </div>
  );
}

export default App;
