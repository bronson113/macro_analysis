import React from 'react';
import { buildFreshnessStatus } from '../utils/dashboardPresentation';

const formatRefreshTime = (lastRefresh) => {
  if (!lastRefresh) return 'Not refreshed yet';

  return new Intl.DateTimeFormat(undefined, {
    timeStyle: 'short',
  }).format(lastRefresh);
};

const Header = ({ metadata, reports = [], lastRefresh, onOpenCheatSheet }) => {
  const freshness = buildFreshnessStatus({ generatedAt: metadata?.generated_at });
  const newestReport = reports[0]?.date || metadata?.date || 'Unavailable';
  const oldestReport = reports[reports.length - 1]?.date || 'Unavailable';

  return (
    <header className="dashboard-header animate-fade-in stagger-1">
      <div>
        <h1 className="gradient-text">Macro Analysis Dashboard</h1>
        <p className="text-secondary">AI-driven financial insights & quantitative macro data.</p>
      </div>
      <div className="header-utilities">
        <button className="cheat-sheet-button" type="button" onClick={onOpenCheatSheet}>
          &#9432; View Macro Cheat Sheet
        </button>
        <div className={`freshness-panel ${freshness.tone}`} aria-label="Data freshness">
          <div className="freshness-status-row">
            <span className="freshness-dot" aria-hidden="true"></span>
            <strong>{freshness.label}</strong>
            <span>{freshness.ageLabel}</span>
          </div>
          <dl className="freshness-details">
            <div>
              <dt>Generated</dt>
              <dd>{freshness.generatedLabel}</dd>
            </div>
            <div>
              <dt>Report</dt>
              <dd>{newestReport}</dd>
            </div>
            <div>
              <dt>Archive</dt>
              <dd>{oldestReport} to {newestReport}</dd>
            </div>
            <div>
              <dt>Browser</dt>
              <dd>{formatRefreshTime(lastRefresh)}</dd>
            </div>
          </dl>
        </div>
      </div>
    </header>
  );
};

export default Header;
