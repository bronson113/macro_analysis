import React from 'react';
import { buildRegimePresentation } from '../utils/dashboardPresentation';

const RegimeOverview = ({ regime, situation, sections }) => {
  const view = buildRegimePresentation({
    macro_regime: regime,
    macro_situation: situation,
    macro_regime_sections: sections,
  });

  if (!view.available) return null;

  return (
    <section className="regime-overview paper-panel" aria-labelledby="regime-overview-heading">
      <div className="regime-overview-header">
        <div>
          <p className="section-kicker">Structured regime</p>
          <h3 id="regime-overview-heading">Macro Regime Overview</h3>
        </div>
        <p className="regime-overview-note">
          Current levels determine the quadrant. Momentum, consensus, and quality are separate overlays.
        </p>
      </div>

      <div className="regime-overview-grid">
        {view.sections.map(section => (
          <article className="regime-group" key={section.key}>
            <h4>{section.label}</h4>
            <p className="regime-group-value">{section.value}</p>
            {section.summary && <p className="regime-group-summary">{section.summary}</p>}
            <dl className="regime-group-details">
              {section.details.map(item => (
                <div key={`${section.key}-${item.label}`}>
                  <dt>{item.label}</dt>
                  <dd title={item.help || undefined}>{item.value}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
};

export default RegimeOverview;
