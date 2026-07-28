import React, { useRef } from 'react';
import { useDialogFocus } from '../hooks/useDialogFocus';

const CheatSheet = ({ isOpen, onClose }) => {
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);

  useDialogFocus({
    isOpen,
    onClose,
    dialogRef,
    initialFocusRef: closeButtonRef,
  });

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content cheat-sheet-content" ref={dialogRef} tabIndex="-1" role="dialog" aria-modal="true" aria-labelledby="cheat-sheet-title" onClick={e => e.stopPropagation()}>
        <button className="modal-close" ref={closeButtonRef} type="button" aria-label="Close cheat sheet" onClick={onClose}>&#x2715;</button>
        <h2 id="cheat-sheet-title" className="dialog-title">Defiant Gatekeeper Cheat Sheet</h2>
        
        <p className="text-secondary cheat-sheet-intro">
          This dashboard tracks macro indicators based on the 4-Quadrant Macro framework popularized by the{' '}
          <a href="https://www.youtube.com/@DefiantGatekeeper" target="_blank" rel="noopener noreferrer">
            Defiant Gatekeeper YouTube Channel
          </a>.
        </p>

        <h3 className="cheat-sheet-heading">The 4 Macro Situations</h3>
        <p className="text-secondary cheat-sheet-copy">
          The framework operates on a 2x2 matrix that combines <strong>Fed Policy Rate Stance</strong> with <strong>Reserve Liquidity Direction</strong>.
        </p>

        <div className="matrix-grid">
          <div className="glass-panel situation-card">
            <h4 className="positive">Situation 1 (Top Left)</h4>
            <div className="situation-detail"><strong>Policy:</strong> Easing / Cutting</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity:</strong> Expanding</div>
            <p className="situation-summary">
              <strong>Risk-Liquidity Tailwind.</strong> Historically favors profitable technology, AI infrastructure, semiconductors, and consumer discretionary (if labor isn't breaking).
            </p>
          </div>
          
          <div className="glass-panel situation-card">
            <h4 className="warning">Situation 2 (Top Right)</h4>
            <div className="situation-detail"><strong>Policy:</strong> Easing / Cutting</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity:</strong> Contracting</div>
            <p className="situation-summary">
              <strong>Late-Cycle Caution.</strong> The Fed may be easing because growth/labor is weakening while liquidity is still tight. Favors defensive sectors (Healthcare, Staples, Gold).
            </p>
          </div>

          <div className="glass-panel situation-card">
            <h4 className="warning">Situation 4 (Bottom Left)</h4>
            <div className="situation-detail"><strong>Policy:</strong> Hawkish / Restrictive</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity:</strong> Expanding</div>
            <p className="situation-summary">
              <strong>Policy/Liquidity Conflict.</strong> Rates are high but money is printing. Favors hard assets, commodity producers, energy, and inflation-linked cash flows.
            </p>
          </div>

          <div className="glass-panel situation-card">
            <h4 className="negative">Situation 3 (Bottom Right)</h4>
            <div className="situation-detail"><strong>Policy:</strong> Hawkish / Restrictive</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity:</strong> Contracting</div>
            <p className="situation-summary">
              <strong>Restrictive Liquidity.</strong> High multiple-compression risk. Cash and T-bills are competitive. Long-duration growth stocks face severe headwinds.
            </p>
          </div>
        </div>

        <h3 className="cheat-sheet-heading">Important Definitions</h3>
        <ul className="text-secondary cheat-sheet-definitions">
          <li><strong>Reserve Liquidity Proxy = </strong> Fed Assets - TGA Balance - Reverse Repo. If this number increases over 30 days, liquidity is expanding.</li>
          <li><strong>Policy Rate Stance:</strong> Classified as "Cutting" or "Raising" based on 30-day changes, or "Holding Restrictive" if the 10Y real yield remains elevated despite no recent hikes.</li>
        </ul>
      </div>
    </div>
  );
};

export default CheatSheet;
