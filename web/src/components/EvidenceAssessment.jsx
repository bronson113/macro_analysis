import React from 'react';

import { buildAssessmentView } from '../utils/evidencePresentation';

const RESEARCH_DISCLOSURE = 'Deterministic outputs are research heuristics, not trade instructions or a validated strategy. WATCH and AVOID indicate research priority only.';

function EvidenceList({ title, items, emptyLabel }) {
  return (
    <section className="evidence-list">
      <h4>{title}</h4>
      <ul>
        {items.length ? items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>) : <li>{emptyLabel}</li>}
      </ul>
    </section>
  );
}

const EvidenceAssessment = ({ assessments = [] }) => {
  if (!assessments.length) return null;

  return (
    <section className="section evidence-assessment-section animate-fade-in stagger-3" id="evidence-heading" aria-labelledby="evidence-heading-title">
      <div className="section-header">
        <div>
          <p className="section-kicker">Research evidence</p>
          <h2 id="evidence-heading-title">Evidence Assessments</h2>
        </div>
      </div>
      <p className="evidence-intro">Postures summarize the available deterministic evidence and explicitly identify what remains unobserved.</p>
      <div className="evidence-card-grid">
        {assessments.map((assessment, index) => {
          const view = buildAssessmentView(assessment);
          const coverage = Number(assessment.coverage_pct);
          const coverageValue = Number.isFinite(coverage) ? Math.min(100, Math.max(0, coverage)) : 0;

          return (
            <article className="evidence-card paper-panel" key={assessment.sector_group || `assessment-${index}`}>
              <header className="evidence-card-header">
                <div>
                  <p className="evidence-card-label">Sector / supply-chain group</p>
                  <h3>{assessment.sector_group || 'Unspecified sector'}</h3>
                </div>
                <span className={`evidence-posture ${view.tone}`}>{assessment.posture || 'NEUTRAL'}</span>
              </header>
              <dl className="evidence-metrics">
                <div>
                  <dt>Score range</dt>
                  <dd>{view.rangeLabel}</dd>
                </div>
                <div>
                  <dt>Coverage</dt>
                  <dd>{view.coverageLabel}</dd>
                </div>
              </dl>
              <meter className="evidence-coverage-meter" min="0" max="100" value={coverageValue} aria-label={`${assessment.sector_group || 'Sector'} evidence coverage`}>
                {view.coverageLabel}
              </meter>
              <div className="evidence-lists">
                <EvidenceList title="Positive evidence" items={view.positives} emptyLabel="No positive factors were recorded." />
                <EvidenceList title="Negative evidence" items={view.negatives} emptyLabel="No negative factors were recorded." />
                <EvidenceList title="Missing evidence" items={view.missing} emptyLabel="No missing-evidence reasons were recorded." />
              </div>
              <p className="research-disclosure">{RESEARCH_DISCLOSURE}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
};

export default EvidenceAssessment;
