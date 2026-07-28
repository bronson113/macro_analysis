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

  return (
    <header className="dashboard-header masthead animate-fade-in stagger-1">
      <div className="masthead-brand">
        <h1 className="masthead-wordmark">MACRO / SIGNAL</h1>
        <p className="masthead-descriptor">Daily market intelligence</p>
      </div>

      <div className="masthead-utilities">
        <div className="metadata-chips" aria-label="Report metadata">
          <span className={`metadata-chip freshness-chip ${freshness.tone}`}>
            <span className="freshness-dot" aria-hidden="true"></span>
            <span>Feed</span>
            <strong>{freshness.label} · {freshness.ageLabel}</strong>
          </span>
          <span className="metadata-chip">
            <span>Report</span>
            <strong>{newestReport}</strong>
          </span>
          <span className="metadata-chip">
            <span>Archive</span>
            <strong>{reports.length ? `${reports.length} reports` : 'Unavailable'}</strong>
          </span>
          <span className="metadata-chip">
            <span>Synced</span>
            <strong>{formatRefreshTime(lastRefresh)}</strong>
          </span>
        </div>
        <button className="cheat-sheet-button" type="button" onClick={onOpenCheatSheet}>
          Macro cheat sheet
        </button>
      </div>
    </header>
  );
};

export default Header;
