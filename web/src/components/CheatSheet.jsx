import React from 'react';

const CheatSheet = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content cheat-sheet-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&#x2715;</button>
        <h2 style={{ marginBottom: '1rem', color: 'var(--accent-primary)' }}>Defiant Gatekeeper Cheat Sheet</h2>
        
        <p className="text-secondary" style={{ marginBottom: '2rem' }}>
          This dashboard tracks macro indicators based on the 4-Quadrant Macro framework popularized by the{' '}
          <a href="https://www.youtube.com/@DefiantGatekeeper" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-secondary)' }}>
            Defiant Gatekeeper YouTube Channel
          </a>.
        </p>

        <h3 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>The 4 Macro Situations</h3>
        <p className="text-secondary" style={{ marginBottom: '1.5rem', lineHeight: '1.6' }}>
          The framework operates on a 2x2 matrix that combines <strong>Fed Policy Rate Stance</strong> with <strong>Reserve Liquidity Direction</strong>.
        </p>

        <div className="matrix-grid" style={{
          display: 'grid', 
          gridTemplateColumns: '1fr 1fr', 
          gap: '1rem',
          marginBottom: '2rem'
        }}>
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h4 style={{ color: 'var(--status-positive)' }}>Situation 1 (Top Left)</h4>
            <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}><strong>Policy:</strong> Easing / Cutting</div>
            <div style={{ fontSize: '0.9rem', marginBottom: '1rem' }}><strong>Liquidity:</strong> Expanding</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <strong>Risk-Liquidity Tailwind.</strong> Historically favors profitable technology, AI infrastructure, semiconductors, and consumer discretionary (if labor isn't breaking).
            </p>
          </div>
          
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h4 style={{ color: 'var(--status-warning)' }}>Situation 2 (Top Right)</h4>
            <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}><strong>Policy:</strong> Easing / Cutting</div>
            <div style={{ fontSize: '0.9rem', marginBottom: '1rem' }}><strong>Liquidity:</strong> Contracting</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <strong>Late-Cycle Caution.</strong> The Fed may be easing because growth/labor is weakening while liquidity is still tight. Favors defensive sectors (Healthcare, Staples, Gold).
            </p>
          </div>

          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h4 style={{ color: 'var(--status-warning)' }}>Situation 4 (Bottom Left)</h4>
            <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}><strong>Policy:</strong> Hawkish / Restrictive</div>
            <div style={{ fontSize: '0.9rem', marginBottom: '1rem' }}><strong>Liquidity:</strong> Expanding</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <strong>Policy/Liquidity Conflict.</strong> Rates are high but money is printing. Favors hard assets, commodity producers, energy, and inflation-linked cash flows.
            </p>
          </div>

          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h4 style={{ color: 'var(--status-negative)' }}>Situation 3 (Bottom Right)</h4>
            <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}><strong>Policy:</strong> Hawkish / Restrictive</div>
            <div style={{ fontSize: '0.9rem', marginBottom: '1rem' }}><strong>Liquidity:</strong> Contracting</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <strong>Restrictive Liquidity.</strong> High multiple-compression risk. Cash and T-bills are competitive. Long-duration growth stocks face severe headwinds.
            </p>
          </div>
        </div>

        <h3 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Important Definitions</h3>
        <ul className="text-secondary" style={{ lineHeight: '1.6', paddingLeft: '1.5rem' }}>
          <li style={{ marginBottom: '0.5rem' }}><strong>Reserve Liquidity Proxy = </strong> Fed Assets - TGA Balance - Reverse Repo. If this number increases over 30 days, liquidity is expanding.</li>
          <li style={{ marginBottom: '0.5rem' }}><strong>Policy Rate Stance:</strong> Classified as "Cutting" or "Raising" based on 30-day changes, or "Holding Restrictive" if the 10Y real yield remains elevated despite no recent hikes.</li>
        </ul>
      </div>
    </div>
  );
};

export default CheatSheet;
