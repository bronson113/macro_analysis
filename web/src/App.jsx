import React, { useState, useEffect, useId, useRef } from 'react';
import Header from './components/Header';
import StatCard from './components/StatCard';
import NewsFeed from './components/NewsFeed';
import StockMatrix from './components/StockMatrix';
import BigUpdate from './components/BigUpdate';
import EditorialReview from './components/EditorialReview';
import TrendGraphs from './components/TrendGraphs';
import CheatSheet from './components/CheatSheet';
import RegimeOverview from './components/RegimeOverview';
import { descriptions } from './utils/descriptions';
import { buildFreshnessStatus } from './utils/dashboardPresentation';
import { buildSourceHealthView } from './utils/sourceHealthPresentation';
import { getNextTabIndex } from './utils/keyboardNavigation';

const DASHBOARD_TABS = [
  { id: 'snapshot', label: 'Snapshot' },
  { id: 'trends', label: 'Trends' },
  { id: 'research', label: 'Research' },
  { id: 'quality', label: 'Data quality' },
];

function SourceHealthSection({ records = [] }) {
  return (
    <section className="section source-health-section animate-fade-in" aria-labelledby="source-health-heading-title">
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
  const [weeklyDigests, setWeeklyDigests] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [activeView, setActiveView] = useState('snapshot');
  const dashboardTabRefs = useRef([]);
  const dashboardId = useId();

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

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'digests/index.json?t=' + new Date().getTime())
      .then(res => {
        if (!res.ok) throw new Error('Failed to load weekly digests.');
        return res.json();
      })
      .then(json => {
        setWeeklyDigests(Array.isArray(json) ? json : []);
      })
      .catch(err => {
        console.error(err);
        setWeeklyDigests([]);
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
    macro_regime: macroRegime,
    macro_situation: macroSituation,
    macro_regime_sections: macroRegimeSections,
    recent_news_events,
    individual_stock_constituents,
    source_health: sourceHealth,
  } = data || {};
  const freshness = buildFreshnessStatus({ generatedAt: metadata?.generated_at });
  const indicators = mq ? (
    <section className="section indicators-section" aria-labelledby="indicators-heading">
      <div className="section-header">
        <div>
          <p className="section-kicker">Key indicators</p>
          <h2 id="indicators-heading">Current Indicators</h2>
        </div>
      </div>
      <div className="grid grid-cols-4">
        <StatCard title="Fed Total Assets" value={mq.fed_total_assets?.value} date={mq.fed_total_assets?.date} unit="M" format="currency" description={descriptions.fed_total_assets} />
        <StatCard title="TGA Balance" value={mq.tga_balance?.value} date={mq.tga_balance?.date} unit="M" format="currency" description={descriptions.tga_balance} />
        <StatCard title="10Y Treasury Yield" value={mq.treasury_10y?.value} date={mq.treasury_10y?.date} format="percent" description={descriptions.treasury_10y} />
        <StatCard title="10Y-2Y Spread" value={mq.spread_10y_2y?.value} date={mq.spread_10y_2y?.date} format="percent" description={descriptions.spread_10y_2y} />
      </div>
    </section>
  ) : null;

  const report = (
    <BigUpdate
      reports={reports}
      weeklyDigests={weeklyDigests}
      macroRegime={macroRegime}
      macroSituation={macroSituation}
      macroRegimeSections={macroRegimeSections}
      showRegimeOverview={false}
    />
  );

  const handleDashboardTabKeyDown = (event, index) => {
    const nextIndex = getNextTabIndex({ key: event.key, currentIndex: index, tabCount: DASHBOARD_TABS.length });
    if (nextIndex === null) return;
    event.preventDefault();
    setActiveView(DASHBOARD_TABS[nextIndex].id);
    dashboardTabRefs.current[nextIndex]?.focus();
  };

  const renderDashboardPanel = tabId => {
    if (tabId === 'snapshot') {
      return (
        <div className="tab-panel-content snapshot-view">
          <section className="snapshot-status paper-panel" aria-label="Snapshot freshness">
            <div>
              <p className="section-kicker">Current evidence</p>
              <h2>Macro snapshot</h2>
            </div>
            <dl>
              <div><dt>Data feed</dt><dd className={`status-${freshness.tone}`}>{freshness.label} · {freshness.ageLabel}</dd></div>
              <div><dt>Generated</dt><dd>{freshness.generatedLabel}</dd></div>
              <div><dt>Last synced</dt><dd>{lastRefresh ? lastRefresh.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : 'Not refreshed yet'}</dd></div>
            </dl>
          </section>
          <RegimeOverview regime={macroRegime} situation={macroSituation} sections={macroRegimeSections} />
          {report}
          {indicators}
        </div>
      );
    }
    if (tabId === 'trends') return <div className="tab-panel-content"><TrendGraphs /></div>;
    if (tabId === 'research') {
      return (
        <div className="tab-panel-content research-view">
          <EditorialReview />
          <details className="supporting-disclosure paper-panel">
            <summary>News and constituent detail</summary>
            <div className="grid grid-cols-2 deep-dive-grid">
              <NewsFeed newsEvents={recent_news_events} />
              <StockMatrix stocks={individual_stock_constituents} />
            </div>
          </details>
        </div>
      );
    }
    return <div className="tab-panel-content"><SourceHealthSection records={sourceHealth || []} /></div>;
  };

  return (
    <div className="container">
      <Header
        metadata={metadata}
        reports={reports}
        weeklyDigests={weeklyDigests}
        lastRefresh={lastRefresh}
        onOpenCheatSheet={() => setIsCheatSheetOpen(true)}
      />

      <main className="dashboard-content">
        <div className="dashboard-tabs" role="tablist" aria-label="Macro dashboard views" aria-orientation="horizontal">
          {DASHBOARD_TABS.map((tab, index) => (
            <button
              key={tab.id}
              ref={element => { dashboardTabRefs.current[index] = element; }}
              className={`dashboard-tab ${activeView === tab.id ? 'active' : ''}`}
              type="button"
              role="tab"
              id={`${dashboardId}-${tab.id}-tab`}
              aria-selected={activeView === tab.id}
              aria-controls={`${dashboardId}-${tab.id}-panel`}
              tabIndex={activeView === tab.id ? 0 : -1}
              onClick={() => setActiveView(tab.id)}
              onKeyDown={event => handleDashboardTabKeyDown(event, index)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {DASHBOARD_TABS.map(tab => (
          <section key={tab.id} className="dashboard-panel" id={`${dashboardId}-${tab.id}-panel`} role="tabpanel" aria-labelledby={`${dashboardId}-${tab.id}-tab`} hidden={activeView !== tab.id} tabIndex="0">
            {activeView === tab.id ? renderDashboardPanel(tab.id) : null}
          </section>
        ))}
      </main>

      <CheatSheet isOpen={isCheatSheetOpen} onClose={() => setIsCheatSheetOpen(false)} />
    </div>
  );
}

export default App;
